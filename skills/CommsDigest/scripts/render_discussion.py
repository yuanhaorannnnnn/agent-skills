#!/usr/bin/env python3
"""Phase 2: JSON → Interactive HTML.

Reads a structured discussion digest JSON from stdin or a file,
injects it into the HTML template, writes the result to stdout or a file.

Usage:
  python3 render_discussion.py < input.json > output.html
  python3 render_discussion.py input.json -o output.html
"""

import json, sys, os
from datetime import date
from pathlib import Path

SKILL_DIR = Path(os.environ.get("SKILL_DIR", Path(__file__).resolve().parent.parent))
TEMPLATE_PATH = SKILL_DIR / "templates" / "discussion-digest.html"


def _html(text: str) -> str:
    """Minimal HTML escaping."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def _build_participant_cards(participants: list) -> str:
    rows = []
    for p in participants:
        name = _html(p.get("name", ""))
        role = _html(p.get("role", ""))
        quote = _html(p.get("representative_quote", ""))
        rationale = _html(p.get("rationale", ""))
        rows.append(f"""      <div class="card">
        <div class="card-name">{name}</div>
        <div class="card-role">{role}</div>
        <div class="card-quote">{quote}</div>
        <div class="card-stance"><strong>立场</strong>&ensp;{rationale}</div>
      </div>""")
    return "\n".join(rows)


def _build_timeline(entries: list) -> str:
    rows = []
    for e in entries:
        date_str = _html(e.get("date", ""))
        author = _html(e.get("author", ""))
        text = _html(e.get("text", ""))
        is_key = e.get("is_key", False)
        why = _html(e.get("why_key", ""))
        key_cls = " key" if is_key else ""
        why_tag = f'<span class="tl-keyword">{why}</span>' if why else ""
        rows.append(f"""    <div class="tl-entry{key_cls}">
      <div class="tl-date">{date_str}</div>
      <div class="tl-body">
        <div class="tl-author">{author}{why_tag}</div>
        <div class="tl-text">{text}</div>
      </div>
    </div>""")
    return "\n".join(rows)


def _build_decisions(decisions: list) -> str:
    rows = []
    icon_map = {"decided": "✅", "leaning": "⚠️", "stalled": "🚫"}
    for d in decisions:
        icon = d.get("icon") or icon_map.get(d.get("status", ""), "📋")
        summary = _html(d.get("summary", ""))
        detail = _html(d.get("detail", ""))
        rows.append(f"""    <div class="d-entry">
      <div class="d-icon">{icon}</div>
      <div class="d-body"><strong>{summary}</strong><br>{detail}</div>
    </div>""")
    return "\n".join(rows)


def _build_unresolved(items: list) -> str:
    if not items:
        return "<ul><li>无</li></ul>"
    lis = "\n".join(f"        <li>{_html(item)}</li>" for item in items)
    return f"<ul>\n{lis}\n      </ul>"

def _build_action_items(items: list) -> str:
    if not items:
        return "<ul><li>无</li></ul>"
    lis = "\n".join(f"        <li>{_html(item)}</li>" for item in items)
    return f"<ul>\n{lis}\n      </ul>"


def _build_meta_pills(data: dict) -> str:
    p_count = data.get("participant_count", 0)
    m_count = data.get("message_count", 0)
    date_range = _html(data.get("date_range", ""))
    return (
        f'<span class="pill op">OP: {p_count}人参与</span>\n'
        f'        <span class="pill stats">📨 {m_count}条消息 &ensp; 🗓 {date_range}</span>'
    )


def render(data: dict, template: str) -> str:
    subs = {
        "PLACEHOLDER_TITLE": _html(data.get("title", "Untitled")),
        "PLACEHOLDER_SOURCE_ID": _html(data.get("source_id", "")),
        "PLACEHOLDER_SOURCE_URL": _html(data.get("source_url", "#")),
        "PLACEHOLDER_DATE": str(date.today()),
        "PLACEHOLDER_TLDR": _html(data.get("tldr", "")),
        "PLACEHOLDER_META_PILLS": _build_meta_pills(data),
        "PLACEHOLDER_PARTICIPANT_CARDS": _build_participant_cards(data.get("participants", [])),
        "PLACEHOLDER_TIMELINE": _build_timeline(data.get("timeline", [])),
        "PLACEHOLDER_DECISIONS": _build_decisions(data.get("decisions", [])),
        "PLACEHOLDER_UNRESOLVED": _build_unresolved(data.get("unresolved", [])),
        "PLACEHOLDER_ACTION_ITEMS": _build_action_items(data.get("action_items", [])),
    }
    html = template
    for placeholder, value in subs.items():
        html = html.replace(placeholder, value)
    return html


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Render discussion digest JSON → HTML")
    ap.add_argument("input", nargs="?", help="JSON input file (stdin if omitted)")
    ap.add_argument("-o", "--output", help="Output HTML file (stdout if omitted)")
    ap.add_argument("--template", default=str(TEMPLATE_PATH), help="Custom template path")
    args = ap.parse_args()

    # load JSON
    if args.input:
        with open(args.input) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    # load template
    with open(args.template) as f:
        template = f.read()

    result = render(data, template)

    if args.output:
        with open(args.output, "w") as f:
            f.write(result)
        print(f"→ {args.output}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
