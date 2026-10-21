#!/usr/bin/env python3
"""Legacy CLI name; structure lint only, never design approval."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re


class DesignHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.ignored = 0

    def handle_starttag(self, tag, attrs):
        if tag in {'head', 'script', 'style', 'template'} or re.fullmatch(r'h[1-6]', tag):
            self.ignored += 1
        if not self.ignored and tag in {'p', 'div', 'li', 'br', 'tr', 'section'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'head', 'script', 'style', 'template'} or re.fullmatch(r'h[1-6]', tag):
            self.ignored = max(0, self.ignored - 1)
        if not self.ignored and tag in {'p', 'div', 'li', 'tr', 'section'}:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.ignored:
            self.parts.append(data)


def lint(path):
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError) as exc:
        return [f'unreadable file ({type(exc).__name__})']
    if path.suffix.lower() in {'.html', '.htm'}:
        parser = DesignHTML()
        parser.feed(text)
        text = ''.join(parser.parts)
    else:
        text = re.sub(r'\A---\s*\n.*?\n---\s*(?:\n|$)', '', text, flags=re.S)
        text = re.sub(r'<!--.*?-->', '', text, flags=re.S)
        text = re.sub(r'^\s*#{1,6}\s+.*$', '', text, flags=re.M)
    body = [re.sub(r'^[\s>*\-\d.)]+', '', line).strip() for line in text.splitlines()]
    substantive = [line for line in body if line and not re.fullmatch(
        r'(?:待定|待补充|TODO|TBD|placeholder|N/A|[.。…—\-]+)[\s.。!！:：]*', line, re.I)]
    return [] if substantive else ['missing non-heading, non-placeholder body']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('doc', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    failed = lint(args.doc)
    result = {'verdict': 'blocked' if failed else 'pass', 'failed': failed,
              'check_kind': 'structure_lint', 'semantic_review': 'required'}
    print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
          f"CONOPS structure lint: {result['verdict']}; semantic review required\n" + '\n'.join(failed))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
