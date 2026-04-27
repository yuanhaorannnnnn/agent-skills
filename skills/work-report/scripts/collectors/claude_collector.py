"""Collect conversation events from Claude Code jsonl logs."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from ..normalizer import Event, Session
    from ..common_wr import (
        load_jsonl,
        load_json,
        parse_iso_timestamp,
        parse_millis_timestamp,
        is_noise,
        extract_text_from_content,
    )
except ImportError:
    from normalizer import Event, Session
    from common_wr import (
        load_jsonl,
        load_json,
        parse_iso_timestamp,
        parse_millis_timestamp,
        is_noise,
        extract_text_from_content,
    )


def collect_claude_sessions(
    since: datetime, until: datetime
) -> list[Session]:
    """Collect all Claude Code sessions within the date range."""
    sessions = []
    projects_dir = Path.home() / ".claude" / "projects"
    if not projects_dir.exists():
        return sessions

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        # Load sessions index for metadata
        sessions_index = _load_sessions_index(project_dir)

        for jsonl_file in project_dir.glob("*.jsonl"):
            session_id = jsonl_file.stem
            session = _parse_claude_jsonl(
                jsonl_file, session_id, project_dir.name, since, until, sessions_index
            )
            if session and session.events:
                sessions.append(session)

    return sessions


def _load_sessions_index(project_dir: Path) -> dict[str, dict]:
    """Load sessions-index.json to get metadata per session."""
    index_path = project_dir / "sessions-index.json"
    data = load_json(index_path)
    if not data or "sessions" not in data:
        return {}
    return {s.get("sessionId", ""): s for s in data["sessions"]}


def _load_session_metadata(session_id: str) -> Optional[dict]:
    """Load session metadata from ~/.claude/sessions/<pid>.json by matching sessionId."""
    sessions_dir = Path.home() / ".claude" / "sessions"
    if not sessions_dir.exists():
        return None
    for meta_file in sessions_dir.glob("*.json"):
        data = load_json(meta_file)
        if data and data.get("sessionId") == session_id:
            return data
    return None


def _parse_claude_jsonl(
    path: Path,
    session_id: str,
    project: str,
    since: datetime,
    until: datetime,
    sessions_index: dict,
) -> Optional[Session]:
    """Parse a single Claude Code jsonl file into a Session."""
    events = []
    title = ""
    cwd = ""
    git_branch = ""
    started_at: Optional[datetime] = None

    records = load_jsonl(path)

    for obj in records:
        msg_type = obj.get("type", "")
        ts = parse_iso_timestamp(obj.get("timestamp", ""))

        if not ts:
            # Some events have numeric timestamps
            ts = parse_millis_timestamp(obj.get("timestamp", 0))

        if not ts:
            continue

        if not (since <= ts <= until):
            # Track title even if out of range for session metadata
            if msg_type == "custom-title":
                title = obj.get("customTitle", "")
            continue

        if started_at is None or ts < started_at:
            started_at = ts

        if msg_type == "custom-title":
            title = obj.get("customTitle", "")
            continue

        if msg_type == "user":
            # Skip meta messages (system-generated user messages)
            if obj.get("isMeta", False):
                continue

            content = extract_text_from_content(obj.get("message", {}).get("content", ""))
            if is_noise(content):
                continue

            cwd = obj.get("cwd", cwd)
            git_branch = obj.get("gitBranch", git_branch)

            events.append(
                Event(
                    timestamp=ts,
                    agent="claude",
                    session_id=session_id,
                    event_type="user_prompt",
                    content=content,
                    project=project,
                    cwd=cwd,
                    git_branch=git_branch,
                )
            )

        elif msg_type == "assistant":
            message = obj.get("message", {})
            content = extract_text_from_content(message.get("content", ""))
            if not content:
                continue

            # Check for tool_use in assistant content
            tool_names = []
            raw_content = message.get("content", [])
            if isinstance(raw_content, list):
                for item in raw_content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_names.append(item.get("name", ""))

            events.append(
                Event(
                    timestamp=ts,
                    agent="claude",
                    session_id=session_id,
                    event_type="assistant_response",
                    content=content,
                    project=project,
                    cwd=cwd,
                    git_branch=git_branch,
                    metadata={"tool_names": tool_names},
                )
            )

        elif msg_type == "file-history-snapshot":
            snapshot = obj.get("snapshot", {})
            backups = snapshot.get("trackedFileBackups", {})
            for filepath, info in backups.items():
                events.append(
                    Event(
                        timestamp=ts,
                        agent="claude",
                        session_id=session_id,
                        event_type="file_change",
                        file_path=filepath,
                        project=project,
                        cwd=cwd,
                        git_branch=git_branch,
                        metadata={"version": info.get("version", 0)},
                    )
                )

        elif msg_type == "attachment":
            att = obj.get("attachment", {})
            att_type = att.get("type", "")

            if att_type == "tool_result":
                tool_name = att.get("toolName", "")
                tool_result = att.get("result", "")
                events.append(
                    Event(
                        timestamp=ts,
                        agent="claude",
                        session_id=session_id,
                        event_type="tool_result",
                        content=str(tool_result)[:500] if tool_result else "",
                        tool_name=tool_name,
                        project=project,
                        cwd=cwd,
                        git_branch=git_branch,
                    )
                )

        elif msg_type == "system":
            subtype = obj.get("subtype", "")
            if subtype == "api_error":
                error_info = obj.get("error", {})
                content = f"API Error: {error_info.get('status', 'unknown')}"
                events.append(
                    Event(
                        timestamp=ts,
                        agent="claude",
                        session_id=session_id,
                        event_type="system",
                        content=content,
                        project=project,
                        cwd=cwd,
                        git_branch=git_branch,
                        metadata={"level": obj.get("level", "error")},
                    )
                )

    if not events:
        return None

    # Enrich with index metadata
    index_meta = sessions_index.get(session_id, {})
    if not title and index_meta:
        title = index_meta.get("summary", "")
    if index_meta.get("firstPrompt"):
        # Prepend first prompt as a synthetic event if not already present
        first_prompt = index_meta["firstPrompt"]
        if first_prompt and not is_noise(first_prompt):
            # Only add if no user events exist or first event is not a prompt
            user_events = [e for e in events if e.event_type == "user_prompt"]
            if not user_events or user_events[0].content != first_prompt:
                created = parse_iso_timestamp(index_meta.get("created", ""))
                if created and since <= created <= until:
                    events.insert(
                        0,
                        Event(
                            timestamp=created,
                            agent="claude",
                            session_id=session_id,
                            event_type="user_prompt",
                            content=first_prompt,
                            project=project,
                            cwd=cwd,
                            git_branch=git_branch,
                        ),
                    )

    # Load session metadata for title
    meta = _load_session_metadata(session_id)
    if meta:
        if not title:
            title = meta.get("name", "")
        if not cwd:
            cwd = meta.get("cwd", "")

    # Sort events by timestamp
    events.sort(key=lambda e: e.timestamp)

    ended_at = events[-1].timestamp if events else started_at

    return Session(
        session_id=session_id,
        agent="claude",
        project=project,
        title=title,
        cwd=cwd,
        git_branch=git_branch,
        started_at=started_at,
        ended_at=ended_at,
        events=events,
    )
