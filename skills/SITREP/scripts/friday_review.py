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
from generate_work_report import collect_all_sessions, _check_llm_availability, filter_by_topic
from task_clustering import Task, cluster_sessions, merge_by_star_similarity
from star_builder import build_stars_for_tasks
from collectors.canon_collector import collect_canon_tasks


def get_friday_week_range() -> tuple[datetime, datetime]:
    """本周一 00:00 → 当前时间（local-aware）。"""
    from common_wr import LOCAL_TZ
    now = datetime.now(LOCAL_TZ)
    monday = now - timedelta(days=now.weekday())
    since = monday.replace(hour=0, minute=0, second=0, microsecond=0)
    return since, now


def _canon_task_to_report_task(ct: dict) -> Task:
    """Convert a Canon task page into the primary weekly report task."""
    task = Task(
        task_id=f"canon-{Path(ct['source_file']).stem}",
        title=ct.get("weekly_title") or ct["title"],
        task_description=ct["objective"] or ct.get("weekly_title") or ct["title"],
        status=ct["status"],
        project=ct["project"],
        start_time=ct.get("modified_at"),
        end_time=ct.get("modified_at"),
    )
    setattr(task, "source", "canon")
    setattr(task, "canon_file", ct.get("source_file", ""))
    task.actions = [c["text"] for c in ct.get("checklist", [])]
    task.result = "Canon task page is the primary weekly work source."
    return task


def _select_work_canon_tasks(canon_tasks: list[dict]) -> list[dict]:
    """Select Canon tasks for the weekly work checklist.

    Decision: only tasks with report_scope: work + weekly: true are included.
    The legacy topic-matching fallback has been removed — it was too broad
    (matched any CarlaUE5 task via topics.yaml).
    """
    selected = []
    excluded = []
    for ct in canon_tasks:
        include, reason = _canon_task_report_decision(ct)
        ct["_sitrep_decision"] = reason
        if include:
            selected.append(ct)
        else:
            excluded.append(ct)

    if excluded:
        print(f"Canon tasks excluded from 工作 checklist: {len(excluded)} 项")
        for ct in excluded[:8]:
            print(f"  - {ct['title'][:50]}... [{ct.get('_sitrep_decision')}]")
    return selected


def _match_session_task(canon_task: Task, session_tasks: list[Task]) -> tuple[Task | None, float]:
    """Find the best session evidence for a Canon task."""
    canon_text = " ".join([
        canon_task.title or "",
        canon_task.task_description or "",
        canon_task.project or "",
    ]).lower()
    best_task = None
    best_score = 0.0
    for st in session_tasks:
        session_text = " ".join([
            st.title or "",
            st.task_description or "",
            st.project or "",
            st.result or "",
        ]).lower()
        score = _title_similarity(canon_text, session_text)
        if score > best_score:
            best_task = st
            best_score = score
    return (best_task, best_score) if best_score >= 0.28 else (None, best_score)


def _merge_session_evidence(canon_task: Task, session_task: Task) -> Task:
    """Keep Canon title/status/objective, enrich with session evidence."""
    canon_title = canon_task.title
    canon_description = canon_task.task_description
    canon_status = canon_task.status
    canon_actions = list(canon_task.actions)
    canon_situation = canon_task.situation
    canon_result = canon_task.result
    canon_files_modified = list(canon_task.files_modified)

    canon_task.sessions = session_task.sessions
    canon_task.agent = session_task.agent
    canon_task.start_time = session_task.start_time or canon_task.start_time
    canon_task.end_time = session_task.end_time or canon_task.end_time
    canon_task.files_modified = session_task.files_modified
    canon_task.total_events = session_task.total_events
    canon_task.total_prompts = session_task.total_prompts
    canon_task.total_responses = session_task.total_responses
    canon_task.situation = session_task.situation
    if session_task.result:
        canon_task.result = session_task.result
    if session_task.actions:
        seen = set(canon_actions)
        for action in session_task.actions:
            if action not in seen:
                canon_actions.append(action)
                seen.add(action)
    canon_task.actions = canon_actions

    canon_task.title = canon_title
    canon_task.task_description = canon_description
    canon_task.status = canon_status
    setattr(canon_task, "_canon_situation", canon_situation)
    setattr(canon_task, "_canon_actions", canon_actions)
    setattr(canon_task, "_canon_result", canon_result)
    setattr(canon_task, "_canon_files_modified", canon_files_modified)
    setattr(canon_task, "source", "canon+session")
    return canon_task


