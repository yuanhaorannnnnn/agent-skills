# Conversation Recap - global-agent-guidance

## Conversation Summary
- Refined the shared global AGENTS.md guidance stored in agent-skills for use across Pi, Claude Code, and Codex.
- Converted the old detailed rulebook into compact baseline preferences focused on durable do/dont guidance rather than task procedures.

## Current Objective
- Global prompt simplification is complete and committed.

## Key Decisions
- AGENTS.md is the canonical shared guidance source; Claude Code compatibility should use a thin CLAUDE.md with @AGENTS.md instead of duplicated guidance.
- Global guidance should not contain project-specific setup, commands, architecture, or temporary task state.
- Keep user-specific rules: Simplified Chinese responses, English technical terms preserved, serious-only English expression feedback, local HTML artifact catalog, ASCII diagram constraints, DESIGN.md token priority, and narrow local session access.

## Constraints
- Keep global prompt runtime-neutral across Pi, Claude Code, and Codex.
- Keep mechanics in skills/scripts and project-specific rules near the target project.
- Do not commit unrelated existing changes in agent-skills worktree.

## Open Questions
- None.

## Active Tasks
- [x] Simplify global AGENTS.md into durable baseline guidance.
- [x] Preserve important original rules while removing detailed how-to flow.
- [x] Commit and push the AGENTS.md update.

## Known Issues
- save_conversation.py created an empty recap initially; this file was manually rewritten with the actual task summary.
- The worktree still has unrelated pre-existing modifications outside AGENTS.md.

## Key Context
- Commit: e8a412a (docs(global): simplify shared agent guidance)
- Branch: main
- Changed file committed: AGENTS.md
- Planning docs were not present, so no .planning update was made.
