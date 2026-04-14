#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


BEGIN_MARKER = "<!-- BEGIN AGENT-SYSTEM -->"
END_MARKER = "<!-- END AGENT-SYSTEM -->"

MANAGED_BLOCK = f"""{BEGIN_MARKER}
## Repo Agent System

### Conversation Save/Restore

- Active conversation pointer: `.agent-state/ACTIVE_CONVERSATION`
- Conversation summaries: `.agent-state/conversations/<conversation>.md`
- Conversation files should focus on conversation context, current goals, todos,
  and risks — not git state snapshots.
- Use conversation id as the primary key, not branch name.
- To create an independent new session, always specify a session name explicitly;
  do not rely on ACTIVE_CONVERSATION fallback.

### Planning

- Task planning files: `.planning/conversations/<conversation-id>/`
  - `spec.md`, `task_plan.md`, `findings.md`, `progress.md`
- Planning id can be a conversation id or a stable workflow name (e.g. `rpm_limit`).
- Do not keep planning files long-term in the repo root; migrate old files to the
  path above before continuing to maintain them.

### Source Of Truth Map

- Repo runtime memory + architecture: `.agent-state/MEMORY.md`
- Guardrails (durable + runtime): `.agent-state/rules/mistakes.md`
- Conversation recap: `.agent-state/conversations/<conversation>.md`
- Task planning: `.planning/conversations/<conversation-id>/`
{END_MARKER}
"""

MEMORY_MD = """# Repo Agent Memory

## Purpose

Record durable agent constraints and architecture knowledge that remain valid
across sessions. Put one-off task details in `.agent-state/conversations/`
and current task plans in `.planning/conversations/`.

## Repository Structure

<!-- Fill in repo-specific structure here -->

## Repo-Specific Constraints

<!-- Fill in repo-specific constraints here -->

## Durable Rules

<!-- Fill in durable rules here -->

## Layout Summary

- Repo-local index: `AGENTS.md`
- Runtime state: `.agent-state/`
- Task planning files: `.planning/conversations/<id>/`
- Guardrails: `.agent-state/rules/mistakes.md`
"""

MISTAKES_MD = """# Mistake Rules

<!-- Add guardrails in the format below as incidents occur.
     Each Rule should capture:
     - ❌ What went wrong
     - ✅ What to do instead
     - 触发场景: When this rule applies
-->

## Rule
❌ 错误做法: Example of the wrong approach.
✅ 正确做法: Example of the correct approach.
触发场景: When this rule triggers.
"""

PLANNING_README = """# Planning Workspace

This directory stores conversation-scoped planning files.

Default structure:

```text
.planning/
└── conversations/
    └── <conversation-id>/
        ├── spec.md
        ├── task_plan.md
        ├── findings.md
        └── progress.md
```
"""

CLAUDE_MD = """@AGENTS.md
"""


def write_if_missing(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text(content.rstrip() + "\n", encoding="utf-8")


def upsert_agents_md(path: Path) -> str:
    if not path.exists():
        path.write_text(
            "# Repo Agent Index\n\n"
            "This file is the repo-local entry index for the local agent system.\n\n"
            f"{MANAGED_BLOCK}\n",
            encoding="utf-8",
        )
        return "created"

    existing = path.read_text(encoding="utf-8")
    if BEGIN_MARKER in existing and END_MARKER in existing:
        before, rest = existing.split(BEGIN_MARKER, 1)
        _, after = rest.split(END_MARKER, 1)
        updated = before.rstrip() + "\n\n" + MANAGED_BLOCK + after
        path.write_text(updated.rstrip() + "\n", encoding="utf-8")
        return "updated_managed_block"

    updated = existing.rstrip() + "\n\n" + MANAGED_BLOCK + "\n"
    path.write_text(updated, encoding="utf-8")
    return "appended_managed_block"


def upsert_claude_md(path: Path) -> str:
    """Create CLAUDE.md as a single-line @AGENTS.md import pointer.

    CLAUDE.md is the Claude Code entrypoint. Rather than duplicating content,
    it imports AGENTS.md via the @-import syntax so AGENTS.md remains the
    single source of truth. Any Claude Code-specific additions can be appended
    after the import line.
    """
    if not path.exists():
        path.write_text(CLAUDE_MD, encoding="utf-8")
        return "created"
    existing = path.read_text(encoding="utf-8")
    if "@AGENTS.md" in existing:
        return "already_present"
    # Prepend the import so it loads before any existing content
    updated = "@AGENTS.md\n" + existing.lstrip()
    path.write_text(updated, encoding="utf-8")
    return "prepended_import"


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize repo-local agent system files.")
    parser.add_argument("--repo", default=".", help="Repository root")
    args = parser.parse_args()

    root = Path(args.repo).resolve()

    agents_status = upsert_agents_md(root / "AGENTS.md")
    claude_status = upsert_claude_md(root / "CLAUDE.md")

    agent_state = root / ".agent-state"
    write_if_missing(agent_state / "MEMORY.md", MEMORY_MD)
    write_if_missing(agent_state / "rules" / "mistakes.md", MISTAKES_MD)

    write_if_missing(root / ".planning" / "README.md", PLANNING_README)
    write_if_missing(root / ".planning" / "conversations" / ".gitkeep", "")

    print(f"AGENTS.md:  {agents_status}")
    print(f"CLAUDE.md:  {claude_status}")
    print(f"Agent state: {agent_state}")
    print(f"Planning root: {root / '.planning'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
