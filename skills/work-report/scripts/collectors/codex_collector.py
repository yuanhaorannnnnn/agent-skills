"""Collect conversation events from Codex session logs."""

from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from ..normalizer import Event, Session
    from ..common_wr import (
        load_jsonl,
        load_json,
        parse_iso_timestamp,
        parse_unix_timestamp,
        is_noise,
    )
except ImportError:
    from normalizer import Event, Session
    from common_wr import (
        load_jsonl,
        load_json,
        parse_iso_timestamp,
        parse_unix_timestamp,
        is_noise,
    )


def collect_codex_sessions(
    since: datetime, until: datetime
) -> list[Session]:
    """Collect all Codex sessions within the date range."""
    sessions = []
    sessions_dir = Path.home() / ".codex" / "sessions"
    if not sessions_dir.exists():
        return sessions

    # Load session index for metadata
    session_index = _load_session_index()

    # Codex organizes sessions by year/month/day
    for year_dir in sessions_dir.iterdir():
        if not year_dir.is_dir() or not year_dir.name.isdigit():
            continue
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir() or not month_dir.name.isdigit():
                continue
            for day_dir in month_dir.iterdir():
                if not day_dir.is_dir() or not day_dir.name.isdigit():
                    continue
                for jsonl_file in day_dir.glob("rollout-*.jsonl"):
                    session = _parse_codex_jsonl(
                        jsonl_file, since, until, session_index
                    )
                    if session and session.events:
                        sessions.append(session)

    return sessions


def _load_session_index() -> dict[str, dict]:
    """Load session_index.jsonl to get metadata per session."""
    index_path = Path.home() / ".codex" / "session_index.jsonl"
    sessions = {}
    records = load_jsonl(index_path)
    for record in records:
        sid = record.get("id", "")
        if sid:
            sessions[sid] = record
    return sessions


def _extract_session_id(filename: str) -> str:
    """Extract session ID from rollout filename.
    Format: rollout-YYYY-MM-DDTHH-MM-SS-<uuid>.jsonl
    """
    # The UUID is the last part before .jsonl
    parts = filename.replace(".jsonl", "").split("-")
    # Find the UUID part (starts after the timestamp)
    # rollout-2026-03-12T14-12-46-019ce0ad-1769-7982-bdd3-9d2c6e001e17
    # The UUID starts after the time components
    if len(parts) >= 7:
        # parts[-5:] should be the UUID segments
        return "-".join(parts[-5:])
    return filename.replace(".jsonl", "")


def _parse_codex_jsonl(
    path: Path,
    since: datetime,
    until: datetime,
    session_index: dict,
) -> Optional[Session]:
    """Parse a single Codex rollout jsonl file into a Session."""
    events = []
    session_id = _extract_session_id(path.name)
    title = ""
    cwd = ""
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # Get metadata from session index
    meta = session_index.get(session_id, {})
    if meta:
        title = meta.get("thread_name", "")
        ts = meta.get("updated_at", 0)
        if ts:
            started_at = parse_unix_timestamp(ts)

    records = load_jsonl(path)

    for obj in records:
        payload = obj.get("payload", obj)  # Some records have payload, some don't
        event_type = payload.get("type", "") if isinstance(payload, dict) else ""

        # Try multiple timestamp fields
        ts = parse_iso_timestamp(obj.get("timestamp", ""))
        if not ts:
            ts = parse_unix_timestamp(obj.get("ts", 0))

        if not ts:
            continue

        if not (since <= ts <= until):
            continue

        if started_at is None or ts < started_at:
            started_at = ts
        if ended_at is None or ts > ended_at:
            ended_at = ts

        # Handle nested payload structure
        if isinstance(payload, dict) and "payload" in payload:
            payload = payload["payload"]

        if event_type == "session_meta":
            session_meta = payload.get("payload", payload)
            if isinstance(session_meta, dict):
                cwd = session_meta.get("cwd", cwd)
                if not title:
                    title = session_meta.get("id", "")
            continue

        if event_type == "user_message":
            text = payload.get("message", "")
            if isinstance(text, dict):
                text = text.get("text", "")
            if not text or is_noise(text):
                continue
            # Skip Codex-specific meta commands
            if text.startswith("$") or text.startswith("/"):
                continue

            events.append(
                Event(
                    timestamp=ts,
                    agent="codex",
                    session_id=session_id,
                    event_type="user_prompt",
                    content=text,
                    cwd=cwd,
                )
            )

        elif event_type == "agent_message":
            text = payload.get("message", "")
            if isinstance(text, dict):
                text = text.get("text", "")
            if not text:
                continue

            phase = payload.get("phase", "")
            events.append(
                Event(
                    timestamp=ts,
                    agent="codex",
                    session_id=session_id,
                    event_type="assistant_response",
                    content=text,
                    cwd=cwd,
                    metadata={"phase": phase},
                )
            )

        elif event_type == "ToolCall":
            tc = payload.get("tool_call", {})
            if isinstance(tc, dict):
                tool_name = tc.get("name", "")
                # Codex tool calls may have different structure
                if not tool_name:
                    tool_name = tc.get("function", {}).get("name", "")
                events.append(
                    Event(
                        timestamp=ts,
                        agent="codex",
                        session_id=session_id,
                        event_type="tool_call",
                        tool_name=tool_name,
                        cwd=cwd,
                    )
                )

        elif event_type == "ToolResult":
            tr = payload.get("tool_result", {})
            if isinstance(tr, dict):
                tool_name = tr.get("name", "")
                content = str(tr.get("content", ""))[:500]
                events.append(
                    Event(
                        timestamp=ts,
                        agent="codex",
                        session_id=session_id,
                        event_type="tool_result",
                        content=content,
                        tool_name=tool_name,
                        cwd=cwd,
                    )
                )

        elif event_type == "StepBegin":
            # Step begin may contain user input
            user_input = payload.get("user_input", "")
            if user_input and not is_noise(user_input):
                if not user_input.startswith("$") and not user_input.startswith("/"):
                    events.append(
                        Event(
                            timestamp=ts,
                            agent="codex",
                            session_id=session_id,
                            event_type="user_prompt",
                            content=user_input,
                            cwd=cwd,
                        )
                    )

        elif event_type == "ContentPart":
            part = payload.get("part", {})
            if isinstance(part, dict):
                part_type = part.get("type", "")
                if part_type == "text":
                    text = part.get("text", "")
                    if text and not is_noise(text):
                        events.append(
                            Event(
                                timestamp=ts,
                                agent="codex",
                                session_id=session_id,
                                event_type="assistant_response",
                                content=text,
                                cwd=cwd,
                            )
                        )
                elif part_type == "thinking":
                    text = part.get("thinking", "")
                    if text:
                        events.append(
                            Event(
                                timestamp=ts,
                                agent="codex",
                                session_id=session_id,
                                event_type="thinking",
                                content=text,
                                cwd=cwd,
                            )
                        )

    if not events:
        return None

    events.sort(key=lambda e: e.timestamp)

    return Session(
        session_id=session_id,
        agent="codex",
        title=title,
        cwd=cwd,
        started_at=started_at or events[0].timestamp,
        ended_at=ended_at or events[-1].timestamp,
        events=events,
    )
