#!/usr/bin/env python3
"""Execute gate — verify goal.md + Canon task page were written.

Usage:
  python3 execution_gate.py --goal <path> --task <canon-task-path> [--json]
"""

import json, sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))
from accepted_spec import artifact_mode, load_spec  # noqa: E402


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


def accepted_spec_path_from_goal(goal_path):
    if not Path(goal_path).exists():
        return None
    for line in Path(goal_path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- accepted_spec_path:"):
            value = stripped.split(":", 1)[1].strip()
            if not value:
                return None
            path = Path(value).expanduser()
            return path if path.is_absolute() else Path(goal_path).parent / path
    return None


def artifact_mode_from_goal(goal_path):
    if not Path(goal_path).exists():
        return None
    for line in Path(goal_path).read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- artifact_mode:"):
            value = stripped.split(":", 1)[1].strip()
            return value or None
    return None


def check_accepted_spec(path, required=False, required_mode=None):
    if not path:
        if required:
            return False, "accepted_spec: required FAIL"
        return True, "accepted_spec: not requested"
    spec, errors = load_spec(
        path,
        require_artifact_mode=required_mode == "delivery",
    )
    if errors:
        return False, "accepted_spec: " + "; ".join(errors) + " FAIL"
    declared_mode = artifact_mode(spec)
    if required_mode and declared_mode != required_mode:
        return (
            False,
            f"accepted_spec: artifact_mode={declared_mode!r}, expected {required_mode!r} FAIL",
        )
    return True, f"accepted_spec: valid ({spec['spec_hash']}) OK"


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--goal", required=True)
    ap.add_argument("--task", required=True)
    ap.add_argument("--accepted-spec", help="Accepted specification path. Overrides the goal metadata.")
    ap.add_argument("--require-accepted-spec", action="store_true")
    ap.add_argument("--artifact-mode", choices=("delivery", "audit", "knowledge"),
                    help="Required mode for the accepted specification.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    accepted_spec = (
        Path(args.accepted_spec).expanduser()
        if args.accepted_spec
        else accepted_spec_path_from_goal(args.goal)
    )
    goal_mode = artifact_mode_from_goal(args.goal)
    required_mode = args.artifact_mode or goal_mode
    accepted_required = (
        args.require_accepted_spec
        or accepted_spec is not None
        or required_mode == "delivery"
    )
    checks = [
        ("1.goal-file", check_file(args.goal, "goal.md")),
        ("2.goal-structure", check_goal_structure(args.goal)),
        ("3.canon-task", check_file(args.task, "Canon task page")),
        ("4.canon-updated", check_canon_updated(args.task)),
        (
            "5.accepted-spec",
            check_accepted_spec(
                accepted_spec,
                required=accepted_required,
                required_mode=required_mode,
            ),
        ),
    ]

    hard = {"1","2","3","4","5"}
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
