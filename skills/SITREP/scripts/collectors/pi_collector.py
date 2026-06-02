"""Pi agent session collector. Reads ~/.pi/agent/sessions/<project>/<timestamp>_<uuid>.jsonl"""

from datetime import datetime
from pathlib import Path
import json

from common_wr import parse_iso_timestamp, is_noise, extract_text_from_content, load_jsonl
from normalizer import Session, Event

PI_SESSIONS_DIR = Path.home() / ".pi" / "agent" / "sessions"


def collect_pi_sessions(since: datetime, until: datetime) -> list[Session]:
    """Collect Pi sessions within the date range."""
    sessions = []
    if not PI_SESSIONS_DIR.exists():
        return sessions

    for project_dir in PI_SESSIONS_DIR.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl_file in project_dir.glob("*.jsonl"):
            session = _parse_pi_session(jsonl_file, project_dir.name, since, until)
            if session and session.events:
                sessions.append(session)
    return sessions


def _parse_pi_session(path: Path, project: str, since: datetime, until: datetime) -> Session | None:
    """Parse a single Pi jsonl session file."""
    events = []
    session_id = ""
    cwd = ""
    title = ""

    try:
        records = load_jsonl(path)
    except Exception:
        return None

    for obj in records:
        msg_type = obj.get("type", "")
        ts = parse_iso_timestamp(obj.get("timestamp", ""))

        if not ts:
            continue

        # Session metadata
        if msg_type == "session":
            session_id = obj.get("id", "")
            cwd = obj.get("cwd", "")
            continue

        # Skip non-message events
        if msg_type in ("model_change", "thinking_level_change"):
            continue

        # Filter by time range
        if not (since <= ts <= until):
            continue

        if msg_type == "message":
            message = obj.get("message", {})
            role = message.get("role", "")
            content_blocks = message.get("content", [])

            # Extract text from content blocks
            text_parts = []
            for block in content_blocks:
                if isinstance(block, dict):
                    block_type = block.get("type", "")
                    if block_type == "text":
                        text_parts.append(block.get("text", ""))
                    elif block_type == "thinking":
                        pass  # skip thinking blocks for clustering
                    elif block_type == "toolCall":
                        fn = block.get("function", {})
                        text_parts.append(f"[tool_call] {fn.get('name', '')}")
                    elif block_type == "toolResult":
                        text_parts.append(block.get("text", "")[:200])

            content = " ".join(text_parts).strip()
            if not content:
                continue

            if role == "user":
                # Use first user message as title
                if not title:
                    title = content[:80]
                events.append(Event(
                    timestamp=ts, agent="pi", session_id=session_id,
                    event_type="user_prompt", content=content,
                    project=project, cwd=cwd,
                ))
            elif role == "assistant":
                events.append(Event(
                    timestamp=ts, agent="pi", session_id=session_id,
                    event_type="assistant_response", content=content,
                    project=project, cwd=cwd,
                ))
            elif role == "toolResult":
                events.append(Event(
                    timestamp=ts, agent="pi", session_id=session_id,
                    event_type="tool_result", content=content,
                    project=project, cwd=cwd,
                ))

    if not events or not session_id:
        return None

    started_at = events[0].timestamp if events else None
    ended_at = events[-1].timestamp if events else None
    project_name = _project_name_from_dir(project)

    return Session(
        session_id=session_id, agent="pi", project=project_name,
        title=title or session_id[:12], cwd=cwd,
        started_at=started_at, ended_at=ended_at,
        status="completed" if ended_at and (until - ended_at).total_seconds() > 3600 else "active",
        events=events,
    )


def _project_name_from_dir(dirname: str) -> str:
    """Convert Pi's directory naming to project name.
    Pi uses: --path--to--project-- (double dash separated)
    """
    if dirname.startswith("--"):
        parts = dirname.strip("-").split("--")
        return "/" + "/".join(parts)
    return dirname


