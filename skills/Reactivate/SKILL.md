---
name: Reactivate
description: |
  Resume work from a saved conversation. Use when the user wants to
  restore a previous session, recover context after /clear, pick up
  where they left off, or find the next step. Trigger on "restore
  conversation", "恢复现场", "接着上次继续", "what were we doing".
---

# Restore Conversation

Read `.agent-state/conversations/<conversation>.md` and surface the current state.

## Identity (same priority as save-conversation)

1. Explicit `--conversation <name>`
2. `.agent-state/ACTIVE_CONVERSATION`
3. Branch name (last resort)

## What to surface

- **`Conversation Summary`** and **`Current Objective`** — the authoritative compressed recap
- **First incomplete item** under `Active Tasks` — this is the next focus
- **`Next Focus`** if present (set during save)
- **`Key Context`** — file paths, repo info, runtime notes
- **`Known Issues`** — anything to watch for

## What not to do

- Don't restore git state snapshots — only conversation context
- Don't switch conversation files because the branch changed
