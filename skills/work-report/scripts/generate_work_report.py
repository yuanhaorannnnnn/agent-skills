#!/usr/bin/env python3
"""Main CLI for generating work reports from coding agent conversations."""

import argparse
import contextlib
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Ensure scripts directory is in path
_SCRIPT_DIR = Path(__file__).parent.resolve()
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from common_wr import get_week_range, get_month_range, get_report_dir
from collectors.claude_collector import collect_claude_sessions
from collectors.codex_collector import collect_codex_sessions
from collectors.kimi_collector import collect_kimi_sessions
from task_clustering import cluster_sessions, merge_by_star_similarity
from star_builder import build_stars_for_tasks
from report_renderer import render_weekly_report, save_report


def _setup_auto_logging() -> Path:
    """Set up logging file for --auto mode."""
    log_dir = Path.home() / ".agents" / "work-reports" / ".logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"auto-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
    return log_path


def _check_llm_availability() -> tuple[bool, str]:
    """Check if LLM API is available for STAR extraction.

    Returns (available, reason).
    """
    try:
        import anthropic
    except ImportError:
        return False, "anthropic SDK not installed (pip install anthropic)"

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return False, "ANTHROPIC_API_KEY not set"

    return True, "OK"


def collect_all_sessions(since: datetime, until: datetime, agent_filter: str = None) -> list:
    """Collect sessions from all configured agents."""
    all_sessions = []

    if agent_filter is None or agent_filter == "claude":
        print("Collecting Claude Code sessions...")
        claude = collect_claude_sessions(since, until)
        print(f"  Found {len(claude)} sessions")
        all_sessions.extend(claude)

    if agent_filter is None or agent_filter == "codex":
        print("Collecting Codex sessions...")
        codex = collect_codex_sessions(since, until)
        print(f"  Found {len(codex)} sessions")
        all_sessions.extend(codex)

    if agent_filter is None or agent_filter == "kimi":
        print("Collecting Kimi sessions...")
        kimi = collect_kimi_sessions(since, until)
        print(f"  Found {len(kimi)} sessions")
        all_sessions.extend(kimi)

    return all_sessions


def filter_by_project(tasks: list, project_filter: str) -> list:
    """Filter tasks by project name (partial match)."""
    if not project_filter:
        return tasks
    filtered = []
    for t in tasks:
        proj = (t.project or "").lower()
        title = (t.title or "").lower()
        if project_filter.lower() in proj or project_filter.lower() in title:
            filtered.append(t)
    return filtered


def cmd_weekly(args):
    """Generate weekly report."""
    if args.since and args.until:
        since = datetime.strptime(args.since, "%Y-%m-%d")
        until = datetime.strptime(args.until, "%Y-%m-%d")
        until = until.replace(hour=23, minute=59, second=59)
    else:
        since, until = get_week_range()

    # Auto mode: redirect output to log file
    log_path = None
    if args.auto:
        log_path = _setup_auto_logging()
        log_file = log_path.open("w", encoding="utf-8")
        stdout_ctx = contextlib.redirect_stdout(log_file)
    else:
        stdout_ctx = contextlib.nullcontext()

    with stdout_ctx:
        print(f"Generating weekly report: {since.strftime('%Y-%m-%d')} to {until.strftime('%Y-%m-%d')}")
        if args.auto:
            print(f"[auto mode] Log: {log_path}")
        print()

        # Check LLM availability
        llm_available, llm_reason = _check_llm_availability()
        if not llm_available:
            print(f"[!] LLM unavailable: {llm_reason}")
            print("[!] Report will be generated without STAR extraction (basic mode)")
            print()

        # Collect
        sessions = collect_all_sessions(since, until, args.agent)
        total_sessions = len(sessions)

        if not sessions:
            print("No sessions found in the specified date range.")
            if args.auto:
                print("[auto mode] Exiting silently (no data to report)")
            return

        # Cluster into tasks
        print("Clustering sessions into tasks...")
        tasks = cluster_sessions(sessions)
        print(f"  Found {len(tasks)} tasks")
        print()

        # Filter by project
        if args.project:
            tasks = filter_by_project(tasks, args.project)
            print(f"After project filter '{args.project}': {len(tasks)} tasks")

        # Build STAR structures (skip if LLM unavailable)
        if llm_available:
            print("Building STAR structures (this may take a while)...")
            tasks = build_stars_for_tasks(tasks, use_cache=not args.no_cache, quiet=args.auto)
            print()

            # Merge tasks by STAR content similarity
            print("Merging similar tasks by STAR content...")
            before_merge = len(tasks)
            tasks = merge_by_star_similarity(tasks, rule_threshold=0.05, quiet=args.auto)
            if len(tasks) < before_merge:
                print(f"  Merged {before_merge - len(tasks)} duplicate tasks → {len(tasks)} tasks")
            print()
        else:
            print("[basic mode] Skipping STAR extraction and merge (LLM unavailable)")
            print()

        # Render report
        report = render_weekly_report(tasks, since, until, total_sessions)

        # Save
        if args.output:
            output_path = Path(args.output)
        else:
            report_dir = get_report_dir()
            month_dir = report_dir / since.strftime("%Y-%m")
            output_path = month_dir / f"weekly-{since.strftime('%Y-%m-%d')}.md"

        save_report(report, output_path)

        # Summary
        completed = len([t for t in tasks if t.status == "completed"])
        in_progress = len([t for t in tasks if t.status == "in_progress"])
        print(f"\nSummary: {len(tasks)} tasks ({completed} completed, {in_progress} in progress)")

    if args.auto and log_path:
        print(f"[auto] Report saved. Log: {log_path}")


