"""Canon task pages collector. Scans /media/yhr/2T/Canon/tasks/ for recently modified task pages.

Canon tasks are the PRIMARY data source — they override LLM-extracted task descriptions
from agent sessions when there's a match.
"""

import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Local timezone for consistent comparison with aware since/until from common_wr
_LOCAL_TZ = datetime.now().astimezone().tzinfo

CANON_TASKS_DIR = Path("/media/yhr/2T/Canon/tasks")


def collect_canon_tasks(since: datetime, until: datetime) -> list[dict]:
    """Collect Canon task pages active in the date range.

    Canon frontmatter `updated`/`created` is the primary activity date. Filesystem
    mtime is only a fallback for legacy pages without frontmatter dates.
    """
    if not CANON_TASKS_DIR.exists():
        return []

    tasks = []
    seen_real_paths: set[str] = set()
    for md_file in CANON_TASKS_DIR.rglob("*.md"):
        # Skip symlinks that resolve to an already-processed file
        # (e.g. JHBN-7699.md → jhbn-7699-repair.md).
        real_path = str(md_file.resolve())
        if real_path in seen_real_paths:
            continue
        seen_real_paths.add(real_path)

        # Nested goal.md files are execution artifacts linked from task pages,
        # not separate weekly work items.
        if md_file.name == "goal.md" and md_file.parent != CANON_TASKS_DIR:
            continue

        mtime = datetime.fromtimestamp(md_file.stat().st_mtime, tz=_LOCAL_TZ)
        content = md_file.read_text(encoding="utf-8")
        parsed = _parse_canon_page(content, md_file, mtime)
        if not parsed:
            continue

        activity_at = parsed.get("activity_at") or mtime

        # Bypass date filter for tasks explicitly marked as weekly work items.
        # report_scope:work + weekly:true is the author's declaration that this
        # task belongs in the weekly report regardless of last-activity date.
        report_scope = (parsed.get("report_scope") or "").strip().lower()
        is_weekly_work = (report_scope == "work" and parsed.get("weekly") is True)

        if not is_weekly_work and not (since <= activity_at <= until):
            continue
        tasks.append(parsed)

    return tasks


def _parse_frontmatter(lines: list[str]) -> tuple[dict, list[str]]:
    if not lines or lines[0].strip() != "---":
        return {}, lines
    meta: dict[str, str] = {}
    idx = 1
    while idx < len(lines):
        line = lines[idx]
        if line.strip() == "---":
            return meta, lines[idx + 1:]
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip().strip('"').strip("'")
        idx += 1
    return meta, lines


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"true", "yes", "y", "1", "on"}:
        return True
    if normalized in {"false", "no", "n", "0", "off"}:
        return False
    return None


def _parse_frontmatter_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip().strip('"').strip("'")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(raw, fmt)
            if fmt == "%Y-%m-%d":
                dt = dt.replace(hour=12)
            return dt.replace(tzinfo=_LOCAL_TZ)
        except ValueError:
            pass
    try:
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=_LOCAL_TZ)
        return dt
    except ValueError:
        return None


def _normalize_status(status: str) -> str:
    value = (status or "").strip().lower()
    mapping = {
        "active": "in_progress",
        "in progress": "in_progress",
        "in_progress": "in_progress",
        "new": "new",
        "todo": "new",
        "complete": "completed",
        "completed": "completed",
        "done": "completed",
        "blocked": "blocked",
    }
    return mapping.get(value, value or "in_progress")


def _parse_canon_page(content: str, filepath: Path, mtime: datetime) -> dict | None:
    """Parse a Canon task page into structured data."""
    raw_lines = content.strip().split("\n")
    frontmatter, lines = _parse_frontmatter(raw_lines)
    if not lines:
        return None

    title = frontmatter.get("title", "").strip()
    body_start = 0
    for idx, line in enumerate(lines):
        if line.startswith("# "):
            if not title:
                title = line[2:].strip()
            body_start = idx + 1
            break
    if not title:
        return None

    objective = ""
    checklist = []
    constraints = []
    current_section = None

    objective_sections = {"目标", "goal", "objective"}
    checklist_sections = {"任务清单", "tasks", "checklist"}
    constraint_sections = {"关键约束", "constraints", "non-goals", "non-goal"}

    for line in lines[body_start:]:
        if line.startswith("## "):
            current_section = line[3:].strip()
            continue
        section_key = (current_section or "").strip().lower()
        if section_key in objective_sections:
            if line.strip() and not line.startswith("#"):
                objective += line.strip() + " "
        elif section_key in checklist_sections:
            m = re.match(r"^- \[(.)\]\s+(.*)", line)
            if m:
                checklist.append({"done": m.group(1).lower() == "x", "text": m.group(2).strip()})
        elif section_key in constraint_sections:
            if line.strip() and not line.startswith("#"):
                constraints.append(line.strip())

    if frontmatter.get("status"):
        status = _normalize_status(frontmatter.get("status", ""))
    elif not checklist:
        status = "in_progress"
    elif all(c["done"] for c in checklist):
        status = "completed"
    elif any(c["done"] for c in checklist):
        status = "in_progress"
    else:
        status = "new"

    activity_at = (
        _parse_frontmatter_datetime(frontmatter.get("updated"))
        or _parse_frontmatter_datetime(frontmatter.get("created"))
        or mtime
    )
    is_active_this_week = (datetime.now(_LOCAL_TZ) - activity_at).days <= 7
    project = frontmatter.get("project") or _infer_project(title, objective, constraints)

    return {
        "title": title,
        "weekly_title": (frontmatter.get("weekly_title") or "").strip(),
        "objective": objective.strip(),
        "checklist": checklist,
        "status": status,
        "source": "canon",
        "source_file": str(filepath),
        "modified_at": mtime,
        "activity_at": activity_at,
        "is_active": is_active_this_week,
        "project": project,
        "report_scope": (frontmatter.get("report_scope") or "").strip().lower(),
        "weekly": _parse_bool(frontmatter.get("weekly")),
        "tags": _infer_tags(title, objective),
    }

def _infer_project(title: str, objective: str, constraints: list[str]) -> str:
    """Infer which project this task belongs to."""
    combined = (title + " " + objective + " " + " ".join(constraints)).lower()
    if "carla" in combined or "ue5" in combined or "sensor" in combined:
        return "CarlaUE5"
    if "tadsim" in combined or "动力学" in combined:
        return "TadSimVehicleDynamicsDemo"
    if "skill" in combined or "agent" in combined or "codex" in combined:
        return "agent-skills"
    return "Canon"


def _infer_tags(title: str, objective: str) -> list[str]:
    """Infer topic tags for matching with topics.yaml."""
    combined = (title + " " + objective).lower()
    tags = []
    if any(kw in combined for kw in ["仿真", "sensor", "lidar", "camera", "传感器"]):
        tags.append("仿真")
    if any(kw in combined for kw in ["重建", "点云", "gaussian", "nerf", "mesh", "3dgs"]):
        tags.append("重建")
    return tags
