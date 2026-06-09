#!/usr/bin/env python3
"""Fusion pre-report gate — verify evidence was actually collected.

Usage:
  python3 pre_report_gate.py --evidence <path> [--json]
"""

import json, sys
from pathlib import Path

def check_evidence_file(p):
    if not Path(p).exists():
        return False, "evidence file: missing — no research trail FAIL"
    try:
        json.loads(Path(p).read_text())
        return True, "evidence file: found OK"
    except Exception as e:
        return False, f"evidence file: error {e} FAIL"

def check_canon_searched(p):
    try:
        d = json.loads(Path(p).read_text()) if Path(p).exists() else {}
    except Exception:
        d = {}
    searches = d.get("canon_searches", [])
    matches = d.get("canon_matches", 0)
    ok = len(searches) > 0
    return ok, f"Canon: {len(searches)} search(es) {matches} match(es)" + (" OK" if ok else " FAIL")

def check_code_scanned(p):
    try:
        d = json.loads(Path(p).read_text()) if Path(p).exists() else {}
    except Exception:
        d = {}
    scans = d.get("code_scans", [])
    files = d.get("files_read", [])
    ok = len(scans) > 0 or len(files) > 0
    return ok, f"code scan: {len(scans)} scan(s) {len(files)} file(s)" + (" OK" if ok else " FAIL")

def check_citations(p):
    try:
        d = json.loads(Path(p).read_text()) if Path(p).exists() else {}
    except Exception:
        d = {}
    markers = d.get("citation_markers_used", [])
    ok = len(markers) > 0
    return ok, f"citations: {'present' if ok else 'NONE'}" + (" OK" if ok else " WARN")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", default=".research/evidence.json", help="Path to research evidence JSON")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    ep = args.evidence
    checks = [
        ("1.evidence", check_evidence_file(ep)),
        ("2.canon", check_canon_searched(ep)),
        ("3.code-scan", check_code_scanned(ep)),
        ("4.citations", check_citations(ep)),
    ]

    hard = {"1","2","3"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Fusion Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
