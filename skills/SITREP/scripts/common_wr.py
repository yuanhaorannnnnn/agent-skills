"""Shared utilities for the work-report system."""

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Local timezone for consistent date-range comparisons.
# All parsed timestamps are converted to this timezone rather than
# being stripped to offset-naive (which would misalign UTC logs vs
# local since/until boundaries).
LOCAL_TZ = datetime.now().astimezone().tzinfo


def parse_iso_timestamp(ts_str) -> Optional[datetime]:
    """Parse ISO 8601 timestamp string to local-aware datetime.

    Converts any offset to local time. Also handles numeric timestamps.
    """
    if not ts_str or ts_str == "null":
        return None

    if isinstance(ts_str, (int, float)):
        return parse_unix_timestamp(ts_str)

    try:
        ts_str = str(ts_str)
        ts_str = ts_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=LOCAL_TZ)
        else:
            dt = dt.astimezone(LOCAL_TZ)
        return dt
    except (ValueError, TypeError):
        return None


def parse_unix_timestamp(ts: int | float) -> Optional[datetime]:
    """Parse Unix timestamp to local-aware datetime."""
    if not ts:
        return None
    try:
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.astimezone(LOCAL_TZ)
    except (ValueError, TypeError, OSError):
        return None


def parse_millis_timestamp(ts: int) -> Optional[datetime]:
    """Parse millisecond timestamp to local-aware datetime."""
    if not ts:
        return None
    return parse_unix_timestamp(ts / 1000)


def get_report_dir() -> Path:
    """Get the output directory for work reports."""
    path = Path.home() / ".agents" / "work-reports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_jsonl(path: Path) -> list[dict]:
    """Load a JSONL file, skipping malformed lines."""
    records = []
    with path.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return records


def load_json(path: Path) -> Optional[dict]:
    """Load a JSON file, returning None on failure."""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, PermissionError):
        return None


# Noise patterns to filter out from user prompts
NOISE_PATTERNS = [
    re.compile(r"^/clear$", re.IGNORECASE),
    re.compile(r"^/login$", re.IGNORECASE),
    re.compile(r"^/logout$", re.IGNORECASE),
    re.compile(r"^/exit$", re.IGNORECASE),
    re.compile(r"^<command-name>", re.IGNORECASE),
    re.compile(r"^<command-message>", re.IGNORECASE),
    re.compile(r"^<local-command-caveat>", re.IGNORECASE),
    re.compile(r"^<local-command-stdout>", re.IGNORECASE),
    re.compile(r"^Caveat: The messages below", re.IGNORECASE),
    re.compile(r"^SessionStart:", re.IGNORECASE),
    re.compile(r"^Checking session restore", re.IGNORECASE),
    re.compile(r"^Detected activity conversation", re.IGNORECASE),
    re.compile(r"^\s*$"),
    re.compile(r"^(ok|yes|no|done|thanks|thx)\s*$", re.IGNORECASE),
]


def is_noise(content: str) -> bool:
    """Check if content is noise that should be filtered out."""
    if not content:
        return True
    for pattern in NOISE_PATTERNS:
        if pattern.match(content):
            return True
    return False


def extract_text_from_content(content) -> str:
    """Extract plain text from various content formats."""
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
    return str(content) if content else ""


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds / 60)}m"
    hours = int(seconds / 3600)
    mins = int((seconds % 3600) / 60)
    return f"{hours}h{mins}m" if mins else f"{hours}h"


def get_week_range(date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Get the start (Monday 00:00) and end (Sunday 23:59) of the week.

    Returns local-aware datetimes for consistent comparison with parsed timestamps.
    """
    if date is None:
        date = datetime.now(LOCAL_TZ)
    monday = date - timedelta(days=date.weekday())
    monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = monday + timedelta(days=6, hours=23, minutes=59, seconds=59)
    return monday, sunday


def get_month_range(date: Optional[datetime] = None) -> tuple[datetime, datetime]:
    """Get the start and end of the month. Returns local-aware datetimes."""
    if date is None:
        date = datetime.now(LOCAL_TZ)
    start = date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1, day=1)
    else:
        end = start.replace(month=start.month + 1, day=1)
    end = end - timedelta(seconds=1)
    return start, end
