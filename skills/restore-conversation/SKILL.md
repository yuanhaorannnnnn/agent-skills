---
name: restore-conversation
description: |
  Use when the user wants to restore a previous conversation, recover context
  after a reset or clear, resume work from saved notes, or find the next step
  from prior progress. Trigger on requests like "restore conversation", "recover
  context", "resume where we left off", or "load the saved recap". Use this
  whenever the user wants to pick work back up from saved conversation state,
  even if they only say "what were we doing" or "tell me the next step".
---

# Restore Conversation

## Workflow

1. Determine the current repository root and current branch.
   Before restoring, treat the repo-local `AGENTS.md` and
   `docs/agent-system/conversation-rules.md` as the authoritative rules for how
   this repository expects conversations to be interpreted.
2. Resolve the active conversation with this priority:
   - explicit conversation override if one was provided
   - `CODEX_THREAD_ID` when running inside Codex, so the same repo and directory can still restore different conversations correctly
   - `.agent-state/ACTIVE_CONVERSATION` if it exists
   - current branch name only as a last fallback when no conversation-scoped identifier exists
3. Run `../.scripts/restore_conversation.py`, resolving that relative path from this skill directory rather than from the repo being restored.
4. Read `.agent-state/conversations/<conversation>.md` if present.
5. Read `.agent-state/MEMORY.md` if present.
   If `docs/agent-system/project-memory.md` exists, read it as the preferred
   repo-level durable memory source. Treat `.agent-state/MEMORY.md` as runtime
   compatibility state.
6. Read and surface the stable summary layer first when it exists. Treat it as the authoritative compressed recap of the whole conversation:
   - `Conversation Summary`
   - `Current Objective`
7. Choose the "next focus" from the action layer with this priority: `Pending Follow-Ups`, then `Known Issues`, then `Key Context`, then `Current Objective`.
8. Return a short confirmation with the restored conversation file, memory file, the stable summary fields that exist, the most important next focus, and `Key Context` when it exists. Branch may be reported as auxiliary metadata, but it should not drive conversation identity when a conversation-scoped identifier exists.

## Script

Use `../.scripts/restore_conversation.py` for deterministic lookup and summary. The script should surface enough context that the user can resume immediately without having to open the conversation file first.

## Recommended Explicit Naming

When you deliberately manage conversations with human-readable names, restore
using the same explicit name instead of depending on whatever runtime thread id
is currently available.

Recommended format:

- `/restore --conversation <name>`

Matching save format:

- `/save --conversation <name>`

Examples:

- `/save --conversation suspension-tuning-v1`
- `/restore --conversation suspension-tuning-v1`

Rule:

- if you manually choose a conversation name once, keep using that same name for all
  later saves and restores of the same conversation
