#!/usr/bin/env python3
"""Dev wrapup helper: git status, task file matching, agent detection."""

import os
import re
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], cwd: Path | None = None) -> str:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True).stdout.strip()


def git_status(cwd: Path) -> list[tuple[str, str]]:
    """Return list of (status_code, filepath) from git status --short."""
    out = run(["git", "status", "--short"], cwd=cwd)
    files = []
    for line in out.splitlines():
        if len(line) >= 3:
            files.append((line[:2].strip(), line[3:].strip()))
    return files


def get_conversation_id(repo_root: Path) -> str | None:
    """Read .agent-state/ACTIVE_CONVERSATION or fallback to branch name."""
    active_file = repo_root / ".agent-state" / "ACTIVE_CONVERSATION"
    if active_file.exists():
        return active_file.read_text().strip()
    # fallback: current branch name
    branch = run(["git", "branch", "--show-current"], cwd=repo_root)
    return branch if branch else None


def get_task_files(repo_root: Path, conversation_id: str | None) -> set[str]:
    """Read task_plan.md and extract mentioned file paths."""
    if not conversation_id:
        return set()
    plan_file = (
        repo_root
        / ".planning"
        / "conversations"
        / conversation_id
        / "task_plan.md"
    )
    if not plan_file.exists():
        return set()
    content = plan_file.read_text()
    # Extract file paths from markdown code blocks and inline references
    files = set()
    # Match `path/to/file.ext` or "path/to/file.ext" or bare paths
    for pattern in [
        r'`([^`]+\.(?:py|sh|js|ts|md|yaml|yml|json|txt))`',
        r'\b([\w\-/]+\.(?:py|sh|js|ts|md|yaml|yml|json|txt))\b',
    ]:
        files.update(re.findall(pattern, content))
    return files


def filter_relevant_files(
    changed_files: list[tuple[str, str]], task_files: set[str]
) -> list[str]:
    """Return only changed files that match task scope."""
    if not task_files:
        return [f[1] for f in changed_files]
    relevant = []
    for _, filepath in changed_files:
        # Check if any task file is a substring match
        if any(tf in filepath or filepath in tf for tf in task_files):
            relevant.append(filepath)
    return relevant if relevant else [f[1] for f in changed_files]


def detect_agent() -> str:
    """Detect current agent runtime."""
    home = Path.home()
    checks = [
        (".claude", "claude"),
        (".codex", "codex"),
        (".kimi", "kimi"),
        (".pi", "pi"),
        (".hermes", "hermes"),
    ]
    for dirname, agent in checks:
        if (home / dirname).exists():
            return agent
    return "agents"


def generate_commit_message(
    repo_root: Path, files: list[str], conversation_id: str | None
) -> str:
    """Generate a conventional commit message based on changed files."""
    # Determine type based on files
    types = []
    for f in files:
        lower = f.lower()
        if "test" in lower:
            types.append("test")
        elif "doc" in lower or "readme" in lower or ".md" in lower:
            types.append("docs")
        elif "fix" in lower or "bug" in lower:
            types.append("fix")
        elif "refactor" in lower:
            types.append("refactor")
        else:
            types.append("feat")

    # Most common type
    commit_type = max(set(types), key=types.count) if types else "chore"

    # Determine scope from common directory
    dirs = [os.path.dirname(f) for f in files if os.path.dirname(f)]
    scope = os.path.commonpath(dirs) if dirs else "repo"

    # Generate description
    file_names = [os.path.basename(f) for f in files[:3]]
    desc = f"update {', '.join(file_names)}"
    if len(files) > 3:
        desc += f" and {len(files) - 3} more files"

    return f"{commit_type}({scope}): {desc}"


def update_progress(repo_root: Path, conversation_id: str | None, commit_hash: str, files: list[str]):
    """Append session log to progress.md."""
    if not conversation_id:
        return
    progress_file = (
        repo_root
        / ".planning"
        / "conversations"
        / conversation_id
        / "progress.md"
    )
    if not progress_file.exists():
        return

    from datetime import datetime

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    log = f"""\n## {now}\n- Completed: committed {len(files)} file(s)\n- Committed: `{commit_hash}`\n- Files changed: {', '.join(files[:5])}{'...' if len(files) > 5 else ''}\n"""

    with open(progress_file, "a") as f:
        f.write(log)


def main():
    repo_root = Path(run(["git", "rev-parse", "--show-toplevel"]) or ".")

    # 1. Git status
    changed = git_status(repo_root)
    if not changed:
        print("No changes to commit.")
        sys.exit(0)

    # 2. Get conversation + task files
    conv_id = get_conversation_id(repo_root)
    task_files = get_task_files(repo_root, conv_id)
    relevant = filter_relevant_files(changed, task_files)

    # 3. Generate commit message
    msg = generate_commit_message(repo_root, relevant, conv_id)
    print(f"Commit message: {msg}")
    print(f"Files to commit: {relevant}")

    # 4. Detect agent
    agent = detect_agent()
    print(f"Detected agent: {agent}")

    # Output JSON for LLM to consume
    import json

    result = {
        "conversation_id": conv_id,
        "changed_files": [f[1] for f in changed],
        "relevant_files": relevant,
        "commit_message": msg,
        "agent": agent,
        "task_files_found": list(task_files),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
