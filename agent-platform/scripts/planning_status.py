#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


import re

from planning_paths import conversation_planning_dir


PHASE_HEADER_RE = re.compile(r"^### (Phase \d+: .+)$")
STATUS_RE = re.compile(r"^- \*\*Status:\*\* ([a-z_]+)$", re.IGNORECASE)


def status_icon(status: str) -> str:
    return {
        "pending": "⏸️",
        "in_progress": "🔄",
        "complete": "✅",
        "failed": "❌",
        "blocked": "❌",
    }.get(status, "⏸️")


def main() -> int:
    parser = argparse.ArgumentParser(description="Show a compact planning status summary.")
    parser.add_argument("--project-dir", default=".", help="Project directory containing task_plan.md")
    parser.add_argument("--conversation", default="", help="Optional conversation id override")
    args = parser.parse_args()

    root = Path(args.project_dir).resolve()
    planning_dir = conversation_planning_dir(root, args.conversation or None)
    plan = planning_dir / "task_plan.md"
    findings = planning_dir / "findings.md"
    progress = planning_dir / "progress.md"

    if not plan.exists():
        legacy_plan = root / "task_plan.md"
        legacy_findings = root / "findings.md"
        legacy_progress = root / "progress.md"
        if legacy_plan.exists():
            plan = legacy_plan
            findings = legacy_findings
            progress = legacy_progress

    if not plan.exists():
        print("📋 No planning files found\n\nRun /plan to start a new planning session.")
        return 0

    text = plan.read_text()
    phases: list[tuple[str, str]] = []
    current = "Unknown"
    error_count = 0
    lines = text.splitlines()
    in_current_phase = False
    pending_phase_name: str | None = None
    in_error_table = False
    in_comment = False

    for raw in lines:
        stripped = raw.strip()

        if "<!--" in raw:
            in_comment = True
        if in_comment:
            if "-->" in raw:
                in_comment = False
            continue

        if raw.startswith("## Current Phase"):
            in_current_phase = True
            continue
        if in_current_phase:
            if not stripped or stripped.startswith("<!--"):
                continue
            if raw.startswith("## "):
                in_current_phase = False
            else:
                current = stripped.strip("- ").strip()
                in_current_phase = False
                continue

        header_match = PHASE_HEADER_RE.match(raw)
        if header_match:
            pending_phase_name = header_match.group(1)
            continue

        status_match = STATUS_RE.match(stripped)
        if pending_phase_name and status_match:
            phases.append((status_match.group(1).lower(), pending_phase_name))
            pending_phase_name = None
            continue

        if raw.startswith("## Errors Encountered"):
            in_error_table = True
            continue
        if in_error_table and raw.startswith("## "):
            in_error_table = False
        if in_error_table and raw.startswith("|") and "Error" not in raw and "-----" not in raw and "|       |" not in raw:
            error_count += 1

    total = len(phases)
    complete = sum(1 for status, _ in phases if status == "complete")
    active_status = "complete" if total and complete == total else "in_progress"
    percent = int((complete / total) * 100) if total else 0

    print("📋 Planning Status\n")
    print(f"Current: {current}")
    print(f"Status: {status_icon(active_status)} {complete}/{total} phases complete ({percent}%)\n")
    for status, name in phases:
        print(f"  {status_icon(status)} {name}")
    print("")
    print(f"Plan dir: {plan.parent}")
    print(f"Files: task_plan.md {'✓' if plan.exists() else '✗'} | findings.md {'✓' if findings.exists() else '✗'} | progress.md {'✓' if progress.exists() else '✗'}")
    print(f"Errors logged: {max(error_count, 0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
