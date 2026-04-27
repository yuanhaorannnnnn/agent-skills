"""Collect conversation events from Kimi session logs."""

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


def collect_kimi_sessions(
    since: datetime, until: datetime
) -> list[Session]:
    """Collect all Kimi sessions within the date range."""
    sessions = []
    sessions_dir = Path.home() / ".kimi" / "sessions"
    if not sessions_dir.exists():
        return sessions

    for session_hash in sessions_dir.iterdir():
        if not session_hash.is_dir():
            continue

        for subsession_dir in session_hash.iterdir():
            if not subsession_dir.is_dir():
                continue

            session = _parse_kimi_subsession(subsession_dir, since, until)
            if session and session.events:
                sessions.append(session)

    return sessions


def _parse_kimi_subsession(
    subsession_dir: Path,
    since: datetime,
    until: datetime,
) -> Optional[Session]:
    """Parse a single Kimi subsession directory into a Session."""
    session_id = subsession_dir.name
    parent_hash = subsession_dir.parent.name

    # Read state.json for metadata
    state_path = subsession_dir / "state.json"
    state = load_json(state_path) or {}
    title = state.get("custom_title", "") or state.get("title", "")

    events = []
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    # Primary source: wire.jsonl (full execution trace)
    wire_path = subsession_dir / "wire.jsonl"
    if wire_path.exists():
        wire_events, wire_start, wire_end = _parse_wire_jsonl(
            wire_path, session_id, since, until
        )
        events.extend(wire_events)
        if wire_start:
            started_at = wire_start
        if wire_end:
            ended_at = wire_end

    # Fallback: context.jsonl (conversation history)
    context_path = subsession_dir / "context.jsonl"
    if context_path.exists() and not events:
        ctx_events, ctx_start, ctx_end = _parse_context_jsonl(
            context_path, session_id, since, until
        )
        events.extend(ctx_events)
        if ctx_start:
            started_at = ctx_start
        if ctx_end:
            ended_at = ctx_end

    if not events:
        return None

    events.sort(key=lambda e: e.timestamp)

    # Deduplicate user prompts (wire may have duplicates from context)
    seen_prompts = set()
    deduped = []
    for e in events:
        if e.event_type == "user_prompt":
            key = (e.timestamp.strftime("%Y-%m-%d %H:%M"), e.content[:100])
            if key in seen_prompts:
                continue
            seen_prompts.add(key)
        deduped.append(e)
    events = deduped

    return Session(
        session_id=session_id,
        agent="kimi",
        project=parent_hash,  # Use hash as project identifier
        title=title,
        started_at=started_at or events[0].timestamp,
        ended_at=ended_at or events[-1].timestamp,
        events=events,
    )


def _parse_wire_jsonl(
    wire_path: Path,
    session_id: str,
    since: datetime,
    until: datetime,
) -> tuple[list[Event], Optional[datetime], Optional[datetime]]:
    """Parse Kimi wire.jsonl into events."""
    events = []
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    records = load_jsonl(wire_path)

    for obj in records:
        msg = obj.get("message", {})
        if not isinstance(msg, dict):
            continue

        msg_type = msg.get("type", "")
        payload = msg.get("payload", {})
        if not isinstance(payload, dict):
            continue

        # Parse timestamp
        ts = parse_iso_timestamp(obj.get("timestamp", ""))
        if not ts:
            ts = parse_unix_timestamp(obj.get("timestamp", 0))
        if not ts:
            ts = parse_unix_timestamp(msg.get("timestamp", 0))

        if not ts:
            continue

        if not (since <= ts <= until):
            continue

        if started_at is None or ts < started_at:
            started_at = ts
        if ended_at is None or ts > ended_at:
            ended_at = ts

        if msg_type == "TurnBegin":
            user_input = payload.get("user_input", [])
            text = _extract_user_input_text(user_input)
            if text and not is_noise(text):
                events.append(
                    Event(
                        timestamp=ts,
                        agent="kimi",
                        session_id=session_id,
                        event_type="user_prompt",
                        content=text,
                    )
                )

        elif msg_type == "ContentPart":
            part = payload.get("part", {})
            if isinstance(part, dict):
                part_type = part.get("type", "")
                if part_type == "text":
                    text = part.get("text", "")
                    if text and not is_noise(text):
                        events.append(
                            Event(
                                timestamp=ts,
                                agent="kimi",
                                session_id=session_id,
                                event_type="assistant_response",
                                content=text,
                            )
                        )
                elif part_type == "think":
                    text = part.get("think", "")
                    if text:
                        events.append(
                            Event(
                                timestamp=ts,
                                agent="kimi",
                                session_id=session_id,
                                event_type="thinking",
                                content=text,
                            )
                        )

        elif msg_type == "ToolCall":
            tc = payload.get("tool_call", {})
            if isinstance(tc, dict):
                func = tc.get("function", {})
                if isinstance(func, dict):
                    tool_name = func.get("name", "")
                else:
                    tool_name = tc.get("name", "")
                events.append(
                    Event(
                        timestamp=ts,
                        agent="kimi",
                        session_id=session_id,
                        event_type="tool_call",
                        tool_name=tool_name,
                    )
                )

        elif msg_type == "ToolResult":
            tr = payload.get("tool_result", {})
            if isinstance(tr, dict):
                tool_name = tr.get("name", "")
                content = str(tr.get("content", ""))[:500]
                events.append(
                    Event(
                        timestamp=ts,
                        agent="kimi",
                        session_id=session_id,
                        event_type="tool_result",
                        content=content,
                        tool_name=tool_name,
                    )
                )

        elif msg_type == "StatusUpdate":
            status = payload.get("status", "")
            if status:
                events.append(
                    Event(
                        timestamp=ts,
                        agent="kimi",
                        session_id=session_id,
                        event_type="system",
                        content=f"Status: {status}",
                    )
                )

    return events, started_at, ended_at


def _parse_context_jsonl(
    context_path: Path,
    session_id: str,
    since: datetime,
    until: datetime,
) -> tuple[list[Event], Optional[datetime], Optional[datetime]]:
    """Parse Kimi context.jsonl as fallback."""
    events = []
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    records = load_jsonl(context_path)

    for i, obj in enumerate(records):
        role = obj.get("role", "")
        content = obj.get("content", "")

        if role == "_system_prompt":
            continue

        # Context.jsonl doesn't have timestamps, use index as proxy
        # Assign evenly spaced timestamps within the range
        ts = since + (until - since) * (i / max(len(records), 1))

        if role == "user":
            text = _extract_content_text(content)
            if text and not is_noise(text):
                events.append(
                    Event(
                        timestamp=ts,
                        agent="kimi",
                        session_id=session_id,
                        event_type="user_prompt",
                        content=text,
                    )
                )

        elif role == "assistant":
            text = _extract_content_text(content)
            if text and not is_noise(text):
                events.append(
                    Event(
                        timestamp=ts,
                        agent="kimi",
                        session_id=session_id,
                        event_type="assistant_response",
                        content=text,
                    )
                )

    if events:
        started_at = events[0].timestamp
        ended_at = events[-1].timestamp

    return events, started_at, ended_at


def _extract_user_input_text(user_input) -> str:
    """Extract text from Kimi's user_input array."""
    if isinstance(user_input, str):
        return user_input
    if isinstance(user_input, list):
        parts = []
        for item in user_input:
            if isinstance(item, dict):
                text = item.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""


def _extract_content_text(content) -> str:
    """Extract text from Kimi content (may be string or array)."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text", "")
                if text:
                    parts.append(text)
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(parts)
    return ""
