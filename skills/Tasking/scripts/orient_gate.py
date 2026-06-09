#!/usr/bin/env python3
"""Orient gate checker — pass/blocked/ready/warn."""

import json, os, sys, subprocess
from pathlib import Path

REQ_ROOT = Path("/media/yhr/2T/yunxiao/requirements")

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw).stdout.strip()

def check_file(p, label):
    ok = p.exists() and p.stat().st_size > 0
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_state_phase(sp):
    if not sp.exists():
        return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        ok = d.get("phase") in ("plan", "new")
        return ok, f"state.json: phase={d.get('phase','EMPTY')}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"state.json: error {e} FAIL"

def check_git_branch(expected):
    actual = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    ok = actual == expected
    return ok, f"branch: expected={expected} actual={actual}" + (" OK" if ok else " FAIL")

def check_design_doc(sp):
    if not sp.exists():
        return False, "design_doc: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        path = d.get("design_doc_path", "")
        ok = bool(path) and Path(path).exists()
        return ok, f"design_doc: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"design_doc: error {e} FAIL"

def check_canon(demand_id):
    ok = Path(f"/media/yhr/2T/Canon/tasks/{demand_id}.md").exists()
    return ok, f"Canon task: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_human_confirmed(sp):
    """User confirmed the intel summary. Cannot be checked by machine."""
    return False, "human-confirmed: PENDING — user must confirm intel summary before Briefing"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("demand_id")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rd = REQ_ROOT / args.demand_id
    sp = rd / "state.json"
    repo = Path(args.repo)

    try:
        state = json.loads(sp.read_text()) if sp.exists() else {}
    except Exception:
        state = {}

    branch = state.get("feature_branch") or state.get("base_branch") or run(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    checks = []
    checks.append(("1.branch", check_git_branch(branch)))
    checks.append(("2.state", check_state_phase(sp)))
    checks.append(("3.design_doc", check_design_doc(sp)))
    checks.append(("4.canon", check_canon(args.demand_id)))
    checks.append(("5.human-confirmed", check_human_confirmed(sp)))

    hard = {"1", "2", "3", "4"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    human_pending = not all(c[1][0] for c in checks if c[0] == "5.human-confirmed")

    if fails:
        verdict = "blocked"
    elif human_pending:
        verdict = "ready"
    else:
        verdict = "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "demand_id": args.demand_id, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Orient Gate: {verdict.upper()}")
        for n, (ok, msg) in checks:
            print(f"  [{n}] {msg}")

    prop = repo / ".proposal" / args.demand_id
    gate_path = prop / "orient_gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate = {"verdict": verdict, "demand_id": args.demand_id, "checks": {n: {"ok": ok, "msg": msg} for n, (ok, msg) in checks}}
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False))
    print(f"\norient_gate.json -> {gate_path}", file=sys.stderr)
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
