#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
from pathlib import Path


def run(cmd: list[str], cwd: Path) -> str:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=True,
    ).stdout


def git_output(repo: Path, args: list[str], default: str = "") -> str:
    try:
        return run(["git", *args], repo).strip()
    except subprocess.CalledProcessError:
        return default


def branch_name(repo: Path) -> str:
    branch = git_output(repo, ["branch", "--show-current"])
    if branch:
        return branch
    branch = git_output(repo, ["rev-parse", "--abbrev-ref", "HEAD"], "detached-head")
    return branch or "detached-head"


def repo_root(repo: Path) -> Path:
    root = git_output(repo, ["rev-parse", "--show-toplevel"])
    return Path(root) if root else repo.resolve()


def ensure_state_dirs(root: Path) -> Path:
    state_dir = root / ".agent-state"
    (state_dir / "sessions").mkdir(parents=True, exist_ok=True)
    (state_dir / "rules").mkdir(parents=True, exist_ok=True)
    return state_dir


def codex_thread_id() -> str:
    return os.environ.get("CODEX_THREAD_ID", "").strip()