def _build_canon_first_tasks(canon_tasks: list[dict], session_tasks: list[Task]) -> list[Task]:
    """Canon decides the weekly work set; sessions only enrich evidence."""
    work_canon_tasks = _select_work_canon_tasks(canon_tasks)
    if not work_canon_tasks:
        print("Canon tasks: 0 项，fallback 到 session tasks")
        return session_tasks

    result: list[Task] = []
    matched_session_ids: set[str] = set()
    print(f"Canon tasks: {len(work_canon_tasks)} 项（主任务源）")
    for ct in work_canon_tasks:
        task = _canon_task_to_report_task(ct)
        matched, score = _match_session_task(task, session_tasks)
        if matched:
            task = _merge_session_evidence(task, matched)
            matched_session_ids.add(matched.task_id)
            print(f"  Canon 主项 + session evidence: {ct['title'][:50]}... score={score:.2f}")
        else:
            print(f"  Canon 主项: {ct['title'][:50]}... → {ct['status']}")
        result.append(task)

    if os.environ.get("SITREP_INCLUDE_SESSION_ONLY") != "0":
        session_only = [t for t in session_tasks if t.task_id not in matched_session_ids]
        # Filter noise: tasks with very short or clearly incomplete titles
        # (e.g. fragments like "现在有一个痛点" that aren't full task descriptions)
        noise_keywords = ["现在有一个", "帮我看", "帮我看一下", "有个问题", "看一下", "帮我"]
        filtered = []
        for t in session_only:
            title = (t.task_description or t.title or "").strip()
            if len(title) < 15 and any(kw in title for kw in noise_keywords):
                print(f"  [noise filtered] {title[:50]}...")
                continue
            filtered.append(t)
        result.extend(filtered)
        if filtered:
            print(f"Session-only 工作补充: {len(filtered)} 项")
    return result


def _canon_task_report_decision(ct: dict) -> tuple[bool, str]:
    scope = (ct.get("report_scope") or "").strip().lower()
    weekly = ct.get("weekly")

    if scope in {"infra", "personal", "ignore"}:
        return False, f"report_scope:{scope}"
    if scope == "work":
        if weekly is True:
            return True, "report_scope:work+weekly:true"
        if weekly is False:
            return False, "report_scope:work+weekly:false"
        return False, "report_scope:work+weekly:missing"

    # No report_scope field: strictly excluded.
    # The legacy topic-matching fallback has been removed — authors must
    # explicitly set report_scope: work + weekly: true to appear.
    return False, "no-report-scope"


def _title_similarity(a: str, b: str) -> float:
    """简单的字符集 Jaccard 相似度。"""
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0
    return len(sa & sb) / len(sa | sb)


def _load_previous_checklist_tasks() -> dict:
    """Load tasks from the most recent previous checklist JSON.

    Returns {"unchecked": [...], "completed": [...], "confirmed": bool}.
    Unchecked tasks → carry-over candidates.
    Completed tasks → suppress from this week's Canon list (already done).
    Prefers Sunday-confirmed checklists over Friday originals.
    """
    import glob
    meta_dir = Path.home() / ".agents" / "work-reports" / ".checklist"
    if not meta_dir.exists():
        return {"unchecked": [], "completed": [], "confirmed": False}

    files = sorted(glob.glob(str(meta_dir / "checklist-*.json")), reverse=True)
    for fpath in files:
        try:
            data = json.loads(Path(fpath).read_text(encoding="utf-8"))
        except Exception:
            continue
        tasks = data.get("tasks", [])
        if not tasks:
            continue
        is_confirmed = data.get("confirmed", False)
        unchecked = [t for t in tasks if t.get("status") != "completed"]
        completed = [t for t in tasks if t.get("status") == "completed"]
        source = "已确认" if is_confirmed else "未确认"
        print(f"读取上周 checklist ({source}): {len(unchecked)} 未完成 + {len(completed)} 已完成")
        return {"unchecked": unchecked, "completed": completed, "confirmed": is_confirmed}
    return {"unchecked": [], "completed": [], "confirmed": False}


