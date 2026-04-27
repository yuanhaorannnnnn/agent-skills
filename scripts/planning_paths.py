#!/usr/bin/env python3
from __future__ import annotations

import os
import re
from pathlib import Path

from common import branch_name, repo_root


ACTIVE_CONVERSATION_FILE = "ACTIVE_CONVERSATION"


def conversation_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("._-")
    return slug or "conversation"


def active_conversation_name(root: Path, override: str | None = None) -> str:
    state_dir = root / ".agent-state"
    active_path = state_dir / ACTIVE_CONVERSATION_FILE

    if override:
        name = conversation_slug(override)
        state_dir.mkdir(parents=True, exist_ok=True)
        active_path.write_text(name + "\n", encoding="utf-8")
        return name

    if active_path.exists():
        name = active_path.read_text(encoding="utf-8").strip()
        if name:
            return conversation_slug(name)

    thread_id = os.environ.get("CODEX_THREAD_ID", "").strip()
    if thread_id:
        name = conversation_slug(thread_id)
        state_dir.mkdir(parents=True, exist_ok=True)
        active_path.write_text(name + "\n", encoding="utf-8")
        return name

    name = conversation_slug(branch_name(root))
    state_dir.mkdir(parents=True, exist_ok=True)
    active_path.write_text(name + "\n", encoding="utf-8")
    return name


def conversation_planning_dir(project_dir: Path, conversation: str | None = None) -> Path:
    root = repo_root(project_dir)
    name = active_conversation_name(root, conversation)
    return root / ".planning" / "conversations" / name
