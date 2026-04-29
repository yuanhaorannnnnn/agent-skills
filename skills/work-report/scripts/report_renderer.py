"""Render work reports as Markdown."""

from datetime import datetime
from pathlib import Path

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
    """Render a weekly work report as readable Markdown."""
    lines = []

    visible_tasks = [t for t in tasks if t.status != "skipped"]

    lines.append(f"# 工作周报：{start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")
    lines.append("")
    lines.append(f"> 基于 {total_sessions} 个 agent session 自动整理，识别出 {len(visible_tasks)} 项有效工作。")
    lines.append("")

    lines.append("## 1. 本周概览")
    lines.append("")

    completed = len([t for t in visible_tasks if t.status == "completed"])
    in_progress = len([t for t in visible_tasks if t.status == "in_progress"])
    blocked = len([t for t in visible_tasks if t.status == "blocked"])

    all_files = set()
    for task in visible_tasks:
        all_files.update(task.files_modified)

    if visible_tasks:
        status_parts = [f"完成 {completed} 项"]
        if in_progress:
            status_parts.append(f"进行中 {in_progress} 项")
        if blocked:
            status_parts.append(f"受阻 {blocked} 项")
        lines.append(
            f"本周共整理 {len(visible_tasks)} 项工作，"
            f"{'，'.join(status_parts)}。"
            f"涉及 {len(all_files)} 个文件的修改或检查。"
        )
    else:
        lines.append("本周没有采集到可汇报的有效工作。")
    lines.append("")

    lines.append("## 2. 重点工作")
    lines.append("")

    for task_idx, task in enumerate(visible_tasks, start=1):
        _render_task(lines, task, task_idx)

    return "\n".join(lines)


def _render_task(lines: list[str], task: Task, task_idx: int) -> None:
    """Render a single task in a readable STAR-inspired format."""
    status_badge = {
        "completed": "已完成",
        "in_progress": "进行中",
        "blocked": "受阻",
    }.get(task.status, task.status)

    duration_str = ""
    if task.start_time and task.end_time:
        duration = (task.end_time - task.start_time).total_seconds()
        duration_str = format_duration(duration)

    lines.append(f"### 2.{task_idx}. {task.title}")
    lines.append("")

    meta_parts = []
    if task.project:
        meta_parts.append(f"**项目**: {task.project}")
    if duration_str:
        meta_parts.append(f"**耗时**: {duration_str}")
    if task.agent:
        meta_parts.append(f"**Agent**: {task.agent}")
    meta_parts.append(f"**状态**: {status_badge}")

    lines.append(" | ".join(meta_parts))
    lines.append("")

    lead = _task_lead(task)
    if lead:
        lines.append(lead)
        lines.append("")

    if task.situation:
        lines.append(f"- **背景**: {task.situation}")

    objective = task.task_description or task.title
    if objective:
        lines.append(f"- **目标**: {objective}")

    if task.actions:
        lines.append("- **主要工作**:")
        for action in task.actions[:6]:
            lines.append(f"  - {action}")

    if task.result:
        lines.append(f"- **结果**: {task.result}")

    if task.files_modified:
        files_str = " ".join(f"`{f}`" for f in task.files_modified[:8])
        lines.append(f"- **相关文件**: {files_str}")
        if len(task.files_modified) > 8:
            lines.append(f"  - 另有 {len(task.files_modified) - 8} 个文件")

    lines.append(
        f"- **记录来源**: {task.total_prompts} 条用户输入，"
        f"{task.total_responses} 条 agent 回复，{task.total_events} 条事件"
    )
    lines.append("")


def _task_lead(task: Task) -> str:
    """Build a short human-readable lead sentence for a task."""
    objective = task.task_description or task.title
    if objective:
        return f"本项工作围绕“{objective}”展开。"
    if task.result:
        return f"本项工作目前的结果是：{task.result}"
    return ""


def save_report(content: str, filepath: Path) -> None:
    """Save a report to disk, creating parent directories as needed."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    print(f"Report saved to: {filepath}")
