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
   Before restoring, treat the repo-local `AGENTS.md` as the authoritative
   rules for how this repository expects conversations to be interpreted.
2. Resolve the active conversation with this priority:
   - explicit conversation override if one was provided
   - `CODEX_THREAD_ID` when running inside Codex, so the same repo and directory can still restore different conversations correctly
   - `.agent-state/ACTIVE_CONVERSATION` if it exists
   - current branch name only as a last fallback when no conversation-scoped identifier exists
3. Run `~/.agents/skills/.scripts/restore_conversation.py` (canonical runtime path). Do not resolve relative to the repo being restored or invent `~/.claude/.scripts/...`.
4. Read `.agent-state/conversations/<conversation>.md` if present.
5. Read `.agent-state/MEMORY.md` if present.
   Read `.agent-state/MEMORY.md` as the repo-level durable memory source.
6. Read and surface the stable summary layer first when it exists. Treat it as the authoritative compressed recap of the whole conversation:
   - `Conversation Summary`
   - `Current Objective`
7. Read `.planning/conversations/<conversation>/` if it exists. Note which tasks have dedicated planning workspaces so they can be surfaced during restore.
8. Choose the "next focus" from the action layer with this priority:
   - First incomplete item under `Active Tasks` (or `Pending Follow-Ups` if using the legacy flat format)
   - Then `Known Issues`
   - Then `Key Context`
   - Then `Current Objective`
   When `Active Tasks` uses task-grouped checklists, surface the heading of the task with the first incomplete item, plus a count of total open items.
9. Return a short confirmation with:
   - the restored conversation file path
   - memory file path
   - the stable summary fields that exist
   - the most important next focus (with task name if grouped)
   - `Key Context` when it exists
   - **planning workspace status**: list task names that have `.planning/conversations/<conversation>/<task>/` directories, so the user knows where to dig deeper
   Branch may be reported as auxiliary metadata, but it should not drive conversation identity when a conversation-scoped identifier exists.

## Script

Use `~/.agents/skills/.scripts/restore_conversation.py` (canonical runtime path) for deterministic lookup and summary. The script should surface enough context that the user can resume immediately without having to open the conversation file first.

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