def _suppress_completed_from_canon(
    canon_tasks: list[dict],
    completed_last_week: list[dict],
) -> list[dict]:
    """Remove Canon tasks that were completed on last week's checklist.

    Matches by canon_file (precise) — only tasks with a matching Canon file
    are suppressed. Session-only tasks from last week never suppress Canon tasks.
    """
    if not completed_last_week:
        return canon_tasks

    completed_files = set()
    for cl in completed_last_week:
        cf = cl.get("canon_file", "")
        if cf:
            completed_files.add(cf)

    if not completed_files:
        return canon_tasks

    suppressed = []
    kept = []
    for ct in canon_tasks:
        ct_file = ct.get("source_file", "")
        if ct_file and ct_file in completed_files:
            suppressed.append(ct)
        else:
            kept.append(ct)

    if suppressed:
        print(f"上周已完成，本周压制: {len(suppressed)} 项")
        for s in suppressed[:5]:
            print(f"  - {s['title'][:50]}...")
    return kept


def _merge_carry_over_tasks(
    tasks: list[Task],
    canon_tasks: list[dict],
    carry_over: list[dict],
) -> list[Task]:
    """Add carry-over items, deduplicating against existing Canon and session tasks.

    Layer 1 (Canon) and Layer 2 (session) take priority. Carry-over items
    only added if they don't match any existing task by title similarity.
    """
    if not carry_over:
        return tasks

    # Build existing title set for dedup (use title first, then description)
    existing_titles = []
    for t in tasks:
        title = _normalize_for_checklist(t.title or t.task_description or "")
        existing_titles.append(title)

    added = 0
    for co in carry_over:
        co_title = _normalize_for_checklist(co.get("title", ""))
        if not co_title:
            continue

        # Check if this carry-over item already has a current task
        is_duplicate = False
        for et in existing_titles:
            if _title_similarity(co_title, et) >= 0.30:
                is_duplicate = True
                break
        if is_duplicate:
            continue

        # Create a carry-over task
        task = Task(
            task_id=f"carryover-{added}",
            title=co.get("title", ""),
            task_description=co.get("title", ""),
            status=co.get("status", "in_progress"),
            project="(carry-over)",
        )
        setattr(task, "source", "carry-over")
        task.result = "从上周 checklist 带入，状态未确认。"
        tasks.append(task)
        existing_titles.append(co_title)
        added += 1

    if added:
        print(f"上周 carry-over 补充: {added} 项")
    return tasks


def _normalize_for_checklist(title: str) -> str:
    """Normalize title for comparison (remove punctuation, lowercase)."""
    import re
    return re.sub(r'[\s.,;:!?·，。；：！？、""''\(\)\[\]【】]', '', title.lower())


def build_checklist_md(tasks, since, until) -> str:
    """生成清单 markdown。数字前缀：1=本周完成 2=进行中 3=跳过。"""
    lines = [f"# 周报确认 · {since.strftime('%-m/%-d')} - {until.strftime('%-m/%-d')}", ""]
    lines.append("> 1=本周完成 / 2=进行中 / 3=跳过")
    lines.append("")
    for i, t in enumerate(tasks, 1):
        status = t.status
        title = t.task_description or t.title if not str(getattr(t, "source", "")).startswith("canon") else t.title
        if status == "completed":
            lines.append(f"1 {title}")
        else:
            lines.append(f"2 {title}")
    lines.append("")
    lines.append("1 发送本周周报")
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


