#!/usr/bin/env python3
"""Cover synthesis gate — verify DESIGN.md generated from multiple references.

Usage:
  python3 synthesis_gate.py --design <path> --evidence <path> [--json]
"""

import json, sys
from pathlib import Path

def check_design_md(p):
    if not Path(p).exists():
        return False, "DESIGN.md: missing FAIL"
    text = Path(p).read_text()
    ok = len(text) > 100 and "colors:" in text and "typography:" in text
    return ok, f"DESIGN.md: {len(text)} chars {'OK' if ok else 'too short or missing sections'}" + (" OK" if ok else " FAIL")

def check_reference_count(ep):
    if not Path(ep).exists():
        return False, "evidence: missing FAIL"
    try:
        d = json.loads(Path(ep).read_text())
        refs = d.get("references_studied", [])
        ok = len(refs) >= 2
        return ok, f"references: {len(refs)} studied (need >=2)" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"evidence: error {e} FAIL"

def check_max_refs(ep):
    try:
        d = json.loads(Path(ep).read_text()) if Path(ep).exists() else {}
        refs = d.get("references_studied", [])
        ok = len(refs) <= 4
        return ok, f"max refs: {len(refs)}" + (" OK" if ok else f" WARN ({len(refs)}>4, synthesis quality may drop)")
    except Exception:
        return True, "max refs: skip OK"

def check_no_wholesale_copy(ep):
    try:
        d = json.loads(Path(ep).read_text()) if Path(ep).exists() else {}
        ok = not d.get("wholesale_copy", False)
        return ok, "copy check: OK" if ok else "copy check: WHOLESALE COPY FLAGGED FAIL"
    except Exception:
        return True, "copy check: skip OK"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--design", required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks = [
        ("1.design_md", check_design_md(args.design)),
        ("2.ref_count", check_reference_count(args.evidence)),
        ("3.max_refs", check_max_refs(args.evidence)),
        ("4.no_copy", check_no_wholesale_copy(args.evidence)),
    ]

    hard = {"1","2"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Cover Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
