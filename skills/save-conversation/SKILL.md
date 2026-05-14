---
name: save-conversation
description: |
  Save the current conversation context so it can be resumed later.
  Trigger when user says "save conversation", "保存会话", "记住进度",
  "store context", or finishes a session. Use whenever future resumption
  should be easy — independent of branch changes.
---

# Save Conversation

Write a conversation recap to `.agent-state/conversations/<conversation>.md`.

## Identity

Resolve the conversation id:
1. Explicit `--conversation <name>` (always create new conversations this way)
2. `.agent-state/ACTIVE_CONVERSATION`
3. `CODEX_THREAD_ID` (Codex runtime)
4. Current branch name (last resort)

Treat any text after the conversation name as `next_focus` — write it as `## Next Focus`.

## Structure

### Stable summary (rewrite every save)
- `Conversation Summary` — 1-3 sentences covering the whole conversation
- `Current Objective` — a single current target
- `Key Decisions` — only decisions that still matter
- `Constraints` — only active constraints
- `Open Questions` — only unresolved

### Action layer
- `Active Tasks` — task-grouped checklists. Simple tasks inline; complex tasks reference `.planning/conversations/<id>/<task>/`
- `Known Issues`
- `Key Context`

## Constraints

- **Do not duplicate.** If information already lives in `.planning/`, `AGENTS.md`, `.proposal/`, or `.research/`, reference the path — don't copy the content.
- **Merge, don't append.** When new information arrives, fold it into existing summaries instead of adding raw recent context.
- **Compress aggressively.** The file should fit in a single screen of context.
