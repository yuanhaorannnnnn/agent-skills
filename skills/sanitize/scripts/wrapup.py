#!/usr/bin/env python3
"""Dev wrapup helper: git status, task file matching, agent detection.

Canon-first: task identity comes from Canon task pages, not .agent-state/.
"""

import os
import re
import subprocess
import sys
from pathlib import Path


CANON_TASKS = Path("/media/yhr/2T/Canon/tasks")


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


def resolve_task_page(repo_root: Path) -> Path | None:
    """Resolve the Canon task page for the current work.

    Priority: explicit env var > branch-based match > semantic scan > None.
    Returns Path to task page or None.
    """
    # 1. Explicit override via env
    explicit = os.environ.get("CANON_TASK_PAGE")
    if explicit:
        p = Path(explicit)
        if p.exists():
            return p

    # 2. Project + branch match
    branch = run(["git", "branch", "--show-current"], cwd=repo_root)
    if branch:
        project = repo_root.name
        # Try demand/bug ID pattern in branch name
        demand_match = re.match(r"(?:feature|bugfix|fix)/([\w-]+)", branch)
        if demand_match:
            candidate = CANON_TASKS / f"{demand_match.group(1)}.md"
            if candidate.exists():
                return candidate
        # Try project-branch pattern
        safe_branch = re.sub(r"[^A-Za-z0-9_.-]+", "-", branch).strip("-")
        candidate = CANON_TASKS / f"{project}-{safe_branch}.md"
        if candidate.exists():
            return candidate

    # 3. Semantic scan — find task pages referencing this project/branch
    if CANON_TASKS.exists() and branch:
        for tf in sorted(CANON_TASKS.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            content = tf.read_text()
            if branch in content or repo_root.name in content:
                return tf

    return None


def get_task_files_from_canon(task_page: Path | None) -> set[str]:
    """Read § Artifacts from a Canon task page to extract file paths."""
    if not task_page or not task_page.exists():
        return set()
    content = task_page.read_text()
    files = set()
    # Extract paths from § Artifacts section and inline code references
    for pattern in [
        r'`([^`]+\.(?:py|sh|js|ts|md|yaml|yml|json|txt))`',
        r'(/[\w\-/]+\.(?:py|sh|js|ts|md|yaml|yml|json|txt))',
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
    ]
    for dirname, agent in checks:
        if (home / dirname).exists():
            return agent
    return "agents"


def generate_commit_message(
    repo_root: Path, files: list[str], task_page: Path | None
) -> str:
    """Generate a conventional commit message based on changed files."""
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

    commit_type = max(set(types), key=types.count) if types else "chore"

    dirs = [os.path.dirname(f) for f in files if os.path.dirname(f)]
    scope = os.path.commonpath(dirs) if dirs else "repo"

    file_names = [os.path.basename(f) for f in files[:3]]
    desc = f"update {', '.join(file_names)}"
    if len(files) > 3:
        desc += f" and {len(files) - 3} more files"

    return f"{commit_type}({scope}): {desc}"


def canon_update_card_suggestion(
    repo_root: Path, task_page: Path | None
) -> dict:
    """Return Canon paths that should be considered after wrapup."""
    canon_root = Path("/media/yhr/2T/Canon")
    branch = run(["git", "branch", "--show-current"], cwd=repo_root)
    slug_source = (task_page.stem if task_page else
                   branch or repo_root.name)
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", slug_source.strip()).strip("-").lower() or "wrapup"
    from datetime import datetime

    date = datetime.now().strftime("%Y%m%d")
    return {
        "canon_root": str(canon_root),
        "schema": str(canon_root / "SCHEMA.md"),
        "task_page": str(task_page) if task_page else None,
        "suggested_update_card": str(
            canon_root / "raw" / "update-cards" / f"{date}-{slug}-wrapup.md"
        ),
        "artifact_policy": "reference absolute paths; do not copy repo artifacts by default",
    }


def main():
    repo_root = Path(run(["git", "rev-parse", "--show-toplevel"]) or ".")

    # 1. Git status
    changed = git_status(repo_root)
    if not changed:
        print("No changes to commit.")
        sys.exit(0)

    # 2. Resolve task page via Canon
    task_page = resolve_task_page(repo_root)
    task_files = get_task_files_from_canon(task_page)
    relevant = filter_relevant_files(changed, task_files)

    # 3. Generate commit message
    msg = generate_commit_message(repo_root, relevant, task_page)
    print(f"Commit message: {msg}")
    print(f"Files to commit: {relevant}")

    # 4. Detect agent
    agent = detect_agent()
    print(f"Detected agent: {agent}")

    import json

    result = {
        "task_page": str(task_page) if task_page else None,
        "changed_files": [f[1] for f in changed],
        "relevant_files": relevant,
        "commit_message": msg,
        "agent": agent,
        "task_files_found": list(task_files),
        "canon": canon_update_card_suggestion(repo_root, task_page),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
