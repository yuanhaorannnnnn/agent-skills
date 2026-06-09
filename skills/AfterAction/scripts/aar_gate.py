#!/usr/bin/env python3
"""AfterAction gate — verify sections and no forbidden words.

Usage:
  python3 aar_gate.py <report.md> [--json]
"""

import json, sys
from pathlib import Path

FORBIDDEN = [
    "此外", "值得注意的是", "综上所述", "显著提升", "进行了相关调整",
    "赋能", "助力", "全方位", "深入探讨", "不言而喻", "不可或缺",
]

REQUIRED = ["背景", "踩过的坑", "最终方案", "判断", "沉淀"]
VALID_VERDICTS = ["临时 hack", "彻底修复", "值得沉淀"]

def check_file(p):
    ok = Path(p).exists() and Path(p).stat().st_size > 50
    return ok, f"file: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_sections(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    missing = [s for s in REQUIRED if s not in text]
    ok = len(missing) == 0
    return ok, f"sections: {'all 5' if ok else f'missing: {missing}'}" + (" OK" if ok else " FAIL")

def check_verdict(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    found = [v for v in VALID_VERDICTS if v in text]
    ok = len(found) > 0
    return ok, f"verdict: {'picked: ' + found[0] if found else 'NONE'}" + (" OK" if ok else " FAIL")

def check_forbidden(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    hits = [w for w in FORBIDDEN if w in text]
    ok = len(hits) == 0
    return ok, f"禁词: {'clean' if ok else f'{len(hits)} hit(s): {hits[:3]}'}" + (" OK" if ok else " WARN")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("report", nargs="?")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.report:
        print("usage: aar_gate.py <report.md>", file=sys.stderr)
        sys.exit(2)

    checks = [
        ("1.file", check_file(args.report)),
        ("2.sections", check_sections(args.report)),
        ("3.verdict", check_verdict(args.report)),
        ("4.forbidden", check_forbidden(args.report)),
    ]

    hard = {"1","2","3"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"AfterAction Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
