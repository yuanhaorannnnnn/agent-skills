#!/usr/bin/env python3
"""herdr-carla-tune pre-flight gate — verify loop is safe to start.

Usage:
  python3 preflight_gate.py [--json]
"""

import json, os, sys, subprocess
from pathlib import Path

def run(cmd, cwd=None, **kw):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, **kw)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None

def check_repo(p, label):
    ok = p.exists() and (p / ".git").exists()
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_branch(p, expected, label):
    actual = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=p)
    ok = actual == expected
    return ok, f"{label}: expected={expected} actual={actual}" + (" OK" if ok else " FAIL")

def check_clean(p, label):
    out = run(["git", "status", "--short"], cwd=p)
    ok = out is not None and out == ""
    return ok, f"{label}: {'clean' if ok else 'dirty'}" + (" OK" if ok else " FAIL")

def check_baseline(ctrl):
    ok = (ctrl / "runs" / "baseline" / "metrics.json").exists()
    return ok, f"baseline: {'found' if ok else 'missing — run experiment first'}" + (" OK" if ok else " FAIL")

def check_loop_py(ctrl):
    ok = (ctrl / "carla_autoresearch" / "loop.py").exists()
    return ok, f"loop.py: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_state(state_file):
    if state_file.exists():
        return False, "state file: EXISTS — resume or re-init? WARN"
    return True, "state file: clean (new loop) OK"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-repo", default=os.environ.get("CARLA_TUNE_TARGET_REPO"))
    ap.add_argument("--controller-repo", default=os.environ.get("CARLA_TUNE_CONTROLLER_REPO"))
    ap.add_argument("--state-file")
    ap.add_argument("--target-branch", default=os.environ.get("CARLA_TUNE_TARGET_BRANCH"))
    ap.add_argument("--ctrl-branch", default=os.environ.get("CARLA_TUNE_CONTROLLER_BRANCH"))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for option, value in (
        ("--target-repo or CARLA_TUNE_TARGET_REPO", args.target_repo),
        ("--controller-repo or CARLA_TUNE_CONTROLLER_REPO", args.controller_repo),
        ("--target-branch or CARLA_TUNE_TARGET_BRANCH", args.target_branch),
        ("--ctrl-branch or CARLA_TUNE_CONTROLLER_BRANCH", args.ctrl_branch),
    ):
        if not value:
            ap.error(f"required: {option}")

    target_repo = Path(args.target_repo).resolve()
    ctrl_repo = Path(args.controller_repo).resolve()
    state_file = Path(args.state_file).resolve() if args.state_file else ctrl_repo / ".agent-state" / "autoresearch-loop-state.yaml"

    checks = []
    checks.append(("1.target-repo", check_repo(target_repo, "target repo")))
    checks.append(("2.ctrl-repo", check_repo(ctrl_repo, "controller repo")))
    checks.append(("3.target-branch", check_branch(target_repo, args.target_branch, "target")))
    checks.append(("4.ctrl-branch", check_branch(ctrl_repo, args.ctrl_branch, "ctrl")))
    checks.append(("5.target-clean", check_clean(target_repo, "target")))
    checks.append(("6.ctrl-clean", check_clean(ctrl_repo, "ctrl")))
    checks.append(("7.baseline", check_baseline(ctrl_repo)))
    checks.append(("8.controller", check_loop_py(ctrl_repo)))
    checks.append(("9.state", check_state(state_file)))

    hard = {"1","2","3","4","5","6","7","8"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]

    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Pre-flight Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
