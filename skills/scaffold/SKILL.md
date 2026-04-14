---
name: scaffold
description: Initialize or normalize a repository into the standard repo-local agent system layout. Use when a repository needs a local `AGENTS.md` index with inlined Guardrails and Agent System rules, `.agent-state/` runtime state, and `.planning/conversations/` planning conventions — especially when an existing `AGENTS.md` should be preserved and augmented rather than replaced. Use this skill whenever the user mentions bootstrapping an agent system, setting up AGENTS.md, initializing repo-local agent memory, or normalizing a repo's agent structure.
---

# Repo Agent Bootstrap

Initialize a repository so it follows the simplified two-layer repo agent-system
structure without destroying existing project guidance.

## Structure Overview

See `references/structure.md` for the full layout rationale. In short:

- `AGENTS.md` — entry index + inlined Guardrails + inlined Agent System rules
- `.agent-state/` — all runtime state (MEMORY.md, mistakes, conversation recaps)
- `.planning/conversations/` — task planning files per conversation

There is no `docs/agent-system/` layer. Rules are inlined directly into `AGENTS.md`
and the runtime state files to reduce indirection.

## Workflow

1. Inspect the repository root for an existing `AGENTS.md`.
2. Run `scripts/init_repo_agent_system.py --repo <repo-root>` to create or
   normalize:
   - `AGENTS.md` (with inlined Guardrails + Agent System block)
   - `.agent-state/MEMORY.md`
   - `.agent-state/rules/mistakes.md`
   - `.planning/README.md`
   - `.planning/conversations/.gitkeep`
3. If `AGENTS.md` already exists, preserve all project-specific content and only
   manage the `<!-- BEGIN AGENT-SYSTEM -->` block.
4. Adjust wording when the repository has specific conventions the templates
   don't already express (e.g., repo-local build skills, language preferences).
5. Summarize what was created, what was updated, and what was preserved.

## What This Skill Creates

- `AGENTS.md` — repo-local index with Guardrails section and inlined Agent System rules
- `.agent-state/MEMORY.md` — durable repo knowledge + architecture notes
- `.agent-state/rules/mistakes.md` — guardrails in ❌/✅ incident format
- `.planning/README.md`
- `.planning/conversations/.gitkeep`

## Compatibility Rule

When the repository already contains an `AGENTS.md`, do not replace the whole
file. Preserve user- or project-authored content and update only the managed block:

- `<!-- BEGIN AGENT-SYSTEM -->`
- `<!-- END AGENT-SYSTEM -->`

If those markers are absent, append the managed block near the end of the file.

## Resources

### scripts/

- `scripts/init_repo_agent_system.py`: deterministic initializer for the
  simplified repo-local agent system layout

### references/

- `references/structure.md`: explains the two-layer structure (`AGENTS.md` +
  `.agent-state/` + `.planning/`) and why `docs/agent-system/` was eliminated
