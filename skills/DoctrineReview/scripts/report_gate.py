#!/usr/bin/env python3
"""DoctrineReview report gate — verify report sections exist.

Usage:
  python3 report_gate.py <report.md> [--json]
"""

import json, sys
from pathlib import Path

REQUIRED = ["Data Scope", "Shortlist", "Decisions"]

def check_file(p):
    ok = Path(p).exists() and Path(p).stat().st_size > 100
    return ok, f"file: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_sections(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    missing = [s for s in REQUIRED if s not in text]
    ok = len(missing) == 0
    return ok, f"sections: {'all 3' if ok else f'missing: {missing}'}" + (" OK" if ok else " FAIL")

def check_not_empty_shortlist(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    has_table = "|---" in text or "| # |" in text
    return has_table, f"shortlist table: {'present' if has_table else 'MISSING'}" + (" OK" if has_table else " WARN")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("report", nargs="?")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.report:
        print("usage: report_gate.py <report.md>", file=sys.stderr)
        sys.exit(2)

    checks = [
        ("1.file", check_file(args.report)),
        ("2.sections", check_sections(args.report)),
        ("3.shortlist", check_not_empty_shortlist(args.report)),
    ]

    hard = {"1","2"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"DoctrineReview Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
