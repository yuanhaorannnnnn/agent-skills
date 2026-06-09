#!/usr/bin/env python3
"""Secure gate — verify Canon task page was actually written.

Usage:
  python3 write_gate.py --task <canon-task-path> [--json]
"""

import json, sys
from pathlib import Path

def check_file(p):
    ok = Path(p).exists() and Path(p).stat().st_size > 100
    return ok, f"task page: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_frontmatter(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    has_status = "status:" in text
    has_updated = "updated:" in text
    ok = has_status and has_updated
    return ok, f"frontmatter: status={'OK' if has_status else 'MISSING'} updated={'OK' if has_updated else 'MISSING'}" + (" OK" if ok else " FAIL")

def check_sections(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    missing = []
    for sec in ["## Goal", "## Current State", "## Next Step"]:
        if sec not in text:
            missing.append(sec)
    ok = len(missing) == 0
    return ok, f"sections: {'all 3 stable' if ok else f'missing: {missing}'}" + (" OK" if ok else " FAIL")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks = [
        ("1.file", check_file(args.task)),
        ("2.frontmatter", check_frontmatter(args.task)),
        ("3.sections", check_sections(args.task)),
    ]

    hard = {"1","2","3"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Secure Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
