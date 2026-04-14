#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import branch_name, codex_thread_id, ensure_state_dirs, repo_root
from save_conversation import ACTIVE_CONVERSATION_FILE, conversation_slug


def first_useful_line(text: str, section: str) -> str:
    current = None
    for raw in text.splitlines():
        line = raw.strip()
        if raw.startswith("## "):
            current = raw[3:].strip()
            continue
        if current == section and line and line != "- None":
            return line.lstrip("- ").strip()
    return ""


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore saved conversation context from .agent-state.")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--branch", default="", help="Optional branch override")
    parser.add_argument("--conversation", default="", help="Optional conversation name override")
    args = parser.parse_args()

    root = repo_root(Path(args.repo))
    state_dir = ensure_state_dirs(root)
    (state_dir / "conversations").mkdir(parents=True, exist_ok=True)
    branch = args.branch or branch_name(root)
    active_path = state_dir / ACTIVE_CONVERSATION_FILE
    conversation_name = args.conversation.strip()
    if not conversation_name:
        thread_id = codex_thread_id()
        if thread_id:
            conversation_name = conversation_slug(thread_id)
        elif active_path.exists():
            conversation_name = active_path.read_text().strip()
        else:
            conversation_name = conversation_slug(branch)
    conversation_path = state_dir / "conversations" / f"{conversation_name}.md"
    memory_path = state_dir / "MEMORY.md"

    if not conversation_path.exists():
        print(f"No saved conversation for conversation '{conversation_name}'. Expected: {conversation_path}")
        return 1

    conversation_text = conversation_path.read_text(encoding="utf-8")
    conversation_summary = first_useful_line(conversation_text, "Conversation Summary")
    current_objective = first_useful_line(conversation_text, "Current Objective")
    pending = first_useful_line(conversation_text, "Pending Follow-Ups")
    known_issues = first_useful_line(conversation_text, "Known Issues")
    key_context = first_useful_line(conversation_text, "Key Context")

    next_task = pending or known_issues or key_context or current_objective
    if not next_task:
        next_task = "Review the saved conversation file and continue from the latest context."

    print(f"Conversation restored: {conversation_path}")
    print(f"Conversation name: {conversation_name}")
    print(f"Current branch: {branch}")
    print(f"Memory: {memory_path if memory_path.exists() else 'not created yet'}")
    if conversation_summary:
        print(f"Conversation summary: {conversation_summary}")
    if current_objective:
        print(f"Current objective: {current_objective}")
    print(f"Next focus: {next_task}")
    if key_context:
        print(f"Key context: {key_context}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
