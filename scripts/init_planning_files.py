#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from planning_paths import conversation_planning_dir

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent / "skills" / "plan-workspace" / "templates"


def copy_if_missing(template_name: str, destination: Path) -> bool:
    target = destination / template_name
    if target.exists():
        return False
    target.write_text((TEMPLATE_ROOT / template_name).read_text())
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize a conversation-scoped planning workspace.")
    parser.add_argument("--project-dir", default=".", help="Target project directory")
    parser.add_argument("--conversation", default="", help="Optional conversation id override")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    planning_dir = conversation_planning_dir(project_dir, args.conversation or None)
    planning_dir.mkdir(parents=True, exist_ok=True)
    created = []
    for name in ("spec.md", "exec_plan.md", "task_plan.md", "findings.md", "progress.md"):
        if copy_if_missing(name, planning_dir):
            created.append(name)

    if created:
        print("Created:")
        for name in created:
            print(f"- {planning_dir / name}")
    else:
        print(f"Planning files already exist in {planning_dir}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
