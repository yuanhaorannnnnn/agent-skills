#!/usr/bin/env python3
"""Neutralize verification gate — did we actually verify and scan?

Usage:
  python3 verify_fix_gate.py --evidence <path> [--json]
"""

import json, os, sys
from pathlib import Path

def check_gate_file(evidence_path):
    """Read the gate evidence file written during Neutralize."""
    p = Path(evidence_path)
    if not p.exists():
        return False, "evidence file: missing — no verification recorded FAIL"
    try:
        d = json.loads(p.read_text())
        return True, f"evidence file: found OK"
    except Exception as e:
        return False, f"evidence file: parse error {e} FAIL"

def check_rerun(evidence_path):
    """Verify the test/command was actually rerun."""
    p = Path(evidence_path)
    if not p.exists():
        return False, "rerun: evidence missing FAIL"
    try:
        d = json.loads(p.read_text())
        cmd = d.get("rerun_command", "")
        ok = bool(cmd) and d.get("rerun_exit_code") is not None
        exit_ok = d.get("rerun_exit_code") == 0
        status = "PASS" if exit_ok else f"FAIL (exit={d.get('rerun_exit_code')})"
        return ok and exit_ok, f"rerun: {'ran' if cmd else 'NOT RUN'} exit={d.get('rerun_exit_code','?')} {status}" + (" OK" if ok and exit_ok else " FAIL")
    except Exception as e:
        return False, f"rerun: error {e} FAIL"

def check_adjacent_scan(evidence_path):
    """Verify adjacent code scan was performed."""
    p = Path(evidence_path)
    if not p.exists():
        return False, "adjacent scan: evidence missing FAIL"
    try:
        d = json.loads(p.read_text())
        searches = d.get("adjacent_searches", [])
        findings = d.get("adjacent_findings", [])
        ok = len(searches) > 0
        return ok, f"adjacent scan: {len(searches)} search(es) {len(findings)} finding(s)" + (" OK" if ok else " FAIL (no search recorded)")
    except Exception as e:
        return False, f"adjacent scan: error {e} FAIL"

def check_risk_summary(evidence_path):
    """Verify remaining risk was explicitly stated."""
    p = Path(evidence_path)
    if not p.exists():
        return False, "risk: evidence missing FAIL"
    try:
        d = json.loads(p.read_text())
        risk = d.get("remaining_risk", "")
        ok = bool(risk) and len(risk) > 10
        return ok, f"risk summary: {'present' if ok else 'EMPTY or too short'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"risk: error {e} FAIL"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=".agent-state/neutralize-gate.json", help="Path to gate evidence JSON")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ep = args.evidence

    checks = []
    checks.append(("1.evidence-file", check_gate_file(ep)))
    checks.append(("2.rerun", check_rerun(ep)))
    checks.append(("3.adjacent-scan", check_adjacent_scan(ep)))
    checks.append(("4.risk", check_risk_summary(ep)))

    hard = {"1","2","3","4"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Neutralize Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
