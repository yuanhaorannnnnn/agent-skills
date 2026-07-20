#!/usr/bin/env python3
"""Neutralize verification gate — did we actually verify and scan?

Usage:
  python3 verify_fix_gate.py --evidence <path> [--json]
"""

import json, os, sys
from pathlib import Path

def load_evidence(evidence_path):
    return json.loads(Path(evidence_path).read_text())

def check_gate_file(evidence_path):
    """Read the gate evidence file written during Neutralize."""
    p = Path(evidence_path)
    if not p.exists():
        return False, "evidence file: missing — no verification recorded FAIL"
    try:
        load_evidence(p)
        return True, f"evidence file: found OK"
    except Exception as e:
        return False, f"evidence file: parse error {e} FAIL"

def check_observed_failure(evidence_path):
    """Verify pre-change evidence or an explicit reproduction exception exists."""
    p = Path(evidence_path)
    if not p.exists():
        return False, "observable target: evidence missing FAIL"
    try:
        d = load_evidence(p)
        observation = str(d.get("failure_observation", "")).strip()
        reproduction = str(d.get("reproduction_command", "")).strip()
        skipped = str(d.get("reproduction_skipped_reason", "")).strip()
        ok = len(observation) > 10 and bool(reproduction or len(skipped) > 10)
        mode = "reproduced" if reproduction else "skip documented" if skipped else "missing reproduction"
        return ok, f"observable target: {mode}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"observable target: error {e} FAIL"

def check_rerun(evidence_path):
    """Verify the test/command was actually rerun."""
    p = Path(evidence_path)
    if not p.exists():
        return False, "rerun: evidence missing FAIL"
    try:
        d = load_evidence(p)
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
        d = load_evidence(p)
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
        d = load_evidence(p)
        risk = d.get("remaining_risk", "")
        ok = bool(risk) and len(risk) > 10
        return ok, f"risk summary: {'present' if ok else 'EMPTY or too short'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"risk: error {e} FAIL"

def check_boundary(evidence_path):
    """Require a module-boundary assessment for every fix."""
    p = Path(evidence_path)
    if not p.exists():
        return False, "boundary: evidence missing FAIL"
    try:
        d = load_evidence(p)
        changed = d.get("public_interface_changed")
        assessment = str(d.get("boundary_assessment", "")).strip()
        ok = isinstance(changed, bool) and len(assessment) > 10
        status = "changed" if changed is True else "stable" if changed is False else "unspecified"
        return ok, f"boundary: {status}, assessment {'present' if assessment else 'missing'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"boundary: error {e} FAIL"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=".agent-state/neutralize-gate.json", help="Path to gate evidence JSON")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ep = args.evidence

    checks = []
    checks.append(("1.evidence-file", check_gate_file(ep)))
    checks.append(("2.observable-target", check_observed_failure(ep)))
    checks.append(("3.rerun", check_rerun(ep)))
    checks.append(("4.adjacent-scan", check_adjacent_scan(ep)))
    checks.append(("5.boundary", check_boundary(ep)))
    checks.append(("6.risk", check_risk_summary(ep)))

    hard = {"1","2","3","4","5","6"}
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
