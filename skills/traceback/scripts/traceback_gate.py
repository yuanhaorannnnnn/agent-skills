#!/usr/bin/env python3
"""Traceback gate — verify 3 checklists exist and summary is complete.

Usage:
  python3 traceback_gate.py --dir .planning/<slug>/ [--json]
"""

import json, sys
from pathlib import Path

def check_file(p, label):
    ok = Path(p).exists() and Path(p).stat().st_size > 50
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_summary(p):
    if not Path(p).exists():
        return False, "summary: missing FAIL"
    text = Path(p).read_text()
    has_d2d = "Design → Dev" in text or "Design->Dev" in text
    has_d2t = "Dev → Test" in text or "Dev->Test" in text
    has_gaps = "Critical Gaps" in text
    ok = has_d2d and has_d2t and has_gaps
    detail = []
    if not has_d2d: detail.append("missing Design→Dev")
    if not has_d2t: detail.append("missing Dev→Test")
    if not has_gaps: detail.append("missing Critical Gaps")
    return ok, f"summary: {'complete' if ok else ', '.join(detail)}" + (" OK" if ok else " FAIL")

def check_gaps_written(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    has_canon = "/media/yhr/2T/Canon" in text
    has_gaps = "Critical Gaps" in text
    return has_gaps or has_canon, f"gaps canon: {'referenced' if has_canon else 'not in Canon'}" + (" OK" if has_canon or has_gaps else " WARN")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True, help="Path to .planning/<slug>/")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    d = Path(args.dir)
    c1 = d / "document-dev-checklist.md"
    c2 = d / "dev-test-coverage-checklist.md"
    c3 = d / "align-summary.md"

    checks = [
        ("1.document-dev", check_file(c1, "document-dev-checklist.md")),
        ("2.dev-test", check_file(c2, "dev-test-coverage-checklist.md")),
        ("3.align-summary", check_file(c3, "align-summary.md")),
        ("4.summary-content", check_summary(c3)),
        ("5.canon-gaps", check_gaps_written(c3)),
    ]

    hard = {"1","2","3","4"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Traceback Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
