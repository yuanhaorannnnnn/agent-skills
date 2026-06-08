# Repo Agent System Structure

Use this structure for repositories that want a repo-local agent runtime system, regardless of which coding agent runtime is attached to the repo.

This structure is intentionally not the durable source of truth. Canon is the durable cross-project memory graph:

```text
/media/yhr/2T/Canon
```

## Layers

### `AGENTS.md`

Repo-local entry index. Contains:

- Project-specific guidelines (build, style, testing, PR conventions)
- Managed **Repo Agent System** block between `<!-- BEGIN/END AGENT-SYSTEM -->`
- Pointers to Canon project/task pages when available

Keep repo-local rules close to the repo. Promote durable cross-project context to Canon.

### `.agent-state/`

Repo-local runtime state and scratch memory:

- `ACTIVE_CONVERSATION` — pointer to the current runtime conversation
- `conversations/<conversation>.md` — per-conversation resume buffers
- `MEMORY.md` — local notes and Canon links; not the durable source of truth
- `rules/mistakes.md` — local guardrails/incident scratchpad before durable incidents are promoted to Canon

### `.planning/`

Current-task runtime planning workspace:

```text
.planning/
└── conversations/
    └── <conversation-id>/
        ├── spec.md
        ├── task_plan.md
        ├── findings.md
        └── progress.md
```

When a task survives a conversation, promote its durable state to:

```text
/media/yhr/2T/Canon/tasks/<task>.md
```

### `.research/` and `.proposal/`

Research and proposal outputs may still be useful as repo-local artifacts. They are referenced from Canon by absolute path when durable.

## Design Principle

Keep runtime and durable roles separate:

- `AGENTS.md` = repo entry index and runtime conventions
- `.agent-state/` = runtime resume buffers and local scratch notes
- `.planning/` = current-task execution planning
- `.research/` / `.proposal/` = repo-local artifacts
- Canon = durable cross-project project/task/workflow/pattern/decision/incident/artifact graph

## Why Not Conversation Directories as Source of Truth?

Conversation directories answer where a chat happened. Canon answers what project, task, decision, artifact, workflow, pattern, or incident changed.

Use local directories for execution speed. Use Canon for long-term agent memory.

## Runtime-Neutral Principle

The repo structure should not assume one specific agent runtime. Runtime-specific entrypoints such as `~/.claude/skills`, `~/.codex/skills`, or `~/.agents/skills` stay outside the repo system design. The repository itself only defines the local index, planning workspace, and runtime state boundaries, while Canon links projects across runtimes.
