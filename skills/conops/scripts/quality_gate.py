#!/usr/bin/env python3
"""CONOPS quality gate — script-check what can be script-checked.

Usage:
  python3 quality_gate.py <design_doc.md> [--json]
"""

import json, re, sys
from pathlib import Path

FORBIDDEN = [
    "此外", "值得注意的是", "需要强调的是", "综上所述", "通过...实现", "基于...进行",
    "显著提升", "深入探讨", "全方位", "赋能", "助力", "在...的过程中", "其目的在于",
    "能够有效地", "具有以下优势", "不言而喻", "不可或缺", "重中之重",
    "本方案具有以下显著优势", "需要指出的是", "在当今...的时代背景下",
]

REQUIRED_SECTIONS = [
    "Executive Summary", "背景与问题", "方案范围", "用户可见行为",
    "Architecture", "Core Logic", "Protocol And Data Model",
    "Product Review Points", "Test Review Points", "Acceptance Criteria",
    "Risks And Mitigations", "Code Navigation", "Current Status And Next Steps",
    "Review Decision Checklist",
]

def check_file(p):
    ok = Path(p).exists() and Path(p).stat().st_size > 100
    return ok, f"file: {'found' if ok else 'missing or too small'}" + (" OK" if ok else " FAIL")

def check_forbidden(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    hits = []
    for word in FORBIDDEN:
        if word in text:
            hits.append(word)
    ok = len(hits) == 0
    detail = f"({len(hits)} hit(s): {', '.join(hits[:5])})" if hits else "clean"
    return ok, f"禁词: {detail}" + (" OK" if ok else " FAIL")

def check_sections(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    missing = []
    for sec in REQUIRED_SECTIONS:
        if sec not in text:
            missing.append(sec)
    ok = len(missing) == 0
    detail = f"missing: {missing}" if missing else "all 14 present"
    return ok, f"sections: {detail}" + (" OK" if ok else " FAIL")

def check_scope_balance(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    include_section = text.split("本次包含")[1].split("本次不包含")[0] if "本次包含" in text and "本次不包含" in text else ""
    exclude_section = text.split("本次不包含")[1].split("\n#")[0] if "本次不包含" in text else ""
    inc = len(re.findall(r'^\s*[-*]\s', include_section, re.MULTILINE))
    exc = len(re.findall(r'^\s*[-*]\s', exclude_section, re.MULTILINE))
    ok = exc >= inc
    return ok, f"scope: include={inc} exclude={exc}" + (" OK" if ok else f" FAIL (exclude < include)")

def check_word_counts(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    jianyi = len(re.findall(r'建议', text))
    xuyao = len(re.findall(r'需要', text))
    houxu = len(re.findall(r'后续', text))
    issues = []
    if xuyao > 10: issues.append(f"需要={xuyao}>10")
    if jianyi > 8: issues.append(f"建议={jianyi}>8")
    if houxu > 5: issues.append(f"后续={houxu}>5")
    ok = len(issues) == 0
    return ok, f"word counts: 需要={xuyao} 建议={jianyi} 后续={houxu}" + (" OK" if ok else f" WARN ({', '.join(issues)})")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("doc", nargs="?", help="Path to design doc")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.doc:
        print("usage: quality_gate.py <design_doc.md>", file=sys.stderr)
        sys.exit(2)

    checks = [
        ("1.file", check_file(args.doc)),
        ("2.forbidden", check_forbidden(args.doc)),
        ("3.sections", check_sections(args.doc)),
        ("4.scope", check_scope_balance(args.doc)),
        ("5.words", check_word_counts(args.doc)),
    ]

    hard = {"1","2","3","4"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"CONOPS Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