def send_dingtalk_link(url: str, since: datetime, until: datetime) -> bool:
    """以个人身份给自己发钉钉消息。"""
    # 查找自己的 userId
    r = subprocess.run(["dws", "contact", "user", "search", "--query", "袁浩然", "--format", "json"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"搜索用户失败: {r.stderr}")
        return False
    users = json.loads(r.stdout).get("result", [])
    if not users:
        print("未找到用户，无法发送消息")
        return False
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
        return False
    try:
        data = json.loads(r2.stdout) if r2.stdout.strip() else {}
    except json.JSONDecodeError:
        data = {}
    if data and data.get("success") is False:
        print(f"发送消息失败: {data}")
        return False
    return True


def main():
    dry_run = "--dry-run" in sys.argv
    skip_llm = "--no-llm" in sys.argv or os.environ.get("SITREP_SKIP_LLM") == "1"

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

    # 2. Canon-first: Canon defines the weekly work set.
    canon_tasks = collect_canon_tasks(since, until)
    print(f"Canon tasks: {len(canon_tasks)} 项")

    # 3. Sessions are evidence/enrichment, not the primary task list.
    sessions = collect_all_sessions(since, until)
    print(f"共 {len(sessions)} 个 session")

    session_tasks: list[Task] = []
    if sessions:
        session_tasks = cluster_sessions(sessions)
        print(f"session 聚类提取 {len(session_tasks)} 个候选任务")

        if skip_llm:
            print("跳过 LLM STAR 提取，使用基础状态")
        else:
            llm_ok, reason = _check_llm_availability()
            if llm_ok:
                print("LLM STAR 提取中...")
                session_tasks = build_stars_for_tasks(session_tasks, use_cache=True, quiet=False)
                session_tasks = merge_by_star_similarity(session_tasks, rule_threshold=0.02, quiet=False)
                print(f"STAR+去重后 {len(session_tasks)} 个候选任务")
            else:
                print(f"LLM 不可用 ({reason})，使用基础状态")

        session_tasks = filter_by_topic(session_tasks, "工作")
        print(f"session 工作候选过滤后 {len(session_tasks)} 个任务")

    # Layer 0: Load last week's confirmed checklist for carry-over + suppression
    prev = _load_previous_checklist_tasks()
    completed_last_week = prev.get("completed", [])
    unchecked_last_week = prev.get("unchecked", [])

    # Suppress Canon tasks that were completed on last week's checklist
    if completed_last_week:
        canon_tasks = _suppress_completed_from_canon(canon_tasks, completed_last_week)
        print(f"压制后 Canon tasks: {len(canon_tasks)} 项")

    tasks = _build_canon_first_tasks(canon_tasks, session_tasks)
    print(f"Canon-first 输出 {len(tasks)} 个任务")

    # Layer 3: Carry-over unchecked items from last week's checklist
    if unchecked_last_week:
        print(f"上周未完成任务: {len(unchecked_last_week)} 项")
        tasks = _merge_carry_over_tasks(tasks, canon_tasks, unchecked_last_week)
        print(f"carry-over 合并后 {len(tasks)} 个任务")
    if not tasks:
        print("本周无 Canon task 或 session 工作候选，跳过。")
        return

    # 6. 生成 checklist
    checklist = build_checklist_md(tasks, since, until)
    title = f"周报确认 · {since.strftime('%-m/%-d')} - {until.strftime('%-m/%-d')}"
    print(f"\n=== Checklist ===\n{checklist}\n================")

    # 6. 保存完整报告到本地（必生成）
    from report_renderer import render_weekly_report, save_report
    report_md = render_weekly_report(tasks, since, until, artifact_mode="audit")
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

    # 保存 checklist 元数据 + 任务列表供下周五 carry-over
    meta_dir = Path.home() / ".agents" / "work-reports" / ".checklist"
    meta_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "nodeId": node_id,
        "url": url,
        "week_start": since.isoformat(),
        "week_end": until.isoformat(),
        "tasks": [
            {
                "title": t.title,
                "canon_file": str(getattr(t, "canon_file", "")),
                "status": t.status,
                "source": str(getattr(t, "source", "unknown")),
            }
            for t in tasks
        ],
    }
    meta_path = meta_dir / f"checklist-{until.strftime('%Y-%m-%d')}.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    print(f"元数据已保存: {meta_path}")

    if not send_dingtalk_link(url, since, until):
        print("链接发送失败")
        sys.exit(1)
    print("链接已发送 ✓")


if __name__ == "__main__":
    main()
