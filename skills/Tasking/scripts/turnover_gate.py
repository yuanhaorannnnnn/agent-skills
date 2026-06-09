#!/usr/bin/env python3
"""Turnover gate checker — pass/blocked. No downstream, terminal gate."""

import json, os, sys
from pathlib import Path

REQ_ROOT = Path("/media/yhr/2T/yunxiao/requirements")

def check_state_phase(sp):
    if not sp.exists(): return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = d.get("phase") in ("test", "dev")
        return ok, f"state.json: phase={d.get('phase','EMPTY')}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"state.json: error {e} FAIL"

def check_deliverables(sp):
    if not sp.exists(): return False, "deliverables: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = bool(d.get("deliverable_url", ""))
        return ok, f"deliverables: {'OK' if ok else 'EMPTY'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"deliverables: error {e} FAIL"

def check_comment_evidence(sp):
    if not sp.exists(): return False, "comment: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = bool(d.get("comment_ids"))
        return ok, f"comment: comment_ids={'present' if ok else 'EMPTY'}" + (" OK" if ok else " FAIL (verify manually)")
    except Exception as e:
        return False, f"comment: error {e} FAIL"

def check_assignee_changed(sp):
    try:
        d = json.loads(sp.read_text()) if sp.exists() else {}
        new = d.get("system_test_assignee", "")
        ok = new == "樊亮亮"
        return ok, f"assignee: {new}" + (" OK" if ok else f" FAIL (expected 樊亮亮, got '{new}')")
    except Exception:
        return False, "assignee: error FAIL"

def check_phase(sp):
    if not sp.exists():
        return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = d.get("phase") == "test"
        return ok, f"phase: {d.get('phase','EMPTY')}" + (" OK" if ok else " FAIL (expected test)")
    except Exception as e:
        return False, f"phase: error {e} FAIL"

def check_status_updated(sp):
    return False, "yunxiao-status: SKIPPED — MCP auth required, verify manually"

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
    checks.append(("1.phase", check_phase(sp)))
    checks.append(("2.deliverables", check_deliverables(sp)))
    checks.append(("3.comment", check_comment_evidence(sp)))
    checks.append(("4.assignee", check_assignee_changed(sp)))
    checks.append(("5.yunxiao-status", check_status_updated(sp)))
    checks.append(("6.canon", check_canon(args.demand_id)))

    hard = {"1", "2", "3", "4", "6"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]

    if fails: verdict = "blocked"
    else: verdict = "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "demand_id": args.demand_id, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Turnover Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")

    prop = repo / ".proposal" / args.demand_id
    gate_path = prop / "turnover_gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate = {"verdict": verdict, "demand_id": args.demand_id, "checks": {n: {"ok": ok, "msg": msg} for n, (ok, msg) in checks}}
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False))
    print(f"\nturnover_gate.json -> {gate_path}", file=sys.stderr)
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
