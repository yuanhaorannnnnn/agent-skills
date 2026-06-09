#!/usr/bin/env python3
"""Fix gate checker — machine-readable pass/blocked/warn verdict.

Usage:
  python3 fix_gate.py <bug-id> [--repo <path>] [--json]
"""

import json, os, sys, subprocess
from pathlib import Path

BUG_ROOT = Path("/media/yhr/2T/yunxiao/bugs")

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw).stdout.strip()

def check_file(p, label):
    ok = p.exists() and p.stat().st_size > 0
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_sentinel_state(state_json, bug_id):
    """Read sentinel_task_ids from state.json and verify at least one passed."""
    try:
        d = json.loads(Path(state_json).read_text())
        task_ids = d.get("sentinel_task_ids", [])
        if not task_ids:
            return False, "sentinel: no task_ids recorded FAIL (no build was run)"
        # Check if self_check_summary exists as proxy for Sentinel completion
        summary = d.get("self_check_summary", "")
        sentinel_ok = bool(summary) and "PASS" in summary.upper() or "成功" in summary or "通过" in summary
        if sentinel_ok:
            return True, f"sentinel: {len(task_ids)} task(s) self_check indicates PASS OK"
        else:
            return False, f"sentinel: {len(task_ids)} task(s) self_check unclear or FAIL — verify manually FAIL"
    except Exception as e:
        return False, f"sentinel: error reading state {e} FAIL"

def check_review_gate(state_json, bug_id):
    """Check review_gate field in state.json."""
    try:
        d = json.loads(Path(state_json).read_text())
        verdict = d.get("review_gate", "")
        if verdict == "passed":
            return True, "review: passed OK"
        elif verdict == "skipped":
            return True, "review: skipped (user exempted) OK"
        elif verdict == "blocked":
            return False, "review: blocked FAIL"
        else:
            return False, f"review: unknown verdict '{verdict}' FAIL"
    except Exception as e:
        return False, f"review: error {e} FAIL"

def check_commit_push(state_json, bug_id):
    """Verify commit was made and pushed."""
    try:
        d = json.loads(Path(state_json).read_text())
        commit = d.get("commit_sha", "")
        pushed = d.get("pushed_branch", "")
        ok = bool(commit) and bool(pushed)
        return ok, f"commit/push: commit={'OK' if commit else 'EMPTY'} branch={'OK' if pushed else 'EMPTY'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"commit/push: error {e} FAIL"

def check_fix_result_json(prop):
    p = prop / "fix_result.json"
    if not p.exists():
        return False, "fix_result.json: missing FAIL"
    try:
        d = json.loads(p.read_text())
        ok = bool(d.get("verdict")) and bool(d.get("fix_summary"))
        return ok, f"fix_result.json: verdict={d.get('verdict')} summary={'OK' if d.get('fix_summary') else 'EMPTY'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"fix_result.json: error {e} FAIL"

def check_canon(task_path, bug_id):
    ok = task_path.exists()
    return ok, f"Canon task: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_fix_plan_json_consumed(prop, bug_id):
    """Ensure fix_plan.json exists (was consumed from Intake)."""
    p = prop / "fix_plan.json"
    ok = p.exists()
    path_prefix_ok = str(prop) in str(p) if ok else True
    return ok, f"fix_plan.json (from Intake): {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("bug_id")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    bug_dir = BUG_ROOT / args.bug_id
    repo = Path(args.repo)
    prop = repo / ".proposal" / "repair" / args.bug_id
    sp = bug_dir / "state.json"

    # Read state for branch check
    try:
        state = json.loads(sp.read_text()) if sp.exists() else {}
    except Exception:
        state = {}

    expected_branch = state.get("fix_branch", "") or state.get("base_branch", "")
    if not expected_branch:
        expected_branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    def git_branch_ok(expected):
        actual = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        ok = actual == expected
        return ok, f"branch: expected={expected} actual={actual}" + (" OK" if ok else " FAIL")

    canon_task = Path(f"/media/yhr/2T/Canon/tasks/{args.bug_id}.md")

    checks = []
    checks.append(("1.branch", git_branch_ok(expected_branch)))
    checks.append(("2.fix_plan_consumed", check_fix_plan_json_consumed(prop, args.bug_id)))
    checks.append(("3.sentinel", check_sentinel_state(sp, args.bug_id)))
    checks.append(("4.review", check_review_gate(sp, args.bug_id)))
    checks.append(("5.commit_push", check_commit_push(sp, args.bug_id)))
    checks.append(("6.fix_result.json", check_fix_result_json(prop)))
    checks.append(("7.canon", check_canon(canon_task, args.bug_id)))

    hard = {"1", "2", "3", "4", "5", "6", "7"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    warns = [c for c in checks if c[0].split(".")[0] not in hard and not c[1][0]]

    if fails:
        verdict = "blocked"
    elif warns:
        verdict = "warn"
    else:
        verdict = "pass"

    if args.json:
        out = {"verdict": verdict, "bug_id": args.bug_id, "failed": [f"{n} {m}" for n, m in checks if not m[0]]}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"Fix Gate: {verdict.upper()}")
        for n, (ok, msg) in checks:
            print(f"  [{n}] {msg}")

    gate_path = prop / "fix_gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate = {"verdict": verdict, "bug_id": args.bug_id, "checks": {n: {"ok": ok, "msg": msg} for n, (ok, msg) in checks}}
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False))
    print(f"\nfix_gate.json -> {gate_path}", file=sys.stderr)
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
