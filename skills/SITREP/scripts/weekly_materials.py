#!/usr/bin/env python3
"""Friday 17:30 — generate DingTalk doc with raw weekly report materials.

This intentionally does not generate or submit a final weekly report. The doc is
only a reference bundle for the user to write the report manually.
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common_wr import get_report_dir
from friday_review import (
    _canon_task_to_report_task,
    _match_session_task,
    _merge_session_evidence,
    _select_work_canon_tasks,
    create_dingtalk_doc,
    get_friday_week_range,
)
from generate_work_report import collect_all_sessions, filter_by_topic
from task_clustering import cluster_sessions
from collectors.canon_collector import collect_canon_tasks


def _parse_range(args: list[str]):
    since, until = None, None
    for i, arg in enumerate(args):
        if arg == "--since" and i + 1 < len(args):
            since = datetime.strptime(args[i + 1], "%Y-%m-%d")
        if arg == "--until" and i + 1 < len(args):
            until = datetime.strptime(args[i + 1], "%Y-%m-%d")
    if since and until:
        return (
            since.replace(hour=0, minute=0, second=0, microsecond=0),
            until.replace(hour=23, minute=59, second=59, microsecond=999999),
        )
    return get_friday_week_range()


def _short_lines(values, limit=8):
    lines = []
    for value in values[:limit]:
        text = str(value).strip()
        if text:
            lines.append(text)
    if len(values) > limit:
        lines.append(f"... 另有 {len(values) - limit} 项")
    return lines


def build_materials_md(tasks, session_only, since, until, total_sessions: int) -> str:
    week_label = f"{since.strftime('%-m/%-d')} - {until.strftime('%-m/%-d')}"
    lines = [
        f"# 周报参考素材 · {week_label}",
        "",
        "> 这不是周报，也不是待确认 checklist。这里只汇总 agent/Canon 捕获到的原始素材，供手写周报参考。",
        "",
        "## 范围",
        "",
        f"- 时间：{since.strftime('%Y-%m-%d %H:%M')} → {until.strftime('%Y-%m-%d %H:%M')}",
        f"- Canon 工作任务：{len(tasks)} 项",
        f"- Session 工作候选：{len(session_only)} 项",
        f"- 原始 session：{total_sessions} 个",
        "",
        "## Canon 工作任务",
        "",
    ]

    if not tasks:
        lines.append("- 本周未发现 `report_scope: work AND weekly: true` 的 Canon task。")
        lines.append("")

    for idx, task in enumerate(tasks, 1):
        lines.extend([
            f"### {idx}. {task.title or task.task_description or 'Untitled'}",
            "",
            f"- 状态：{task.status or 'unknown'}",
            f"- 项目：{task.project or 'unknown'}",
            f"- 来源：{getattr(task, 'source', 'unknown')}",
        ])
        canon_file = getattr(task, "canon_file", "")
        if canon_file:
            lines.append(f"- Canon：`{canon_file}`")
        if task.task_description and task.task_description != task.title:
            lines.extend(["", "任务描述：", task.task_description])
        if task.actions:
            lines.extend(["", "动作/线索："])
            lines.extend([f"- {item}" for item in _short_lines(task.actions)])
        if task.files_modified:
            lines.extend(["", "相关文件："])
            lines.extend([f"- `{item}`" for item in _short_lines(task.files_modified, 10)])
        if task.result and task.result != "Canon task page is the primary weekly work source.":
            lines.extend(["", "Session 结果线索：", task.result])
        lines.append("")

    lines.extend(["## Session-only 候选素材", ""])
    if not session_only:
        lines.append("- 无额外 session-only 工作候选。")
        lines.append("")
    for idx, task in enumerate(session_only, 1):
        title = task.task_description or task.title or "Untitled"
        lines.extend([
            f"### S{idx}. {title}",
            "",
            f"- 状态：{task.status or 'unknown'}",
            f"- 项目：{task.project or 'unknown'}",
            f"- Agent：{task.agent or 'unknown'}",
            f"- Prompts/Responses：{task.total_prompts}/{task.total_responses}",
        ])
        if task.files_modified:
            lines.extend(["", "相关文件："])
            lines.extend([f"- `{item}`" for item in _short_lines(task.files_modified, 10)])
        snippet = task.conversation_text(max_length=1200).strip()
        if snippet:
            lines.extend(["", "原始对话摘录：", "```text", snippet, "```"])
        lines.append("")

    lines.extend([
        "## 使用说明",
        "",
        "- 手写周报时只取确认为业务交付的内容。",
        "- 不要直接把本文件当最终周报发送。",
        "- 若任务不该进入周报，改对应 Canon task 的 `report_scope` / `weekly` 字段。",
        "",
    ])
    return "\n".join(lines)


def send_materials_link(url: str, since: datetime, until: datetime) -> bool:
    r = subprocess.run(
        ["dws", "contact", "user", "search", "--query", "袁浩然", "--format", "json"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"搜索用户失败: {r.stderr}")
        return False
    users = json.loads(r.stdout).get("result", [])
    if not users:
        print("未找到用户，无法发送消息")
        return False
    my_id = users[0]["userId"]

    week_label = f"{since.strftime('%-m/%-d')}-{until.strftime('%-m/%-d')}"
    msg_cmd = [
        "dws",
        "chat",
        "message",
        "send",
        "--user",
        my_id,
        "--title",
        f"周报参考素材 {week_label}",
        "--text",
        f"本周周报参考素材已生成（不是最终周报，不需要 checklist 确认）：\n\n{url}",
        "--format",
        "json",
    ]
    r2 = subprocess.run(msg_cmd, capture_output=True, text=True)
    if r2.returncode != 0:
        print(f"发送消息失败: {r2.stderr}")
        return False
    if r2.stdout.strip():
        try:
            data = json.loads(r2.stdout)
        except json.JSONDecodeError:
            data = {}
        if data.get("success") is False:
            print(f"发送消息失败: {data}")
            return False
    return True


def main():
    dry_run = "--dry-run" in sys.argv
    since, until = _parse_range(sys.argv[1:])
    print(f"[weekly_materials] {datetime.now():%Y-%m-%d %H:%M:%S}")
    print(f"范围: {since.strftime('%Y-%m-%d')} → {until.strftime('%Y-%m-%d')}")

    canon_tasks = collect_canon_tasks(since, until)
    work_canon_tasks = _select_work_canon_tasks(canon_tasks)
    print(f"Canon 工作任务: {len(work_canon_tasks)} 项")

    sessions = collect_all_sessions(since, until)
    print(f"原始 session: {len(sessions)} 个")
    session_tasks = filter_by_topic(cluster_sessions(sessions), "工作") if sessions else []
    print(f"session 工作候选: {len(session_tasks)} 项")

    tasks = []
    matched_session_ids = set()
    for ct in work_canon_tasks:
        task = _canon_task_to_report_task(ct)
        matched, score = _match_session_task(task, session_tasks)
        if matched:
            task = _merge_session_evidence(task, matched)
            matched_session_ids.add(matched.task_id)
            print(f"Canon + session evidence: {ct['title'][:50]}... score={score:.2f}")
        tasks.append(task)

    session_only = [t for t in session_tasks if t.task_id not in matched_session_ids]
    materials = build_materials_md(tasks, session_only, since, until, len(sessions))

    report_dir = get_report_dir()
    report_dir.mkdir(parents=True, exist_ok=True)
    materials_path = report_dir / f"weekly-materials-{until.strftime('%Y-%m-%d')}.md"
    materials_path.write_text(materials, encoding="utf-8")
    print(f"参考素材已保存: {materials_path}")

    if dry_run:
        print("[dry-run] 跳过钉钉操作")
        return

    title = f"周报参考素材 · {since.strftime('%-m/%-d')} - {until.strftime('%-m/%-d')}"
    node_id, url = create_dingtalk_doc(materials, title)
    print(f"文档已创建: {url}")

    meta_dir = Path.home() / ".agents" / "work-reports" / ".materials"
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "nodeId": node_id,
        "url": url,
        "week_start": since.isoformat(),
        "week_end": until.isoformat(),
        "path": str(materials_path),
        "type": "weekly_materials",
    }
    meta_path = meta_dir / f"materials-{until.strftime('%Y-%m-%d')}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"元数据已保存: {meta_path}")

    if not send_materials_link(url, since, until):
        print("链接发送失败")
        sys.exit(1)
    print("链接已发送 ✓")


if __name__ == "__main__":
    main()
