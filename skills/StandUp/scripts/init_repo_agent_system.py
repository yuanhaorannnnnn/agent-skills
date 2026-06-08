#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


BEGIN_MARKER = "<!-- BEGIN AGENT-SYSTEM -->"
END_MARKER = "<!-- END AGENT-SYSTEM -->"

MANAGED_BLOCK = f"""{BEGIN_MARKER}
## Repo Agent System

### Canon Context

- Durable cross-project context belongs in Canon: `/media/yhr/2T/Canon`
- Repo-local `.agent-state/`, `.planning/`, `.research/`, and `.proposal/` are runtime buffers and artifact locations, not long-term source of truth.
- When a task, decision, incident, workflow, pattern, or artifact should survive the current conversation, create or update a Canon update card under `/media/yhr/2T/Canon/raw/update-cards/` and link the relevant Canon page.
- Reference repo artifacts by absolute path; do not copy them into Canon unless a portable bundle is explicitly requested.

### Conversation Save/Restore

- Active conversation pointer: `.agent-state/ACTIVE_CONVERSATION`
- Conversation summaries: `.agent-state/conversations/<conversation>.md`
- Conversation files are runtime resume buffers: current objective, todos, risks, next focus, and Canon links.
- Use conversation id as the runtime key, not branch name.
- To create an independent new session, always specify a session name explicitly; do not rely on ACTIVE_CONVERSATION fallback.

### Planning

- Runtime task planning files: `.planning/conversations/<conversation-id>/`
  - `spec.md`, `task_plan.md`, `findings.md`, `progress.md`
- Planning id can be a conversation id or a stable workflow name.
- For durable task state, use Canon task pages: `/media/yhr/2T/Canon/tasks/<task>.md`
- Do not keep long-term planning files in the repo root.

### Source Of Truth Map

- Durable project/task graph: `/media/yhr/2T/Canon`
- Repo-local index: `AGENTS.md`
- Runtime conversation recap: `.agent-state/conversations/<conversation>.md`
- Runtime task planning: `.planning/conversations/<conversation-id>/`
- Local guardrail scratchpad: `.agent-state/rules/mistakes.md`
{END_MARKER}
"""

MEMORY_MD = """# Repo Agent Runtime Notes

## Purpose

Record repo-local runtime notes and pointers that help agents operate in this repository. Durable cross-project memory belongs in Canon:

```text
/media/yhr/2T/Canon
```

Put one-off task details in `.agent-state/conversations/` and active execution plans in `.planning/conversations/`. Promote stable facts to Canon project/task/decision/pattern/incident/artifact pages.

## Canon Links

- Project page: <!-- /media/yhr/2T/Canon/projects/<project>.md -->
- Active task pages: <!-- /media/yhr/2T/Canon/tasks/<task>.md -->
- Relevant workflows/patterns/decisions/incidents: <!-- Canon links here -->

## Repository Structure

<!-- Fill in repo-specific structure here -->

## Repo-Specific Runtime Constraints

<!-- Fill in repo-local constraints here -->

## Local Notes

<!-- Keep short. Promote durable facts to Canon. -->

## Layout Summary

- Repo-local index: `AGENTS.md`
- Runtime state: `.agent-state/`
- Runtime task planning files: `.planning/conversations/<id>/`
- Durable context graph: `/media/yhr/2T/Canon`
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

This directory stores runtime conversation-scoped planning files. Durable task state belongs in Canon: `/media/yhr/2T/Canon/tasks/`.

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
