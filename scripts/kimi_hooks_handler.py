#!/usr/bin/env python3
"""
Kimi Code hooks handler — reminder-only mode.

Instead of auto-running save/restore scripts (which cannot generate AI-quality
summaries), this handler prints actionable reminders to the terminal so the
user is prompted to run the skill explicitly.

Supported events:
  - PreCompact:   remind user to $save-conversation before context is lost
  - SessionStart: remind user to $restore-conversation to resume context
  - SessionEnd:   remind user to $save-conversation before exiting

Install in ~/.kimi/config.toml:

    [[hooks]]
    event = "PreCompact"
    command = "python3 ~/.agents/skills/.scripts/kimi_hooks_handler.py"
    timeout = 10

    [[hooks]]
    event = "SessionStart"
    command = "python3 ~/.agents/skills/.scripts/kimi_hooks_handler.py"
    timeout = 10
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def active_conversation(cwd: Path) -> str | None:
    """Read ACTIVE_CONVERSATION from repo-local .agent-state."""
    active_file = cwd / ".agent-state" / "ACTIVE_CONVERSATION"
    if active_file.exists():
        name = active_file.read_text().strip()
        if name:
            return name
    return None


def print_reminder(message: str) -> None:
    """Print a visible terminal reminder."""
    # Use stderr so it appears even in non-interactive modes
    print(message, file=sys.stderr)


def handle_pre_compact(cwd: Path) -> None:
    """Remind user to save before context compaction."""
    conversation = active_conversation(cwd)
    if conversation:
        print_reminder(
            f"\n[⚠️ 上下文即将压缩] 建议先执行保存，防止跨 agent 切换时丢失进度：\n"
            f"   $save-conversation --conversation {conversation}\n"
        )
    else:
        print_reminder(
            "\n[⚠️ 上下文即将压缩] 建议先执行保存：\n"
            "   $save-conversation\n"
            "   （或先设置 conversation ID：echo 'name' > .agent-state/ACTIVE_CONVERSATION）\n"
        )


def handle_session_start(cwd: Path) -> None:
    """Remind user to restore conversation on session start."""
    conversation = active_conversation(cwd)
    if conversation:
        print_reminder(
            f"\n[💡 会话已启动] 如需恢复之前的上下文，请执行：\n"
            f"   $restore-conversation --conversation {conversation}\n"
        )
    else:
        print_reminder(
            "\n[💡 会话已启动] 如需恢复之前的上下文，请执行：\n"
            "   $restore-conversation\n"
            "   （或先设置 conversation ID：echo 'name' > .agent-state/ACTIVE_CONVERSATION）\n"
        )


def handle_session_end(cwd: Path) -> None:
    """Remind user to save before exiting."""
    conversation = active_conversation(cwd)
    if conversation:
        print_reminder(
            f"\n[⚠️ 会话即将结束] 建议先执行保存：\n"
            f"   $save-conversation --conversation {conversation}\n"
        )
    else:
        print_reminder(
            "\n[⚠️ 会话即将结束] 建议先执行保存：\n"
            "   $save-conversation\n"
        )


def main() -> int:
    payload = json.load(sys.stdin)
    event = payload.get("hook_event_name", "")
    cwd = Path(payload.get("cwd", os.getcwd()))

    if event == "PreCompact":
        handle_pre_compact(cwd)
    elif event == "SessionStart":
        handle_session_start(cwd)
    elif event == "SessionEnd":
        handle_session_end(cwd)
    else:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
