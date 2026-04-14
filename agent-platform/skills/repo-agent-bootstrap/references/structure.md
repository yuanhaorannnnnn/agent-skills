# Repo Agent System Structure

Use this structure for repositories that want a repo-local agent workflow
system, regardless of which coding agent runtime is attached to the repo.

## Layers

### `AGENTS.md`

Repo-local entry index. Contains:
- Project-specific guidelines (build, style, testing, PR conventions)
- **Guardrails** section — inlined durable constraints (no separate file needed)
- **Repo Agent System** block (managed, between `<!-- BEGIN/END AGENT-SYSTEM -->`)
  - Conversation save/restore rules
  - Planning conventions
  - Source Of Truth Map

Keep rules inlined here rather than routing to a separate `docs/agent-system/`
directory. This reduces indirection without sacrificing completeness.

### `.agent-state/`

All runtime and durable state in one place:

- `MEMORY.md` — durable repo knowledge, architecture notes, workflow constraints
- `rules/mistakes.md` — guardrails in ❌/✅ incident format (raw + durable, unified)
- `ACTIVE_CONVERSATION` — pointer to the current conversation
- `conversations/<conversation>.md` — per-conversation recap files

### `.planning/`

Current-task planning workspace. Default target layout:

```text
.planning/
└── conversations/
    └── <conversation-id>/
        ├── spec.md
        ├── task_plan.md
        ├── findings.md
        └── progress.md
```

## Design Principle

Keep roles distinct, but keep the layer count minimal:

- `AGENTS.md` = index + inlined rules (no separate docs layer)
- `.agent-state/` = all durable and runtime state
- `.planning/` = current-task planning files

## Why Not `docs/agent-system/`?

An earlier version of this structure used a `docs/agent-system/` directory with
four topic files (`conversation-rules.md`, `project-memory.md`,
`mistake-patterns.md`, `planning-rules.md`). This was eliminated because:

1. The content was short enough to inline directly into `AGENTS.md` and
   `.agent-state/MEMORY.md` without loss of clarity.
2. Two files with overlapping "durable knowledge" roles (`project-memory.md`
   and `MEMORY.md`) created ambiguity about which was authoritative.
3. Fewer files means fewer places to look and fewer sync issues.

## Runtime-Neutral Principle

The repo structure should not assume one specific agent runtime. Keep runtime-
specific entrypoints such as `~/.claude/skills` or `~/.agents/skills` outside
the repo system design. The repository itself only defines the local index,
planning workspace, and runtime state boundaries.
