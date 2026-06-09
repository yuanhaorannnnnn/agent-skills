#!/usr/bin/env python3
"""Sweep pre-flight gate — verify loop is safe to start.

Usage:
  python3 preflight_gate.py [--json]
"""

import json, os, sys, subprocess
from pathlib import Path

TARGET_REPO = Path("/media/yhr/2T/CarlaUE5")
CTRL_REPO = Path("/media/yhr/2T/autoresearch")
STATE_FILE = CTRL_REPO / ".agent-state" / "autoresearch-loop-state.yaml"

def run(cmd, cwd=None, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, **kw).stdout.strip()

def check_repo(p, label):
    ok = p.exists() and (p / ".git").exists()
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_branch(p, expected, label):
    actual = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=p)
    ok = actual == expected
    return ok, f"{label}: expected={expected} actual={actual}" + (" OK" if ok else " FAIL")

def check_clean(p, label):
    out = run(["git", "status", "--short"], cwd=p)
    ok = out == ""
    return ok, f"{label}: {'clean' if ok else 'dirty'}" + (" OK" if ok else " FAIL")

def check_baseline(ctrl):
    ok = (ctrl / "runs" / "baseline" / "metrics.json").exists()
    return ok, f"baseline: {'found' if ok else 'missing — run experiment first'}" + (" OK" if ok else " FAIL")

def check_loop_py(ctrl):
    ok = (ctrl / "carla_autoresearch" / "loop.py").exists()
    return ok, f"loop.py: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_state():
    if STATE_FILE.exists():
        return False, "state file: EXISTS — resume or re-init? WARN"
    return True, "state file: clean (new loop) OK"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-branch", default="feature/carla-lidar-optimization")
    ap.add_argument("--ctrl-branch", default="feature/carla-lidar-autoresearch")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks = []
    checks.append(("1.target-repo", check_repo(TARGET_REPO, "target repo")))
    checks.append(("2.ctrl-repo", check_repo(CTRL_REPO, "controller repo")))
    checks.append(("3.target-branch", check_branch(TARGET_REPO, args.target_branch, "target")))
    checks.append(("4.ctrl-branch", check_branch(CTRL_REPO, args.ctrl_branch, "ctrl")))
    checks.append(("5.target-clean", check_clean(TARGET_REPO, "target")))
    checks.append(("6.ctrl-clean", check_clean(CTRL_REPO, "ctrl")))
    checks.append(("7.baseline", check_baseline(CTRL_REPO)))
    checks.append(("8.controller", check_loop_py(CTRL_REPO)))
    checks.append(("9.state", check_state()))

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
