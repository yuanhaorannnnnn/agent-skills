---
name: StandUp
description: Initialize or normalize a repository into the standard repo-local agent system layout. Use when a repository needs a local `AGENTS.md` index with inlined Guardrails and Agent System rules, `.agent-state/` runtime state, and `.planning/conversations/` planning conventions — especially when an existing `AGENTS.md` should be preserved and augmented rather than replaced. Use this skill whenever the user mentions bootstrapping an agent system, setting up AGENTS.md, initializing repo-local agent memory, normalizing a repo's agent structure, bootstrap a coding-agent repo, init agent conventions, or set up agent rules for a repository.
---

# Scaffold

Initialize a repo with the standard agent-system layout: `AGENTS.md` (index +
inlined rules) + `.agent-state/` (runtime state) + `.planning/` (task planning).
See `references/structure.md` for the full layout rationale.

## What it creates

- `AGENTS.md` — entry index with Guardrails and inlined Agent System block
- `.agent-state/MEMORY.md` — durable repo knowledge
- `.agent-state/rules/mistakes.md` — guardrails in ❌/✅ format
- `.planning/README.md`
- `.planning/conversations/.gitkeep`

## Workflow

1. Run `scripts/init_repo_agent_system.py --repo <repo-root>`
2. If `AGENTS.md` already exists, preserve all project content, only update
   the `<!-- BEGIN AGENT-SYSTEM -->` / `<!-- END AGENT-SYSTEM -->` block
3. Adjust wording for repo-specific conventions
4. Summarize what was created, updated, and preserved
