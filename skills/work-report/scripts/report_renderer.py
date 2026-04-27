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
    """Render a weekly work report as Markdown."""
    lines = []

    # Header
    lines.append(f"# Weekly Work Report - {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"> Generated from coding agent conversations")
    lines.append(f"> Total sessions: {total_sessions} | Total tasks: {len(tasks)}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")

    completed = len([t for t in tasks if t.status == "completed"])
    in_progress = len([t for t in tasks if t.status == "in_progress"])
    blocked = len([t for t in tasks if t.status == "blocked"])
    skipped = len([t for t in tasks if t.status == "skipped"])

    lines.append("| Metric | Count |")
    lines.append("|--------|-------|")
    lines.append(f"| Tasks identified | {len(tasks)} |")
    lines.append(f"| Completed | {completed} |")
    lines.append(f"| In Progress | {in_progress} |")
    lines.append(f"| Blocked | {blocked} |")
    if skipped:
        lines.append(f"| Skipped (too short) | {skipped} |")

    all_files = set()
    for t in tasks:
        all_files.update(t.files_modified)
    lines.append(f"| Files modified | {len(all_files)} |")
    lines.append("")

    # By Project
    lines.append("## By Project")
    lines.append("")

    # Group tasks by project
    by_project: dict[str, list[Task]] = {}
    for t in tasks:
        proj = t.project or "Uncategorized"
        if proj not in by_project:
            by_project[proj] = []
        by_project[proj].append(t)

    for project, proj_tasks in sorted(by_project.items()):
        # Clean up project name
        display_project = project.replace("-", " ").replace("_", " ")
        if display_project.startswith("media yhr 2T files cc projects "):
            display_project = display_project[len("media yhr 2T files cc projects "):]
        elif display_project.startswith("home yhr "):
            display_project = display_project[len("home yhr "):]
        elif display_project.startswith("home lkshpc ZHITAI 2T "):
            display_project = display_project[len("home lkshpc ZHITAI 2T "):]

        lines.append(f"### {display_project}")
        lines.append("")

        for task in proj_tasks:
            _render_task(lines, task)

    # Daily Breakdown
    lines.append("## Daily Breakdown")
    lines.append("")
    lines.append("| Date | Tasks | Key Activities |")
    lines.append("|------|-------|----------------|")

    by_date: dict[str, list[Task]] = {}
    for t in tasks:
        if t.start_time:
            date_str = t.start_time.strftime("%Y-%m-%d (%a)")
            if date_str not in by_date:
                by_date[date_str] = []
            by_date[date_str].append(t)

    for date_str, day_tasks in sorted(by_date.items()):
        summaries = []
        for t in day_tasks:
            title = t.title[:30] + "..." if len(t.title) > 30 else t.title
            status_icon = "✅" if t.status == "completed" else "🔄" if t.status == "in_progress" else "⚠️"
            summaries.append(f"{status_icon} {title}")
        lines.append(f"| {date_str} | {len(day_tasks)} | {', '.join(summaries[:3])} |")

    lines.append("")

    # In Progress / Pending
    pending = [t for t in tasks if t.status in ("in_progress", "blocked")]
    if pending:
        lines.append("## In Progress / Pending")
        lines.append("")
        for t in pending:
            icon = "🔄" if t.status == "in_progress" else "⚠️"
            lines.append(f"- {icon} **{t.project or 'Uncategorized'}**: {t.title}")
            if t.task_description:
                lines.append(f"  - {t.task_description[:100]}")
        lines.append("")

    # Completed
    completed_tasks = [t for t in tasks if t.status == "completed"]
    if completed_tasks:
        lines.append("## Completed This Week")
        lines.append("")
        for t in completed_tasks:
            lines.append(f"- ✅ **{t.project or 'Uncategorized'}**: {t.title}")
        lines.append("")

    # Files Modified
    if all_files:
        lines.append("## Files Modified")
        lines.append("")
        # Group by extension
        by_ext: dict[str, list[str]] = {}
        for f in sorted(all_files):
            ext = Path(f).suffix or "no ext"
            if ext not in by_ext:
                by_ext[ext] = []
            by_ext[ext].append(f)

        for ext, files in sorted(by_ext.items()):
            lines.append(f"### {ext}")
            for f in files[:20]:
                lines.append(f"- `{f}`")
            if len(files) > 20:
                lines.append(f"- ... and {len(files) - 20} more")
            lines.append("")

    return "\n".join(lines)


def _render_task(lines: list[str], task: Task) -> None:
    """Render a single task in STAR format."""
    # Skip very short/noise tasks
    if task.status == "skipped":
        return

    # Status badge
    status_badge = {
        "completed": "✅ Completed",
        "in_progress": "🔄 In Progress",
        "blocked": "⚠️ Blocked",
    }.get(task.status, task.status)

    # Duration
    duration_str = ""
    if task.start_time and task.end_time:
        duration = (task.end_time - task.start_time).total_seconds()
        duration_str = format_duration(duration)

    lines.append(f"#### {task.title}")
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
