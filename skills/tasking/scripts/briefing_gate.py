#!/usr/bin/env python3
"""Briefing gate checker — pass/blocked/ready/warn."""

import json, os, sys
from pathlib import Path

REQ_ROOT = Path("/media/yhr/2T/yunxiao/requirements")

def check_state_phase(sp):
    if not sp.exists(): return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = d.get("phase") in ("review", "plan")
        return ok, f"state.json: phase={d.get('phase','EMPTY')}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"state.json: error {e} FAIL"

def check_kb_upload(sp):
    if not sp.exists(): return False, "kb: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = bool(d.get("knowledge_doc_url", ""))
        return ok, f"kb_upload: {'OK' if ok else 'EMPTY'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"kb: error {e} FAIL"

def check_user_ids(sp):
    if not sp.exists(): return False, "user_ids: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ids = d.get("participant_user_ids", [])
        ok = bool(ids)
        return ok, f"user_ids: {len(ids)} resolved" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"user_ids: error {e} FAIL"

def check_calendar(sp):
    if not sp.exists(): return False, "calendar: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = bool(d.get("calendar_event_id", ""))
        return ok, f"calendar: {'OK' if ok else 'EMPTY'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"calendar: error {e} FAIL"

def check_canon(demand_id):
    ok = Path(f"/media/yhr/2T/Canon/tasks/{demand_id}.md").exists()
    return ok, f"Canon task: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_human_review_passed(sp):
    return False, "human-review: PENDING — review meeting outcome must be confirmed before Engage"

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
    checks.append(("2.kb_upload", check_kb_upload(sp)))
    checks.append(("3.user_ids", check_user_ids(sp)))
    checks.append(("4.calendar", check_calendar(sp)))
    checks.append(("5.canon", check_canon(args.demand_id)))
    checks.append(("6.human-review", check_human_review_passed(sp)))

    hard = {"1", "2", "3", "4", "5"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    human_pending = not any(c[1][0] for c in checks if c[0] == "6.human-review")

    if fails: verdict = "blocked"
    elif human_pending: verdict = "ready"
    else: verdict = "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "demand_id": args.demand_id, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Briefing Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")

    prop = repo / ".proposal" / args.demand_id
    gate_path = prop / "briefing_gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate = {"verdict": verdict, "demand_id": args.demand_id, "checks": {n: {"ok": ok, "msg": msg} for n, (ok, msg) in checks}}
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False))
    print(f"\nbriefing_gate.json -> {gate_path}", file=sys.stderr)
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
