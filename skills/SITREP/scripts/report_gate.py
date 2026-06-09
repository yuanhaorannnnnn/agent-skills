#!/usr/bin/env python3
"""SITREP gate — verify checklist or final report.

Usage:
  python3 report_gate.py --mode checklist <checklist.md> [--json]
  python3 report_gate.py --mode report <report.md> --checklist <checklist.md> [--json]
"""

import json, sys
from pathlib import Path

def check_file(p, label):
    ok = Path(p).exists() and Path(p).stat().st_size > 100
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_not_empty(p, label):
    text = Path(p).read_text() if Path(p).exists() else ""
    item_count = text.count("\n- ") + text.count("\n* ")
    ok = item_count > 0
    return ok, f"{label}: {item_count} items" + (" OK" if ok else " FAIL (empty)")

def check_from_canon(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    has_canon = "/media/yhr/2T/Canon/tasks/" in text or "Canon" in text
    return has_canon, f"Canon source: {'present' if has_canon else 'NONE'}" + (" OK" if has_canon else " WARN")

def check_based_on_checklist(report, checklist):
    """Verify report is based on checklist, not fresh scan."""
    rtext = Path(report).read_text() if Path(report).exists() else ""
    ctext = Path(checklist).read_text() if Path(checklist).exists() else ""
    if not rtext or not ctext:
        return False, "based-on-checklist: missing files FAIL"
    # Weak proxy: report date >= checklist date
    ok = "checklist" in rtext.lower() or "confirmed" in rtext.lower()
    return ok, f"based-on-checklist: {'confirmed' if ok else 'UNCLEAR — was this from fresh scan?'}" + (" OK" if ok else " WARN")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["checklist", "report"])
    ap.add_argument("path", nargs="?", help="Path to checklist or report")
    ap.add_argument("--checklist", help="Path to checklist (report mode)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.path:
        print("usage: report_gate.py --mode <checklist|report> <path>", file=sys.stderr)
        sys.exit(2)

    if args.mode == "checklist":
        checks = [
            ("1.file", check_file(args.path, "checklist")),
            ("2.not-empty", check_not_empty(args.path, "checklist")),
            ("3.canon", check_from_canon(args.path)),
        ]
        hard = {"1","2"}
    else:
        if not args.checklist:
            print("--checklist required in report mode", file=sys.stderr)
            sys.exit(2)
        checks = [
            ("1.file", check_file(args.path, "report")),
            ("2.checklist-ref", check_file(args.checklist, "checklist")),
            ("3.based-on", check_based_on_checklist(args.path, args.checklist)),
            ("4.not-empty", check_not_empty(args.path, "report")),
        ]
        hard = {"1","2","3"}

    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"SITREP Gate ({args.mode}): {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
