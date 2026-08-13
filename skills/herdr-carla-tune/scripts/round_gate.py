#!/usr/bin/env python3
"""herdr-carla-tune per-round gate — verify safe to start next hypothesis.

Usage:
  python3 round_gate.py [--json]
"""

import json, os, sys, subprocess
from pathlib import Path
import yaml

def run(cmd, cwd=None, **kw):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, **kw)
    except OSError:
        return None
    return result.stdout.strip() if result.returncode == 0 else None

def check_worktree_clean(target_repo):
    out = run(["git", "status", "--short"], cwd=target_repo)
    ok = out is not None and out == ""
    return ok, f"worktree: {'clean' if ok else 'dirty — uncommitted changes'}" + (" OK" if ok else " FAIL")

def check_state_file(state_file):
    if not state_file.exists():
        return False, "state file: missing FAIL"
    try:
        with open(state_file) as f:
            data = yaml.safe_load(f)
        ok = bool(data) and "loop_id" in data
        return ok, f"state file: loop_id={data.get('loop_id','EMPTY')}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"state file: parse error {e} FAIL"

def check_not_terminated(state_file):
    if not state_file.exists():
        return False, "termination: state file missing FAIL"
    try:
        with open(state_file) as f:
            data = yaml.safe_load(f) or {}
        term = data.get("termination", {})
        reason = term.get("reason", "")
        ok = not reason
        return ok, f"termination: {'active' if ok else f'TERMINATED — {reason}'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"termination: error {e} FAIL"

def check_hypotheses_remaining(state_file):
    if not state_file.exists():
        return False, "hypotheses: state file missing FAIL"
    try:
        with open(state_file) as f:
            data = yaml.safe_load(f) or {}
        hyps = data.get("hypotheses", [])
        pending = [h for h in hyps if h.get("status") == "pending"]
        ok = len(pending) > 0
        return ok, f"hypotheses: {len(pending)} pending / {len(hyps)} total" + (" OK" if ok else " DONE (no more)")
    except Exception as e:
        return False, f"hypotheses: error {e} FAIL"

def check_round_limits(state_file):
    if not state_file.exists():
        return False, "limits: state file missing FAIL"
    try:
        with open(state_file) as f:
            data = yaml.safe_load(f) or {}
        cfg = data.get("config", {})
        current = data.get("current", {})
        rnd = current.get("round", 0)
        max_rnd = cfg.get("max_rounds", 10)
        streak = data.get("termination", {}).get("no_improvement_streak", 0)
        ok = rnd < max_rnd and streak < 3
        return ok, f"limits: round={rnd}/{max_rnd} streak={streak}/3" + (" OK" if ok else " HIT LIMIT")
    except Exception as e:
        return False, f"limits: error {e} FAIL"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-repo", default=os.environ.get("CARLA_TUNE_TARGET_REPO"))
    ap.add_argument("--controller-repo", default=os.environ.get("CARLA_TUNE_CONTROLLER_REPO"))
    ap.add_argument("--state-file")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    for option, value in (
        ("--target-repo or CARLA_TUNE_TARGET_REPO", args.target_repo),
        ("--controller-repo or CARLA_TUNE_CONTROLLER_REPO", args.controller_repo),
    ):
        if not value:
            ap.error(f"required: {option}")

    target_repo = Path(args.target_repo).resolve()
    ctrl_repo = Path(args.controller_repo).resolve()
    state_file = Path(args.state_file).resolve() if args.state_file else ctrl_repo / ".agent-state" / "autoresearch-loop-state.yaml"

    checks = []
    checks.append(("1.worktree", check_worktree_clean(target_repo)))
    checks.append(("2.state-file", check_state_file(state_file)))
    checks.append(("3.not-terminated", check_not_terminated(state_file)))
    checks.append(("4.hypotheses", check_hypotheses_remaining(state_file)))
    checks.append(("5.limits", check_round_limits(state_file)))

    hard = {"1","2","3","4","5"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Round Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