def cmd_monthly(args):
    """Generate monthly report."""
    if args.since and args.until:
        since = datetime.strptime(args.since, "%Y-%m-%d")
        until = datetime.strptime(args.until, "%Y-%m-%d")
        until = until.replace(hour=23, minute=59, second=59)
    else:
        since, until = get_month_range()

    # Auto mode: redirect output to log file
    log_path = None
    if args.auto:
        log_path = _setup_auto_logging()
        log_file = log_path.open("w", encoding="utf-8")
        stdout_ctx = contextlib.redirect_stdout(log_file)
    else:
        stdout_ctx = contextlib.nullcontext()

    with stdout_ctx:
        print(f"Generating monthly report: {since.strftime('%Y-%m-%d')} to {until.strftime('%Y-%m-%d')}")
        if args.auto:
            print(f"[auto mode] Log: {log_path}")
        print()

        # Check LLM availability
        llm_available, llm_reason = _check_llm_availability()
        if not llm_available:
            print(f"[!] LLM unavailable: {llm_reason}")
            print("[!] Report will be generated without STAR extraction (basic mode)")
            print()

        sessions = collect_all_sessions(since, until, args.agent)
        total_sessions = len(sessions)

        if not sessions:
            print("No sessions found in the specified date range.")
            if args.auto:
                print("[auto mode] Exiting silently (no data to report)")
            return

        print("Clustering sessions into tasks...")
        tasks = cluster_sessions(sessions)
        print(f"  Found {len(tasks)} tasks")
        print()

        if args.project:
            tasks = filter_by_project(tasks, args.project)
            print(f"After project filter '{args.project}': {len(tasks)} tasks")

        if llm_available:
            print("Building STAR structures (this may take a while)...")
            tasks = build_stars_for_tasks(tasks, use_cache=not args.no_cache, quiet=args.auto)
            print()

            print("Merging similar tasks by STAR content...")
            before_merge = len(tasks)
            tasks = merge_by_star_similarity(tasks, rule_threshold=0.05, quiet=args.auto)
            if len(tasks) < before_merge:
                print(f"  Merged {before_merge - len(tasks)} duplicate tasks → {len(tasks)} tasks")
            print()
        else:
            print("[basic mode] Skipping STAR extraction and merge (LLM unavailable)")
            print()

        report = render_weekly_report(tasks, since, until, total_sessions)

        if args.output:
            output_path = Path(args.output)
        else:
            report_dir = get_report_dir()
            output_path = report_dir / since.strftime("%Y-%m") / f"monthly-{since.strftime('%Y-%m')}.md"

        save_report(report, output_path)

        completed = len([t for t in tasks if t.status == "completed"])
        in_progress = len([t for t in tasks if t.status == "in_progress"])
        print(f"\nSummary: {len(tasks)} tasks ({completed} completed, {in_progress} in progress)")

    if args.auto and log_path:
        print(f"[auto] Report saved. Log: {log_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate work reports from coding agent conversations."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Weekly command
    weekly_parser = subparsers.add_parser("weekly", help="Generate weekly report")
    weekly_parser.add_argument(
        "--since", type=str, help="Start date (YYYY-MM-DD)"
    )
    weekly_parser.add_argument(
        "--until", type=str, help="End date (YYYY-MM-DD)"
    )
    weekly_parser.add_argument(
        "--project", type=str, help="Filter by project name"
    )
    weekly_parser.add_argument(
        "--agent", type=str, choices=["claude", "codex", "kimi"],
        help="Filter by agent"
    )
    weekly_parser.add_argument(
        "--output", type=str, help="Output file path"
    )
    weekly_parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable LLM response caching"
    )
    weekly_parser.add_argument(
        "--auto", action="store_true",
        help="Auto mode: silent execution, log to file, suitable for cron"
    )

    # Monthly command
    monthly_parser = subparsers.add_parser("monthly", help="Generate monthly report")
    monthly_parser.add_argument(
        "--since", type=str, help="Start date (YYYY-MM-DD)"
    )
    monthly_parser.add_argument(
        "--until", type=str, help="End date (YYYY-MM-DD)"
    )
    monthly_parser.add_argument(
        "--project", type=str, help="Filter by project name"
    )
    monthly_parser.add_argument(
        "--agent", type=str, choices=["claude", "codex", "kimi"],
        help="Filter by agent"
    )
    monthly_parser.add_argument(
        "--output", type=str, help="Output file path"
    )
    monthly_parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable LLM response caching"
    )
    monthly_parser.add_argument(
        "--auto", action="store_true",
        help="Auto mode: silent execution, log to file, suitable for cron"
    )

    args = parser.parse_args()

    if args.command == "weekly":
        cmd_weekly(args)
    elif args.command == "monthly":
        cmd_monthly(args)


if __name__ == "__main__":
    main()
