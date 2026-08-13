# Global Agent Guidance

## Communication

Respond in Simplified Chinese. Keep technical terms, identifiers, commands, file paths, and code snippets in English.

When the user writes in English, correct only serious issues that make the meaning ambiguous, invert the intended meaning, misuse a critical technical term, or make the sentence unreadable. Ignore minor issues when the meaning is clear.

If correction is needed, append exactly one final line:
`> 💡 "your version" → "suggested version"`

## Compression

Drop filler, articles, pleasantries, and hedging. Use fragments, short synonyms, and arrows for causality. Technical terms, code, and file paths stay exact. Full sentences only for security warnings, irreversible actions, and design docs.

## Canon

Durable context at `/media/yhr/2T/Canon`. Query before acting — Canon overrides repo-local `.agent-state/`.

## Knowledge

Reference-only knowledge base at `/media/yhr/2T/files/wiki` — articles, concepts, paper notes, ingested media.

## Skill Paths

In skill instructions, `<skill-dir>` means the directory containing the loaded
`SKILL.md`; `<skills-root>` means its parent directory. Resolve these placeholders
from the actual loaded skill path. Do not replace them with runtime-specific
`~/.claude/skills` or `~/.agents/skills` assumptions.

## Skill Telemetry

When a skill materially passes, blocks, skips, or errors, emit one local event
using `<skills-root>/.scripts/skill_telemetry.py`. Record only skill/runtime/
trigger/outcome/duration and artifact or gate references. Never record prompts,
responses, transcript content, tool arguments, tokens, credentials, or arbitrary
error text. Telemetry failure is a warning and never changes the task outcome.

## Approvals and Guardian

- Run read-only inspection in the active sandbox first. Never pre-escalate `rg`, `sed -n`, `jq`, `wc`, `nl`, `find`, or ordinary file reads. Use `require_escalated` only after a concrete sandbox or network denial in the current turn, and cite that failure in the justification.
- Batch headless browser validation into one final pass per artifact revision, including all required viewports and screenshots. Re-run only after a concrete visual defect or a subsequent artifact change.
- Reduce Auto-review volume by fixing sandbox boundaries and narrow `writable_roots`. Never add broad command allow rules merely to suppress Guardian prompts.
- Guardian is scoped to the parent conversation. `/compact` does not reset it. For context rollover, start a fresh conversation and use passdown; do not resume or fork the old transcript.

## Worktree

Use `<repo>/.worktrees/<safe-branch-name>` as the canonical worktree root.

`git worktree list` is source of truth. Claude Code must redirect `WorktreeCreate` / `WorktreeRemove` hooks to this root; Codex and other runtimes create worktrees there directly. Do not keep persistent worktrees under `.claude/worktrees/`.

Worktree directories under `.worktrees/` are local scratch space — never push their branches to remote. Workflow-designated branches (e.g. `bugfix/*`, `feature/*`) created by repair/tasking may be pushed after gates pass.
