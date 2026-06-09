#!/usr/bin/env python3
"""Closeout gate checker — verifies the defect was cleanly closed.

Usage:
  python3 closeout_gate.py <bug-id> [--repo <path>] [--json]
"""

import json, os, sys, subprocess
from pathlib import Path

BUG_ROOT = Path("/media/yhr/2T/yunxiao/bugs")

OUTCOME_STATUS_MAP = {
    "fixed": "回归验证",
    "false-positive": "关闭",
    "requirement": "转需求",
    "cannot-reproduce": "开发挂起",
    "blocked": "开发挂起",
}

def check_state_outcome(sp):
    if not sp.exists():
        return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        outcome = d.get("outcome", "")
        status = d.get("status", "")
        if not outcome or not status:
            return False, f"state.json: outcome={outcome or 'EMPTY'} status={status or 'EMPTY'} FAIL"
        expected_status = OUTCOME_STATUS_MAP.get(outcome)
        if expected_status and status != expected_status:
            return False, f"state.json: outcome={outcome} → status={status} FAIL (expected {expected_status})"
        ok = bool(outcome) and bool(status)
        return ok, f"state.json: outcome={outcome} status={status}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"state.json: error {e} FAIL"

def check_phase(sp):
    if not sp.exists():
        return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = d.get("phase") in ("regression", "requirement", "closed", "suspended", "fixed")
        return ok, f"phase: {d.get('phase','EMPTY')}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"phase: error {e} FAIL"

def check_comment_evidence(sp):
    """comment_ids or --comment evidence exists."""
    if not sp.exists():
        return False, "comment: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        has_comment_ids = bool(d.get("comment_ids"))
        return has_comment_ids, f"comment: comment_ids={'present' if has_comment_ids else 'EMPTY'}" + (" OK" if has_comment_ids else " FAIL (verify comment was actually posted)")
    except Exception as e:
        return False, f"comment: error {e} FAIL"

def check_owner_unchanged(sp, bug_id):
    """Compare current assignee with original. SKIPPED offline."""
    return False, "owner: SKIPPED — MCP auth required, verify manually"

def check_canon(task_path, bug_id):
    ok = task_path.exists()
    return ok, f"Canon task: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("bug_id")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    sp = BUG_ROOT / args.bug_id / "state.json"
    canon_task = Path(f"/media/yhr/2T/Canon/tasks/{args.bug_id}.md")

    checks = []
    checks.append(("1.phase", check_phase(sp)))
    checks.append(("2.state-outcome", check_state_outcome(sp)))
    checks.append(("3.comment", check_comment_evidence(sp)))
    checks.append(("4.owner", check_owner_unchanged(sp, args.bug_id)))
    checks.append(("5.canon", check_canon(canon_task, args.bug_id)))

    hard = {"1", "2", "3", "5"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]

    if fails:
        verdict = "blocked"
    else:
        verdict = "pass"

    if args.json:
        out = {"verdict": verdict, "bug_id": args.bug_id, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"Closeout Gate: {verdict.upper()}")
        for n, (ok, msg) in checks:
            print(f"  [{n}] {msg}")

    # Write to Intake's gate file (same location), or in absence, to proposal dir
    repo = Path(args.repo)
    prop = repo / ".proposal" / "repair" / args.bug_id
    gate_path = prop / "closeout_gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate = {"verdict": verdict, "bug_id": args.bug_id, "checks": {n: {"ok": ok, "msg": msg} for n, (ok, msg) in checks}}
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False))
    print(f"\ncloseout_gate.json -> {gate_path}", file=sys.stderr)
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
