"""Render work reports as Markdown."""

from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from .task_clustering import Task
    from .common_wr import format_duration
except ImportError:
    from task_clustering import Task
    from common_wr import format_duration


def render_weekly_report(
    tasks: list[Task],
    start_date: datetime,
    end_date: datetime,
    total_sessions: int = 0,
) -> str:
    """Render a weekly work report as Markdown with numbered sections."""
    lines = []

    # Header
    lines.append(f"# Weekly Work Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"> Total sessions: {total_sessions} | Total tasks: {len(tasks)}")
    lines.append("")

    # 1. Summary
    lines.append("## 1. Summary")
    lines.append("")

    completed = len([t for t in tasks if t.status == "completed"])
    in_progress = len([t for t in tasks if t.status == "in_progress"])
    blocked = len([t for t in tasks if t.status == "blocked"])

    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Tasks | {len(tasks)} |")
    lines.append(f"| Completed | {completed} |")
    lines.append(f"| In Progress | {in_progress} |")
    lines.append(f"| Blocked | {blocked} |")

    all_files = set()
    for t in tasks:
        all_files.update(t.files_modified)
    lines.append(f"| Files modified | {len(all_files)} |")
    lines.append("")

    # 2. Tasks
    lines.append("## 2. Tasks")
    lines.append("")

    # Group tasks by project
    by_project: dict[str, list[Task]] = {}
    for t in tasks:
        proj = t.project or "Uncategorized"
        if proj not in by_project:
            by_project[proj] = []
        by_project[proj].append(t)

    proj_idx = 1
    for project, proj_tasks in sorted(by_project.items()):
        # Clean up project name
        display_project = project.replace("-", " ").replace("_", " ")
        if display_project.startswith("media yhr 2T files cc projects "):
            display_project = display_project[len("media yhr 2T files cc projects "):]
        elif display_project.startswith("home yhr "):
            display_project = display_project[len("home yhr "):]
        elif display_project.startswith("home lkshpc ZHITAI 2T "):
            display_project = display_project[len("home lkshpc ZHITAI 2T "):]

        lines.append(f"### 2.{proj_idx}. {display_project.strip()}")
        lines.append("")

        visible_tasks = [t for t in proj_tasks if t.status != "skipped"]
        for task_idx, task in enumerate(visible_tasks, start=1):
            _render_task(lines, task, proj_idx, task_idx)

        proj_idx += 1

    return "\n".join(lines)


def _render_task(lines: list[str], task: Task, proj_idx: int, task_idx: int) -> None:
    """Render a single task in STAR format with numbering."""
    # Status badge
    status_badge = {
        "completed": "Completed",
        "in_progress": "In Progress",
        "blocked": "Blocked",
    }.get(task.status, task.status)

    # Duration
    duration_str = ""
    if task.start_time and task.end_time:
        duration = (task.end_time - task.start_time).total_seconds()
        duration_str = format_duration(duration)

    lines.append(f"#### 2.{proj_idx}.{task_idx}. {task.title}")
    lines.append("")

    meta_parts = []
    if task.agent:
        meta_parts.append(f"**Agent**: {task.agent}")
    if duration_str:
        meta_parts.append(f"**Duration**: {duration_str}")
    meta_parts.append(f"**Status**: {status_badge}")

    lines.append(" | ".join(meta_parts))
    lines.append("")

    # STAR fields
    if task.situation:
        lines.append(f"- **Situation**: {task.situation}")
    elif task.task_description:
        lines.append(f"- **Situation**: {task.task_description}")

    if task.task_description:
        lines.append(f"- **Task**: {task.task_description}")
    elif task.title:
        lines.append(f"- **Task**: {task.title}")

    if task.actions:
        lines.append("- **Action**:")
        for action in task.actions[:6]:
            lines.append(f"  - {action}")

    if task.result:
        lines.append(f"- **Result**: {task.result}")

    # Files
    if task.files_modified:
        files_str = " ".join(f"`{f}`" for f in task.files_modified[:8])
        lines.append(f"- **Files**: {files_str}")
        if len(task.files_modified) > 8:
            lines.append(f"  - ... and {len(task.files_modified) - 8} more files")

    # Stats
    lines.append(f"- **Stats**: {task.total_prompts} prompts, {task.total_responses} responses, {task.total_events} events")
    lines.append("")


def save_report(content: str, filepath: Path) -> None:
    """Save a report to disk, creating parent directories as needed."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    print(f"Report saved to: {filepath}")
