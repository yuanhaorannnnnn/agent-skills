#!/usr/bin/env python3
"""Extract filtered conversation turns from Codex / Pi / Claude Code JSONL sessions.

Usage:
  python extract_handoff.py --source codex --cwd /path/to/project
  python extract_handoff.py --source pi    --cwd /path/to/project
  python extract_handoff.py --source claude --cwd /path/to/project

Output: JSON with session metadata, token estimate, and filtered turns.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def slugify_claude(cwd: str) -> str:
    """Claude Code cwd encoding: / → -, _ → -, leading - preserved."""
    return cwd.replace("/", "-").replace("_", "-")


def slugify_pi(cwd: str) -> str:
    """Pi cwd encoding: wrap with --, inner / replaced with -."""
    inner = cwd.strip("/").replace("/", "-")
    return "--" + inner + "--"


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 chars per token for CJK, ~4 for English."""
    return max(1, len(text) // 3)


# ── Codex ──────────────────────────────────────────────────────────────────

def _cwd_matches(session_cwd: str, target_cwd: str) -> bool:
    """Codex may record a parent directory as cwd. Match if equal or ancestor."""
    return session_cwd == target_cwd or target_cwd.startswith(session_cwd + "/")


def find_codex_session(cwd: str) -> Path | None:
    """Find the most recent Codex session file for the given cwd.

    Codex often records the parent directory as cwd (e.g. `projects/` when
    the actual working dir is `projects/flight`). Uses prefix match so a
    session cwd that is an ancestor of the target cwd counts as a match.

    Sorts by mtime (not filename) because Codex appends to existing session
    files — the filename timestamp is creation time, not last-write time.
    """
    sessions_root = Path.home() / ".codex" / "sessions"
    candidates = []  # list of (path, session_cwd)
    for jsonl in sessions_root.rglob("*.jsonl"):
        try:
            with open(jsonl, encoding="utf-8", errors="ignore") as f:
                for line in f:
                    if '"session_meta"' not in line and '"cwd"' not in line:
                        continue
                    try:
                        d = json.loads(line.strip())
                    except json.JSONDecodeError:
                        continue
                    if d.get("type") == "session_meta":
                        sc = d.get("payload", {}).get("cwd", "")
                        if _cwd_matches(sc, cwd):
                            candidates.append((jsonl, sc))
                        break
        except Exception:
            continue
    # Sort by match precision (longer cwd = better match), then mtime
    candidates.sort(key=lambda x: (len(x[1]), x[0].stat().st_mtime), reverse=True)
    return candidates[0][0] if candidates else None


def extract_codex_transcript(text: str) -> list[dict]:
    """Extract [N] user:/assistant: turns from a TRANSCRIPT block."""
    turns = []
    pattern = re.compile(r'^\[(\d+)\]\s+(user|assistant):\s*(.*)', re.MULTILINE)
    for m in pattern.finditer(text):
        turns.append({
            "turn": int(m.group(1)),
            "role": m.group(2),
            "text": m.group(3).strip(),
        })
    # Dedup by (turn, role), keep longest
    seen = {}
    for t in turns:
        key = (t["turn"], t["role"])
        if key not in seen or len(t["text"]) > len(seen[key]["text"]):
            seen[key] = t
    return sorted(seen.values(), key=lambda x: x["turn"])


def extract_all_text_from_jsonl(path: Path) -> tuple[bool, str]:
    """Extract all text blocks from a Codex JSONL, returning (has_transcript, combined_text)."""
    has_transcript = False
    all_texts = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            # Check for TRANSCRIPT in raw JSON string of this line
            line_str = json.dumps(d)
            if ">>> TRANSCRIPT" in line_str:
                has_transcript = True
            # Extract text from content blocks regardless of type
            payload = d.get("payload") or {}
            content = payload.get("content") or []
            for block in content:
                text = block.get("text") or ""
                if text:
                    all_texts.append(text)

    return has_transcript, "\n".join(all_texts)


def parse_codex(path: Path) -> dict:
    """Parse a Codex session JSONL. Auto-detect TRANSCRIPT vs direct mode."""
    has_transcript, combined = extract_all_text_from_jsonl(path)
    total_lines = sum(1 for _ in open(path, encoding="utf-8", errors="ignore"))

    if has_transcript:
        turns = extract_codex_transcript(combined)
        return {
            "mode": "transcript",
            "total_lines": total_lines,
            "turns": turns,
        }

    # Direct mode fallback
    turns = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            t = d.get("type", "")
            payload = d.get("payload") or {}
            role = payload.get("role", "")
            if t != "response_item" or role not in ("user", "assistant"):
                continue
            content = payload.get("content") or []
            texts = []
            for block in content:
                btype = block.get("type", "")
                text = block.get("text") or ""
                if btype in ("input_text", "output_text") and text:
                    texts.append(text)
            if texts:
                combined_text = "\n".join(texts)
                if role == "assistant" and combined_text.strip().startswith('{"outcome"'):
                    continue
                turns.append({"role": role, "text": combined_text})

    return {
        "mode": "direct",
        "total_lines": total_lines,
        "turns": turns,
    }


# ── Pi ─────────────────────────────────────────────────────────────────────

def find_pi_session(cwd: str) -> Path | None:
    """Find the most recent Pi session for the given cwd."""
    slug = slugify_pi(cwd)
    sessions_dir = Path.home() / ".pi" / "agent" / "sessions" / slug
    if not sessions_dir.is_dir():
        return None
    files = sorted(sessions_dir.glob("*.jsonl"), reverse=True)
    return files[0] if files else None


def parse_pi(path: Path) -> dict:
    """Parse a Pi session JSONL."""
    turns = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            t = d.get("type", "")
            if t != "message":
                continue
            msg = d.get("message") or {}
            role = msg.get("role", "")
            if role not in ("user", "assistant"):
                continue
            content = msg.get("content") or []
            texts = []
            for block in content:
                if block.get("type") == "text":
                    text = block.get("text") or ""
                    if text:
                        texts.append(text)
            if texts:
                turns.append({"role": role, "text": "\n".join(texts)})

    return {
        "mode": "message",
        "total_lines": sum(1 for _ in open(path, encoding="utf-8", errors="ignore")),
        "turns": turns,
    }


# ── Claude Code ─────────────────────────────────────────────────────────────

def _count_turns(jsonl_path: Path) -> int:
    """Count user/assistant turns in a JSONL for quality scoring."""
    try:
        count = 0
        with open(jsonl_path, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if '"type":"user"' in line or '"type":"assistant"' in line:
                    count += 1
        return count
    except Exception:
        return 0


def find_claude_session(cwd: str) -> Path | None:
    """Find the most recent Claude Code session for the given cwd.

    Tries ~/.claude/sessions/*.json index first. Falls back to direct
    scan of ~/.claude/projects/<cwd-slug>/*.jsonl when the index has
    no entry for this cwd (common when sessions are started from
    different CLI invocations or the index wasn't written).
    """
    # ── Primary: session index ───────────────────────────
    sessions_dir = Path.home() / ".claude" / "sessions"
    best_ts = 0
    best_id = None
    if sessions_dir.is_dir():
        for session_file in sessions_dir.glob("*.json"):
            try:
                meta = json.loads(session_file.read_text(encoding="utf-8"))
                if meta.get("cwd") == cwd:
                    ts = meta.get("startedAt", 0)
                    if ts > best_ts:
                        best_ts = ts
                        best_id = meta.get("sessionId")
            except Exception:
                continue

    slug = slugify_claude(cwd)
    project_dir = Path.home() / ".claude" / "projects" / slug

    if best_id:
        candidate = project_dir / f"{best_id}.jsonl"
        if candidate.is_file():
            return candidate

    # ── Fallback: scan project directory directly ──────────
    if not project_dir.is_dir():
        return None

    candidates = []
    for jsonl in project_dir.glob("*.jsonl"):
        turns = _count_turns(jsonl)
        mtime = jsonl.stat().st_mtime
        candidates.append((turns, mtime, jsonl))

    if not candidates:
        return None

    # Sort by meaningful content (turns), then recency
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)

    # Skip noise sessions (auto-push, cron, or very short)
    for turns, _, jsonl in candidates:
        if turns >= 5:  # skip trivially short sessions
            return jsonl
    return candidates[0][2]  # fallback: return best even if short


def parse_claude(path: Path) -> dict:
    """Parse a Claude Code session JSONL."""
    turns = []
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
            except json.JSONDecodeError:
                continue
            t = d.get("type", "")
            if t == "user":
                msg = d.get("message") or {}
                text = msg.get("content", "")
                if text:
                    turns.append({"role": "user", "text": str(text)})
            elif t == "assistant":
                msg = d.get("message") or {}
                content = msg.get("content") or []
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        text = block.get("text") or ""
                        if text:
                            texts.append(text)
                if texts:
                    turns.append({"role": "assistant", "text": "\n".join(texts)})

    return {
        "mode": "message",
        "total_lines": sum(1 for _ in open(path, encoding="utf-8", errors="ignore")),
        "turns": turns,
    }


# ── CLI ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Extract handoff context from coding agent sessions")
    parser.add_argument("--former", choices=["codex", "pi", "claude"], help="Alias for --source (preferred in handoff context)")
    parser.add_argument("--source", choices=["codex", "pi", "claude"], help="Which agent session to read")
    parser.add_argument("--cwd", required=True, help="Target working directory to match sessions")
    parser.add_argument("--json", action="store_true", help="Output raw JSON (default: human-readable)")
    args = parser.parse_args()

    source = args.former or args.source
    if not source:
        print("Error: --former (or --source) is required", file=sys.stderr)
        return 1

    finders = {"codex": find_codex_session, "pi": find_pi_session, "claude": find_claude_session}
    parsers = {"codex": parse_codex, "pi": parse_pi, "claude": parse_claude}

    finder = finders[source]
    parser_fn = parsers[source]

    session_path = finder(args.cwd)
    if not session_path:
        print(f"No session found for source={args.source} cwd={args.cwd}", file=sys.stderr)
        return 1

    result = parser_fn(session_path)
    turns = result["turns"]
    total_words = sum(len(t["text"].split()) for t in turns)
    total_tokens = sum(estimate_tokens(t["text"]) for t in turns)

    output = {
        "source": source,
        "session_file": str(session_path),
        "mode": result["mode"],
        "total_lines": result["total_lines"],
        "extracted_turns": len(turns),
        "estimated_words": total_words,
        "estimated_tokens": total_tokens,
        "turns": turns,
    }

    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(f"source:      {output['source']}")
        print(f"session:     {output['session_file']}")
        print(f"mode:        {output['mode']}")
        print(f"lines:       {output['total_lines']}")
        print(f"turns:       {output['extracted_turns']}")
        print(f"words:       ~{output['estimated_words']}")
        print(f"tokens:      ~{output['estimated_tokens']}")
        print(f"{'─'*60}")
        for i, turn in enumerate(turns):
            role = turn["role"]
            text = turn["text"]
            if role == "user":
                print(f"\n[{i}] USER: {text[:300]}{'...' if len(text) > 300 else ''}")
            else:
                print(f"[{i}] ASSISTANT: {text[:400]}{'...' if len(text) > 400 else ''}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
