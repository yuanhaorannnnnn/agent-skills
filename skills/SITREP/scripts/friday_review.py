#!/usr/bin/env python3
"""Friday 18:00 — 生成 Checklist 钉钉文档，发链接给用户确认。

用法:
  python3 friday_review.py [--dry-run]
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common_wr import get_report_dir
from generate_work_report import collect_all_sessions, _check_llm_availability, load_topics, filter_by_topic
from task_clustering import cluster_sessions, merge_by_star_similarity
from star_builder import build_stars_for_tasks


def get_friday_week_range() -> tuple[datetime, datetime]:
    """本周一 00:00 → 今天（周五）当前时间。"""
    now = datetime.now()
    monday = now - timedelta(days=now.weekday())  # ISO: Mon=0, Sun=6
    since = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return since, now


def build_checklist_md(tasks, since, until) -> str:
    """生成极简 checklist markdown。"""
    lines = [f"# 周报确认 · {since.strftime('%-m/%-d')} - {until.strftime('%-m/%-d')}", ""]
    for i, t in enumerate(tasks, 1):
        status = t.status
        checked = "x" if status == "completed" else " "
        title = (t.task_description or t.title)[:120]
        lines.append(f"- [{checked}] {title}")
    lines.append("")
    lines.append("- [x] 发送本周周报")
    return "\n".join(lines)


def create_dingtalk_doc(content: str, title: str, folder: str = None) -> str:
    """创建钉钉文档，返回 nodeId。"""
    cmd = ["dws", "doc", "create", "--name", title, "--markdown", content, "--format", "json"]
    if folder:
        cmd.extend(["--folder", folder])
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"创建文档失败: {r.stderr}")
        sys.exit(1)
    data = json.loads(r.stdout)
    node_id = data.get("nodeId", "")
    url = data.get("docUrl", "")
    if not node_id:
        print(f"创建文档失败，无 nodeId: {data}")
        sys.exit(1)
    return node_id, url


def send_dingtalk_link(url: str) -> None:
    """以个人身份给自己发钉钉消息。"""
    # 查找自己的 userId
    r = subprocess.run(["dws", "contact", "user", "search", "--query", "袁浩然", "--format", "json"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"搜索用户失败: {r.stderr}")
        # 不 fatal，只是发不了消息
        return
    users = json.loads(r.stdout).get("result", [])
    if not users:
        print("未找到用户，跳过发送消息")
        return
    my_id = users[0]["userId"]

    # 发消息
    week_label = f"{since.strftime('%-m/%-d')}-{until.strftime('%-m/%-d')}"
    msg_cmd = [
        "dws", "chat", "message", "send",
        "--user", my_id,
        "--title", f"周报确认 {week_label}",
        "--text", f"请确认本周工作状态（{week_label}）：\n\n{url}",
        "--format", "json",
    ]
    r2 = subprocess.run(msg_cmd, capture_output=True, text=True)
    if r2.returncode != 0:
        print(f"发送消息失败: {r2.stderr}")


def main():
    dry_run = "--dry-run" in sys.argv

    # 支持自定义日期范围: --since YYYY-MM-DD --until YYYY-MM-DD
    since, until = None, None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == "--since" and i + 1 < len(args):
            since = datetime.strptime(args[i+1], "%Y-%m-%d")
        if arg == "--until" and i + 1 < len(args):
            until = datetime.strptime(args[i+1], "%Y-%m-%d")

    print(f"[friday_review] {datetime.now():%Y-%m-%d %H:%M:%S}")

    # 1. 日期范围
    if since and until:
        since = since.replace(hour=0, minute=0, second=0, microsecond=0)
        until = until.replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        since, until = get_friday_week_range()
    print(f"范围: {since.strftime('%Y-%m-%d')} → {until.strftime('%Y-%m-%d')}")

    # 2. 收集 sessions
    sessions = collect_all_sessions(since, until)
    if not sessions:
        print("本周无 session，跳过。")
        return
    print(f"共 {len(sessions)} 个 session")

    # 3. 聚类
    tasks = cluster_sessions(sessions)
    print(f"提取 {len(tasks)} 个任务")

    # 4. STAR 提取
    llm_ok, reason = _check_llm_availability()
    if llm_ok:
        print("LLM STAR 提取中...")
        tasks = build_stars_for_tasks(tasks, use_cache=True, quiet=False)
        tasks = merge_by_star_similarity(tasks, rule_threshold=0.05, quiet=False)
        print(f"STAR+去重后 {len(tasks)} 个任务")
    else:
        print(f"LLM 不可用 ({reason})，使用基础状态")

    # 5. 按「工作」主题过滤
    tasks = filter_by_topic(tasks, "工作")
    print(f"过滤后 {len(tasks)} 个任务")

    # 5. 生成 checklist
    checklist = build_checklist_md(tasks, since, until)
    title = f"周报确认 · {since.strftime('%-m/%-d')} - {until.strftime('%-m/%-d')}"
    print(f"\n=== Checklist ===\n{checklist}\n================")

    # 6. 保存完整报告到本地（必生成）
    from report_renderer import render_weekly_report, save_report
    report_md = render_weekly_report(tasks, since, until)
    report_dir = get_report_dir()
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"weekly-{until.strftime('%Y-%m-%d')}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_md, encoding="utf-8")
    print(f"完整周报已保存: {report_path}")

    # 7. 创建钉钉文档 + 发链接
    if dry_run:
        print("[dry-run] 跳过钉钉操作")
        return

    node_id, url = create_dingtalk_doc(checklist, title)
    print(f"文档已创建: {url}")

    # 保存 checklist 元数据供 sunday_finalize 读回
    meta_dir = Path.home() / ".agents" / "work-reports" / ".checklist"
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta = {"nodeId": node_id, "url": url, "week_start": since.isoformat(), "week_end": until.isoformat()}
    meta_path = meta_dir / f"checklist-{until.strftime('%Y-%m-%d')}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"元数据已保存: {meta_path}")

    send_dingtalk_link(url)
    print("链接已发送 ✓")


if __name__ == "__main__":
    main()
