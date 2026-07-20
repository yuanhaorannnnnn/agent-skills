#!/usr/bin/env python3
"""
Kimi Code hooks handler — reminder-only mode.

Reminds the user to update the current Canon task page directly and use
Passdown for hot runtime context.

Supported events:
  - PreCompact:   remind user to update Canon before context is lost
  - SessionStart: remind user to resume from Canon and optionally use Passdown
  - SessionEnd:   remind user to update Canon before leaving

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


def resolve_task_page(cwd: Path) -> str | None:
    """Resolve likely Canon task page from branch or project name."""
    import subprocess
    try:
        branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd, text=True, capture_output=True
        ).stdout.strip()
        if branch:
            return f"/media/yhr/2T/Canon/tasks/ (project={cwd.name}, branch={branch})"
    except Exception:
        pass
    return f"/media/yhr/2T/Canon/tasks/ (project={cwd.name})"


def print_reminder(message: str) -> None:
    print(message, file=sys.stderr)


def handle_pre_compact(cwd: Path) -> None:
    task_hint = resolve_task_page(cwd)
    print_reminder(
        f"\n[上下文即将压缩] 建议先保存进度到 Canon task page：\n"
        f"   直接更新当前 task page\n"
        f"   → {task_hint}\n"
    )


def handle_session_start(cwd: Path) -> None:
    task_hint = resolve_task_page(cwd)
    print_reminder(
        f"\n[会话已启动] 如需恢复之前的上下文：\n"
        f"   先读取 Canon task page；需要热上下文时调用 Passdown\n"
        f"   → {task_hint}\n"
    )


def handle_session_end(cwd: Path) -> None:
    task_hint = resolve_task_page(cwd)
    print_reminder(
        f"\n[会话即将结束] 建议先保存进度：\n"
        f"   直接更新当前 Canon task page\n"
        f"   → {task_hint}\n"
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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
