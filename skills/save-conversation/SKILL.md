---
name: save-conversation
description: |
  Use when the user wants to save the current conversation, persist working
  context, store progress, or write next steps so the same conversation can be
  resumed later. Trigger on requests like "save conversation", "save where we
  are", "store context", "write recap", or "remember where we left off". Use
  this whenever future resumption should be easy, especially when the user wants
  a stable conversation identity that is independent of branch changes.
---

# Save Conversation

## Workflow

1. Determine the current repository root. Branch can be recorded elsewhere if useful, but it is not the primary identity of a saved conversation.
   Before updating the conversation file, treat the repo-local `AGENTS.md` and
   `docs/agent-system/conversation-rules.md` as the authoritative rules for how
   this repository wants conversation state organized.
2. Resolve the active conversation document with this priority:
   - explicit conversation override if one was provided
   - when the current save should create a new independent conversation in a repo, ALWAYS pass `--conversation <name>` explicitly instead of relying on `.agent-state/ACTIVE_CONVERSATION` fallback
   - `.agent-state/ACTIVE_CONVERSATION` if it already exists
   - `CODEX_THREAD_ID` when running inside Codex, so different conversations in the same repo and directory do not overwrite each other
   - current branch name only as a last fallback when no conversation-scoped identifier exists
3. Read any existing `.agent-state/conversations/<conversation>.md`.
4. Run `../../.scripts/save_conversation.py` to refresh the conversation file. Resolve that relative path from this skill directory, not from the repo being saved.
5. Re-open the resulting conversation file and verify it stays focused on conversation context rather than git state.
6. Re-read and rewrite the stable summary layer on every save. Do not just preserve it blindly. Compress the whole conversation into concise, deduplicated statements so the file reflects the current best understanding rather than only the latest turns. Keep these sections short and durable:
   - `Conversation Summary`
   - `Current Objective`
   - `Key Decisions`
   - `Constraints`
   - `Open Questions`
   Preferred style:
   - `Conversation Summary`: 1-3 sentences covering the whole conversation, not just the latest step
   - `Current Objective`: a single current target
   - `Key Decisions`: only decisions that still matter
   - `Constraints`: only active constraints
   - `Open Questions`: only unresolved questions
   When new information appears, merge it into these summaries instead of appending raw recent context.
7. Update the action layer on every save so the next restore can resume immediately:
   - `Pending Follow-Ups`
   - `Known Issues`
   - `Key Context`
   Preserve useful existing notes; if there is nothing specific to add, leave `- None` rather than deleting the sections.
8. Write the updated conversation recap back to `.agent-state/conversations/<conversation>.md`. Do not switch conversation files just because the git branch changed inside the same conversation.

## Script

Use `../../.scripts/save_conversation.py` for deterministic conversation-file selection and persistence. The skill should keep the saved file centered on actionable conversation context for a future restore.

## Recommended Explicit Naming

When you want a stable human-readable conversation name that matches your renamed
thread, prefer explicit naming instead of depending on runtime thread ids.

Recommended format:

- `/save --conversation <name>`

Examples:

- `/save --conversation suspension-tuning-v1`
- `/save --conversation steer-comparison-pass-2`

Naming rules:

- use short, stable names
- prefer lowercase words with hyphens
- keep using the exact same name for later saves and restores of the same
  conversation
- treat the explicit conversation name as the source of truth for manual naming

## State Files

- `AGENTS.md`
- `docs/agent-system/conversation-rules.md`
- `docs/agent-system/project-memory.md`
- `.agent-state/MEMORY.md`
- `.agent-state/ACTIVE_CONVERSATION`
- `.agent-state/conversations/<conversation>.md`
- `.agent-state/rules/mistakes.md`

## Resume Context

Keep these stable summary sections in every saved conversation file:

- `## Conversation Summary`
- `## Current Objective`
- `## Key Decisions`
- `## Constraints`
- `## Open Questions`

Keep these action sections in every saved conversation file:

- `## Pending Follow-Ups`
- `## Known Issues`
- `## Key Context`

The summary layer should represent the whole conversation in compressed form. It must be intentionally rewritten so it does not drift into "recent chat only". The action layer should change often and represent the immediate resume point.

When repo-local topic docs exist, prefer them as the long-term system of record.
Treat `.agent-state/*` as runtime/conversation state and compatibility storage, not
as the only durable rule source.
