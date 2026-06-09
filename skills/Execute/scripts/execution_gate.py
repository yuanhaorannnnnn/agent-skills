#!/usr/bin/env python3
"""Execute gate — verify goal.md + Canon task page were written.

Usage:
  python3 execution_gate.py --goal <path> --task <canon-task-path> [--json]
"""

import json, sys
from pathlib import Path

def check_file(p, label):
    ok = Path(p).exists() and Path(p).stat().st_size > 50
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_goal_structure(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    has_goal = "## 目标" in text or "## Goal" in text
    has_tasks = "## 任务清单" in text or "## Tasks" in text or "- [ ]" in text
    ok = has_goal and has_tasks
    return ok, f"goal.md: goal={'OK' if has_goal else 'MISSING'} tasks={'OK' if has_tasks else 'MISSING'}" + (" OK" if ok else " FAIL")

def check_canon_updated(p):
    if not Path(p).exists():
        return False, "Canon task: missing FAIL"
    text = Path(p).read_text()
    has_goal = "## Goal" in text
    return has_goal, f"Canon task: {'Goal section present' if has_goal else 'Goal MISSING'}" + (" OK" if has_goal else " FAIL")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks = [
        ("1.goal-file", check_file(args.goal, "goal.md")),
        ("2.goal-structure", check_goal_structure(args.goal)),
        ("3.canon-task", check_file(args.task, "Canon task page")),
        ("4.canon-updated", check_canon_updated(args.task)),
    ]

    hard = {"1","2","3","4"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Execute Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
