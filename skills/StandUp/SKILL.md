---
name: StandUp
status: deprecated
description: |
  DEPRECATED — AGENTS.md + CLAUDE.md initialization is now handled by
  repo conventions and Canon project pages. Runtime directory scaffolding
  (.agent-state/, .planning/) is no longer part of the standard agent
  bootstrap — these directories are created on-demand by skills that
  need them, not pre-initialized.
---

# DEPRECATED — Scaffold

StandUp has been deprecated. The repo-local agent runtime layout (AGENTS.md + CLAUDE.md + .agent-state/ + .planning/) is no longer pre-initialized:

- **AGENTS.md + CLAUDE.md**: maintained by repo conventions and the user. No skill pre-creates these.
- **.agent-state/ + .planning/**: created on-demand by skills that write to them (as runtime scratch buffers only, not durable state).
- **Canon project pages**: created manually or by Secure when a repo has durable cross-project relevance. See `/media/yhr/2T/Canon/SCHEMA.md`.

The `scripts/init_repo_agent_system.py` script and `references/structure.md` are kept for reference but are no longer maintained.

This file is kept for backward reference only. Do not trigger on this skill.
