#!/usr/bin/env python3
"""Scan Codex sessions and list those that need a passdown handoff.

Hard signal only: structured compaction count (`context_compacted` events or
`compacted` rows). Per-rollout session files are grouped by `session_id` so a
single conversation is counted once. Read-only unless a mark option is used.

Privacy: output includes session id, cwd and compaction counts only. No message
text or tool output is emitted.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DEFAULT_SESSIONS = Path.home() / ".codex" / "sessions"
DEFAULT_STATE = Path.home() / ".agents" / "session-handoff" / "state.json"


def parse_ts(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def scan_file(path: Path) -> dict[str, Any] | None:
    session_id: str | None = None
    cwd: str | None = None
    compacted_rows = 0
    compacted_events = 0
    last_ts: datetime | None = None
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                row_type = row.get("type")
                payload = row.get("payload") or {}
                if row_type == "session_meta":
                    session_id = payload.get("session_id") or payload.get("id") or session_id
                    cwd = payload.get("cwd") or cwd
                elif row_type == "compacted":
                    compacted_rows += 1
                elif row_type == "event_msg" and payload.get("type") == "context_compacted":
                    compacted_events += 1
                ts = parse_ts(row.get("timestamp"))
                if ts and (last_ts is None or ts > last_ts):
                    last_ts = ts
    except OSError:
        return None
    if not session_id:
        return None
    return {
        "session_id": session_id,
        "cwd": cwd,
        # Some Codex versions may emit both representations for one compaction.
        # Use the larger structured count instead of summing both.
        "compactions": max(compacted_rows, compacted_events),
        "last_ts": last_ts,
        "path": str(path),
    }


def aggregate(sessions_dir: Path) -> dict[str, dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for path in sorted(sessions_dir.glob("**/*.jsonl")):
        record = scan_file(path)
        if not record:
            continue
        session_id = record["session_id"]
        entry = by_id.setdefault(
            session_id,
            {
                "session_id": session_id,
                "cwd": record["cwd"],
                "compactions": 0,
                "last_ts": None,
                "files": [],
            },
        )
        entry["compactions"] += record["compactions"]
        entry["files"].append(record["path"])
        if record["cwd"]:
            entry["cwd"] = record["cwd"]
        if record["last_ts"] and (entry["last_ts"] is None or record["last_ts"] > entry["last_ts"]):
            entry["last_ts"] = record["last_ts"]
    return by_id


def load_state(path: Path) -> dict[str, Any]:
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
    else:
        data = {}
    data.setdefault("version", 2)
    data.setdefault("handled", {})
    return data


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def mark_stage(
    path: Path,
    session_id: str,
    stage: str,
    successor: str | None,
    reason: str | None,
) -> None:
    state = load_state(path)
    current = state["handled"].get(session_id, {})
    if successor is None:
        successor = current.get("successor_thread_id")
    now = datetime.now(timezone.utc).isoformat()
    current.update({
        "stage": stage,
        "updated_at": now,
        "successor_thread_id": successor,
        "reason": reason or current.get("reason"),
    })
    if stage == "complete":
        current["handled_at"] = now
    state["handled"][session_id] = current
    state["version"] = 2
    save_state(path, state)


def candidates(
    by_id: dict[str, dict[str, Any]],
    state: dict[str, Any],
    threshold: int,
    min_idle_minutes: int,
    max_age_days: int,
    include_handled: bool,
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    age_cutoff = now - timedelta(days=max_age_days)
    idle_cutoff = now - timedelta(minutes=min_idle_minutes)
    handled = state.get("handled", {})
    out: list[dict[str, Any]] = []
    for entry in by_id.values():
        if entry["compactions"] < threshold:
            continue
        last_ts = entry["last_ts"]
        if last_ts is None or last_ts < age_cutoff or last_ts > idle_cutoff:
            continue
        handoff = handled.get(entry["session_id"])
        # Version-1 records had no stage and represented completed handoffs.
        stage = handoff.get("stage", "complete") if handoff else None
        if stage == "complete" and not include_handled:
            continue
        record = dict(entry)
        record["last_ts"] = last_ts.isoformat()
        record["idle_minutes"] = int((now - last_ts).total_seconds() // 60)
        record["handled"] = stage == "complete"
        record["handoff_stage"] = stage
        record["successor_thread_id"] = handoff.get("successor_thread_id") if handoff else None
        out.append(record)
    out.sort(key=lambda item: item["compactions"], reverse=True)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions-dir", type=Path, default=DEFAULT_SESSIONS)
    parser.add_argument("--state", type=Path, default=DEFAULT_STATE)
    parser.add_argument("--threshold", type=int, default=3)
    parser.add_argument("--min-idle-minutes", type=int, default=120)
    parser.add_argument("--max-age-days", type=int, default=30)
    parser.add_argument("--include-handled", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--mark-handled", metavar="SESSION_ID")
    parser.add_argument("--mark-successor", metavar="SESSION_ID")
    parser.add_argument("--mark-complete", metavar="SESSION_ID")
    parser.add_argument("--successor-thread-id")
    parser.add_argument("--reason")
    args = parser.parse_args()

    mark_args = [args.mark_handled, args.mark_successor, args.mark_complete]
    if sum(value is not None for value in mark_args) > 1:
        parser.error("use only one mark option")
    if args.mark_successor:
        if not args.successor_thread_id:
            parser.error("--mark-successor requires --successor-thread-id")
        mark_stage(args.state, args.mark_successor, "successor_created", args.successor_thread_id, args.reason)
        print(f"marked successor: {args.mark_successor} -> {args.successor_thread_id}")
        return 0
    if args.mark_complete or args.mark_handled:
        session_id = args.mark_complete or args.mark_handled
        mark_stage(args.state, session_id, "complete", args.successor_thread_id, args.reason)
        print(f"marked complete: {session_id} -> {args.successor_thread_id}")
        return 0

    state = load_state(args.state)
    found = candidates(
        aggregate(args.sessions_dir),
        state,
        args.threshold,
        args.min_idle_minutes,
        args.max_age_days,
        args.include_handled,
    )
    if args.json:
        print(json.dumps({"candidates": found}, ensure_ascii=False, indent=2))
        return 0
    if not found:
        print("no candidates")
        return 0
    print(f"{'comp':>5}  {'idle_min':>8}  {'session_id':36}  cwd")
    for item in found:
        print(f"{item['compactions']:>5}  {item['idle_minutes']:>8}  {item['session_id']:36}  {item['cwd']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
