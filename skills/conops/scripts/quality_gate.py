#!/usr/bin/env python3
"""CONOPS quality gate — script-check what can be script-checked.

Usage:
  python3 quality_gate.py <design_doc.md-or-index.html> [--json]
"""

import json, re, sys
from pathlib import Path
from html.parser import HTMLParser

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

class DesignHTML(HTMLParser):
    """Normalize static HTML headings/lists for the existing text checks."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"head", "script", "style", "template"}:
            self.ignored += 1
        if self.ignored:
            return
        if re.fullmatch(r"h[1-6]", tag):
            self.parts.append("\n\x00heading " + "#" * int(tag[1]) + " ")
        elif tag == "li":
            self.parts.append("\n\x00li ")
        elif tag in {"p", "div", "section", "br", "tr", "ul", "ol", "pre"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"head", "script", "style", "template"} and self.ignored:
            self.ignored -= 1
            return
        if not self.ignored and (re.fullmatch(r"h[1-6]", tag) or tag in {"li", "p", "div", "section", "tr", "pre"}):
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored:
            # Source indentation must not split headings or inline prose.
            self.parts.append(re.sub(r"\s+", " ", data))


def read_text(p):
    path = Path(p)
    if not path.exists():
        return ""
    text = path.read_text()
    if path.suffix.lower() in {".html", ".htm"}:
        parser = DesignHTML()
        parser.feed(text)
        return "".join(parser.parts)
    return text

def check_file(p):
    ok = Path(p).exists() and Path(p).stat().st_size > 100
    return ok, f"file: {'found' if ok else 'missing or too small'}" + (" OK" if ok else " FAIL")

def check_forbidden(p):
    text = read_text(p)
    hits = []
    for word in FORBIDDEN:
        if word in text:
            hits.append(word)
    ok = len(hits) == 0
    detail = f"({len(hits)} hit(s): {', '.join(hits[:5])})" if hits else "clean"
    return ok, f"禁词: {detail}" + (" OK" if ok else " FAIL")

def check_sections(p):
    text = read_text(p)
    if Path(p).suffix.lower() in {".html", ".htm"}:
        text = "\n".join(re.findall(r"^\x00heading #+[^\n]*", text, re.MULTILINE))
    missing = []
    for sec in REQUIRED_SECTIONS:
        if sec not in text:
            missing.append(sec)
    ok = len(missing) == 0
    detail = f"missing: {missing}" if missing else "all 14 present"
    return ok, f"sections: {detail}" + (" OK" if ok else " FAIL")

def check_scope_balance(p):
    text = read_text(p)
    is_html = Path(p).suffix.lower() in {".html", ".htm"}
    if is_html:
        def scope_section(title):
            match = re.search(r'^\x00heading #+\s+' + title + r'\s*\n(.*?)(?=^\x00heading #+|\Z)',
                              text, re.MULTILINE | re.DOTALL)
            return match.group(1) if match else ""
        include_section = scope_section("本次包含")
        exclude_section = scope_section("本次不包含")
    else:
        include_section = text.split("本次包含")[1].split("本次不包含")[0] if "本次包含" in text and "本次不包含" in text else ""
        exclude_section = text.split("本次不包含")[1].split("\n#")[0] if "本次不包含" in text else ""
    item = r'^\s*\x00li ' if is_html else r'^\s*[-*]\s'
    inc = len(re.findall(item, include_section, re.MULTILINE))
    exc = len(re.findall(item, exclude_section, re.MULTILINE))
    ok = exc >= inc and (inc > 0 if is_html else True)
    failure = "missing scope items or exclude < include" if is_html else "exclude < include"
    return ok, f"scope: include={inc} exclude={exc}" + (" OK" if ok else f" FAIL ({failure})")

def check_word_counts(p):
    text = read_text(p)
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
        print("usage: quality_gate.py <design_doc.md-or-index.html>", file=sys.stderr)
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
