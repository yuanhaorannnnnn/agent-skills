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

## Worktree

Use `<repo>/.worktrees/<safe-branch-name>` as the canonical worktree root.

`git worktree list` is source of truth. Claude Code must redirect `WorktreeCreate` / `WorktreeRemove` hooks to this root; Codex and other runtimes create worktrees there directly. Do not keep persistent worktrees under `.claude/worktrees/`.

Worktree branches are local scratch space — never push them to remote.
