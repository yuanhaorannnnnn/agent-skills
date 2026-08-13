#!/usr/bin/env python3
"""Engage gate checker — pass/blocked/warn. No human gate (all machine)."""

import json, os, sys
from pathlib import Path

REQ_ROOT = Path("/media/yhr/2T/yunxiao/requirements")

def run(cmd, **kw):
    import subprocess
    return subprocess.run(cmd, capture_output=True, text=True, **kw).stdout.strip()

def check_state_phase(sp):
    if not sp.exists(): return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = d.get("phase") in ("dev", "review")
        return ok, f"state.json: phase={d.get('phase','EMPTY')}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"state.json: error {e} FAIL"

def check_goal_md(sp, repo):
    if not sp.exists(): return False, "goal.md: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        path = d.get("goal_path", "")
        ok = bool(path) and Path(path).exists()
        return ok, f"goal.md: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"goal.md: error {e} FAIL"

def check_review_gate(sp):
    if not sp.exists(): return False, "review: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        verdict = d.get("review_gate", "")
        if verdict == "passed": return True, "review: passed OK"
        elif verdict == "skipped": return True, "review: skipped (exempted) OK"
        elif verdict == "blocked": return False, "review: blocked FAIL"
        else: return False, f"review: unknown '{verdict}' FAIL"
    except Exception as e:
        return False, f"review: error {e} FAIL"

def check_traceback(sp):
    if not sp.exists(): return False, "traceback: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = bool(d.get("traceback_done"))
        return ok, f"traceback: {'done' if ok else 'not run'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"traceback: error {e} FAIL"

def check_yunxiao_status(sp):
    return False, "yunxiao-status: SKIPPED — MCP auth required"

def check_canon(demand_id):
    ok = Path(f"/media/yhr/2T/Canon/tasks/{demand_id}.md").exists()
    return ok, f"Canon task: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("demand_id")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    sp = REQ_ROOT / args.demand_id / "state.json"
    repo = Path(args.repo)

    checks = []
    checks.append(("1.state", check_state_phase(sp)))
    checks.append(("2.goal_md", check_goal_md(sp, repo)))
    checks.append(("3.review", check_review_gate(sp)))
    checks.append(("4.traceback", check_traceback(sp)))
    checks.append(("5.yunxiao", check_yunxiao_status(sp)))
    checks.append(("6.canon", check_canon(args.demand_id)))

    hard = {"1", "2", "3", "4", "6"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]

    if fails: verdict = "blocked"
    else: verdict = "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "demand_id": args.demand_id, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Engage Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")

    prop = repo / ".proposal" / args.demand_id
    gate_path = prop / "engage_gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate = {"verdict": verdict, "demand_id": args.demand_id, "checks": {n: {"ok": ok, "msg": msg} for n, (ok, msg) in checks}}
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False))
    print(f"\nengage_gate.json -> {gate_path}", file=sys.stderr)
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
