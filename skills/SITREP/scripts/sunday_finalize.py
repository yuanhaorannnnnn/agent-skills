#!/usr/bin/env python3
"""Sunday 23:00 — 读回 checklist 文档，应用用户确认，生成/提交周报。

用法:
  python3 sunday_finalize.py [--dry-run]
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common_wr import get_report_dir


def find_checklist_meta(since, until) -> dict:
    """查找同一 week_start 内最新的 checklist 元数据文件。"""
    meta_dir = Path.home() / ".agents" / "work-reports" / ".checklist"
    if not meta_dir.exists():
        return None

    target_start = since.date()
    candidates = []
    for meta_path in meta_dir.glob("checklist-*.json"):
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            week_start = datetime.fromisoformat(meta.get("week_start", meta.get("since", ""))).date()
            week_end_raw = meta.get("week_end", meta.get("until", ""))
            week_end = datetime.fromisoformat(week_end_raw) if week_end_raw else datetime.fromtimestamp(meta_path.stat().st_mtime)
        except Exception as exc:
            print(f"跳过无效 checklist 元数据 {meta_path.name}: {exc}")
            continue
        if week_start == target_start:
            candidates.append((week_end, meta_path.stat().st_mtime, meta_path, meta))

    if not candidates:
        return None
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    _, _, meta_path, meta = candidates[0]
    print(f"使用本工作周最新 checklist: {meta_path.name}")
    return meta


def fetch_checklist_md(node_id: str) -> str:
    """从钉钉文档读取 checklist markdown 内容。"""
    r = subprocess.run(["dws", "doc", "read", "--node", node_id, "--format", "json"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"读取文档失败: {r.stderr}")
        return None
    data = json.loads(r.stdout)
    return data.get("markdown", "") or data.get("content", "") or data.get("text", "")


def parse_checklist(md: str) -> dict:
    """解析 checklist markdown，返回任务状态和发送标记。

    数字前缀格式（当前），兼容旧 emoji/checkbox 格式：
      1 / ✅ / [x]     → completed（本周已完成）
      2 / ⬜ / [ ]     → in_progress（本周未完成）
      3 / ➖ / [-]     → excluded（之前已完成，不纳入本周）
    """
    tasks = []
    send = False

    lines = md.strip().split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith(">"):
            continue

        title = None
        status = None

        # Number prefix: 1/2/3
        m = re.match(r"^([123])\s+(.+)", stripped)
        if m:
            marker = m.group(1)
            title = m.group(2).strip()
            status = {"1": "completed", "2": "in_progress", "3": "excluded"}[marker]
        else:
            # Emoji format
            for emoji, st in [("✅", "completed"), ("⬜", "in_progress"), ("➖", "excluded")]:
                if stripped.startswith(emoji):
                    title = stripped[1:].strip()
                    status = st
                    break
        if title is None:
            # Legacy checkbox format
            m = re.match(r"^(?:-\s+)?\[(x| |-)\]\s+(.*)", stripped)
            if m:
                marker = m.group(1)
                title = m.group(2).strip()
                status = "completed" if marker == "x" else ("excluded" if marker == "-" else "in_progress")

        if not title or "发送" in title and "周报" in title:
            if status == "completed" and "发送" in title:
                send = True
            continue

        if status:
            tasks.append({"title": title, "user_status": status})

    if not send:
        for line in reversed(lines):
            s = line.strip()
            if "发送" in s and "周报" in s:
                send = s.startswith("1") or "✅" in s or "[x]" in s
                break

    return {"tasks": tasks, "send": send}


def match_task_by_title(checklist_task: dict, report_tasks: list) -> object:
    """用任务标题子串匹配。返回匹配度最高的 report task，或 None。"""
    ct = checklist_task["title"]
    best, best_score = None, 0
    for rt in report_tasks:
        rt_text = (rt.task_description or rt.title or "")
        # Jaccard-like: 共享字符集比例
        a, b = set(ct.lower()), set(rt_text.lower())
        if not a or not b:
            continue
        score = len(a & b) / len(a)
        if score > best_score:
            best, best_score = rt, score
    return best if best_score > 0.3 else None


def apply_overrides(tasks: list, checklist_data: dict):
    """Use the confirmed checklist as the final task set.

    Three-state handling:
      [x] completed   → include in report
      [ ] in_progress → include in report
      [-] excluded    → exclude from report (previously done, not this week)
    """
    from task_clustering import Task

    ctasks = checklist_data["tasks"]
    final_tasks = []
    applied = 0
    added = 0
    excluded = 0
    for ct in ctasks:
        if ct["user_status"] == "excluded":
            excluded += 1
            continue

        matched = match_task_by_title(ct, tasks)
        if matched:
            matched.status = ct["user_status"]
            matched.title = ct["title"]
            matched.task_description = ct["title"]
            final_tasks.append(matched)
            applied += 1
        else:
            final_tasks.append(Task(
                task_id=f"checklist-{added + 1}",
                title=ct["title"],
                task_description=ct["title"],
                status=ct["user_status"],
                project="checklist",
            ))
            added += 1
    dropped = max(len(tasks) - applied, 0)
    print(f"状态覆盖: {applied}/{len(ctasks)} 项匹配, {added} 项新增, {excluded} 项排除, {dropped} 项 session-only 丢弃")
    return final_tasks


def generate_and_submit(tasks, since, until, should_send: bool, dry_run: bool):
    """生成完整周报，保存本地，可选提交钉钉。"""
    from report_renderer import render_weekly_report, save_report

    report_md = render_weekly_report(tasks, since, until)
    report_dir = get_report_dir()
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"weekly-{until.strftime('%Y-%m-%d')}.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"周报已保存: {report_path}")

    if not should_send:
        print("用户标记「不发」，跳过提交")
        return

    if dry_run:
        print("[dry-run] 将提交钉钉周报")
        return

    # 提交钉钉周报
    submit_script = _SCRIPT_DIR / "submit_dingtalk_report.py"
    if submit_script.exists():
        r = subprocess.run(
            ["python3", str(submit_script), "--report", str(report_path)],
            capture_output=True, text=True,
        )
        if r.returncode == 0:
            print("钉钉周报提交成功 ✓")
        else:
            print(f"提交失败: {r.stderr or r.stdout}")
            raise SystemExit(r.returncode)
    else:
        print("submit_dingtalk_report.py 不存在，无法提交")
        raise SystemExit(1)


def main():
    dry_run = "--dry-run" in sys.argv
    skip_llm = "--no-llm" in sys.argv or os.environ.get("SITREP_SKIP_LLM") == "1"
    print(f"[sunday_finalize] {datetime.now():%Y-%m-%d %H:%M:%S}")

    # 1. 确定周范围，支持补发指定周期: --since YYYY-MM-DD --until YYYY-MM-DD
    args = sys.argv[1:]
    since_arg = None
    until_arg = None
    for i, arg in enumerate(args):
        if arg == "--since" and i + 1 < len(args):
            since_arg = args[i + 1]
        if arg == "--until" and i + 1 < len(args):
            until_arg = args[i + 1]

    if since_arg and until_arg:
        since = datetime.strptime(since_arg, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)
        until = datetime.strptime(until_arg, "%Y-%m-%d").replace(hour=23, minute=59, second=59, microsecond=999999)
    else:
        now = datetime.now()
        since = now - timedelta(days=now.weekday())
        since = since.replace(hour=0, minute=0, second=0, microsecond=0)
        until = since + timedelta(days=6, hours=23, minutes=59, seconds=59)

    meta = find_checklist_meta(since, until)

    if not meta:
        print("无 checklist 元数据，跳过")
        return

    # 2. 读回 checklist 文档
    md = fetch_checklist_md(meta["nodeId"])
    if not md:
        print("无法读取 checklist 文档，跳过")
        return

    print(f"读取 checklist ({len(md)} 字符)")

    # 3. 解析
    checklist_data = parse_checklist(md)
    print(f"解析: {len(checklist_data['tasks'])} 项任务, 发送={'是' if checklist_data['send'] else '否'}")

    if not dry_run:
        for t in checklist_data["tasks"]:
            print(f"  [{'x' if t['user_status']=='completed' else ' '}] {t['title'][:80]}")

    # 4. 加载本地报告的任务
    from task_clustering import Task
    report_dir = get_report_dir()
    report_path = report_dir / f"weekly-{meta['week_end'][:10]}.md" if meta.get("week_end") else None
    if not report_path or not report_path.exists():
        print(f"周报文件不存在: {report_path}")
        return

    # 5. 重新采集 + 聚类 + STAR 得到完整 Task 对象（带 session 信息）
    since_dt = datetime.fromisoformat(meta.get("week_start", meta.get("since", since.isoformat())))
    until_dt = datetime.fromisoformat(meta.get("week_end", meta.get("until", until.isoformat())))
    from generate_work_report import collect_all_sessions, _check_llm_availability
    from task_clustering import cluster_sessions
    from star_builder import build_stars_for_tasks

    sessions = collect_all_sessions(since_dt, until_dt)
    if not sessions:
        print("无 session 数据")
        return
    tasks = cluster_sessions(sessions)
    if skip_llm:
        print("跳过 LLM STAR 提取，使用基础状态")
    else:
        llm_ok, _ = _check_llm_availability()
        if llm_ok:
            tasks = build_stars_for_tasks(tasks, use_cache=True, quiet=True)

    # 6. 覆盖用户确认状态
    tasks = apply_overrides(tasks, checklist_data)

    # 7. 回写确认状态到 checklist JSON，供下周五 carry-over
    meta_path = Path.home() / ".agents" / "work-reports" / ".checklist"
    for candidate in meta_path.glob("checklist-*.json"):
        try:
            existing = json.loads(candidate.read_text(encoding="utf-8"))
            if existing.get("week_start") == meta.get("week_start"):
                confirmed_tasks = []
                # Tasks from the confirmed checklist (applied to session tasks)
                for t in tasks:
                    confirmed_tasks.append({
                        "title": t.task_description or t.title,
                        "canon_file": str(getattr(t, "canon_file", "")),
                        "status": t.status,
                        "source": "confirmed",
                    })
                # Excluded items ([ - ]) → saved as completed for carry-over suppression
                for ct in checklist_data["tasks"]:
                    if ct.get("user_status") == "excluded":
                        confirmed_tasks.append({
                            "title": ct["title"],
                            "canon_file": "",
                            "status": "completed",
                            "source": "excluded",
                        })
                # Deleted from DingTalk doc → implicitly completed
                user_kept_titles = set()
                for ct in checklist_data["tasks"]:
                    user_kept_titles.add(ct.get("title", "").strip())
                deleted_count = 0
                for orig in existing.get("tasks", []):
                    orig_title = orig.get("title", "").strip()
                    if orig_title and orig_title not in user_kept_titles:
                        confirmed_tasks.append({
                            "title": orig_title,
                            "canon_file": orig.get("canon_file", ""),
                            "status": "completed",
                            "source": "deleted",
                        })
                        deleted_count += 1
                if deleted_count:
                    print(f"已删除项标记完成: {deleted_count} 项")
                existing["tasks"] = confirmed_tasks
                existing["confirmed"] = True
                candidate.write_text(json.dumps(existing, ensure_ascii=False, indent=2))
                print(f"确认状态已回写: {candidate.name}")
                break
        except Exception:
            continue

    # 8. 生成 + 提交
    generate_and_submit(tasks, since_dt, until_dt, checklist_data["send"], dry_run)


if __name__ == "__main__":
    main()
