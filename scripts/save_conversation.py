#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import branch_name, codex_thread_id, ensure_state_dirs, repo_root


SUMMARY_HEADERS = (
    "Conversation Summary",
    "Current Objective",
    "Key Decisions",
    "Constraints",
    "Open Questions",
)

ACTION_HEADERS = (
    "Pending Follow-Ups",
    "Known Issues",
    "Key Context",
)

ACTIVE_CONVERSATION_FILE = "ACTIVE_CONVERSATION"


def parse_sections(text: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    current = None
    for line in text.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            sections.setdefault(current, [])
            continue
        if current:
            sections[current].append(line)
    return sections


def render_section(title: str, lines: list[str]) -> str:
    body = "\n".join(lines).rstrip()
    if not body:
        body = "- None"
    return f"## {title}\n{body}\n"


def conversation_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return slug or "conversation"


def active_conversation_name(state_dir: Path, branch: str, override: str) -> str:
    active_path = state_dir / ACTIVE_CONVERSATION_FILE
    if override:
        name = conversation_slug(override)
        active_path.write_text(name + "\n")
        return name

    thread_id = codex_thread_id()
    if thread_id:
        name = conversation_slug(thread_id)
        active_path.write_text(name + "\n")
        return name

    if active_path.exists():
        name = active_path.read_text().strip()
        if name:
            return name

    name = conversation_slug(branch)
    active_path.write_text(name + "\n")
    return name


def preserved_or_default(preserved: dict[str, list[str]], header: str) -> list[str]:
    lines = [line for line in preserved.get(header, []) if line.strip()]
    return lines or ["- None"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Persist current conversation context into .agent-state.")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--branch", default="", help="Optional branch override")
    parser.add_argument("--conversation", default="", help="Optional conversation name override")
    args = parser.parse_args()

    root = repo_root(Path(args.repo))
    state_dir = ensure_state_dirs(root)
    (state_dir / "conversations").mkdir(parents=True, exist_ok=True)
    branch = args.branch or branch_name(root)
    conversation_name = active_conversation_name(state_dir, branch, args.conversation)
    conversation_path = state_dir / "conversations" / f"{conversation_name}.md"

    existing = conversation_path.read_text(encoding="utf-8") if conversation_path.exists() else ""
    preserved = parse_sections(existing)

    output = [
        f"# Conversation Recap - {conversation_name}",
        "",
    ]

    for header in SUMMARY_HEADERS + ACTION_HEADERS:
        output.extend([render_section(header, preserved_or_default(preserved, header)).rstrip(), ""])

    for header, lines in preserved.items():
        if header in SUMMARY_HEADERS or header in ACTION_HEADERS:
            continue
        lines = [line for line in lines if line.strip()]
        output.extend([render_section(header, lines).rstrip(), ""])

    conversation_path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")

    # Always sync ACTIVE_CONVERSATION to the resolved name so cross-agent
    # restores always hit the same conversation file regardless of thread ID.
    active_path = state_dir / ACTIVE_CONVERSATION_FILE
    active_path.write_text(conversation_name + "\n")

    print(conversation_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
