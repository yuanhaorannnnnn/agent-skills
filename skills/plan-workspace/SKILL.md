---
name: plan-workspace
description: |
  Use when a task needs a durable, conversation-scoped planning workspace:
  creating or resuming `.planning/conversations/<conversation-id>/`, organizing
  multi-step work, tracking phases, findings, progress, and handoff state
  across Codex, Claude Code, Kimi Code, or other coding agents.
  Trigger this for complex implementation, architecture, research, or cross-agent
  work; prefer it over root-level task_plan.md files.
---

# Plan Workspace

Create and maintain repo-local planning files under:

```text
.planning/conversations/<conversation-id>/
```

Use this skill when the user asks to plan, start, organize, resume, or track a
multi-step task. It adapts file-based planning to the repo-local conversation
system without depending on agent-specific slash commands.

## Core Model: 3 Documents

```text
.agent-state/conversations/<id>.md
  Cross-agent resume summary: current objective, next focus, key context.

.planning/conversations/<id>/task_plan.md
  The single source of truth for the task. Contains goal, architecture,
  phases, decisions, and errors. This is the primary file to re-read before
  making decisions.

.planning/conversations/<id>/findings.md
  Evidence, research notes, code observations, external-document summaries.
  Write anything discovered from outside the codebase here.

.planning/conversations/<id>/progress.md
  Session log, commands run, tests, errors, and handoff notes.
  Chronological record of what was done.
```

`task_plan.md` is the main plan. Keep it self-contained enough that a fresh
agent can continue the task. Re-read it before major decisions.

## Workflow

1. Resolve the conversation id:
   - explicit `--conversation <id>` when provided
   - `.agent-state/ACTIVE_CONVERSATION`
   - `CODEX_THREAD_ID`
   - current branch name as a last fallback
2. Initialize the planning workspace with:
   - `task_plan.md`
   - `findings.md`
   - `progress.md`
3. Before execution, fill in `task_plan.md` with:
   - Goal (what we're trying to achieve)
   - Architecture / Decisions (how we'll approach it)
   - Phases (broken into 3-7 logical steps)
   - Validation strategy (how we'll know it's done)
4. During execution, update:
   - `task_plan.md` when phase status or decisions change
   - `findings.md` after discoveries or external-source reads
   - `progress.md` after material actions, tests, errors, or handoff points
5. Before major decisions, re-read `task_plan.md` and `findings.md`.

## File Purposes

| File | Purpose | When to Update |
|------|---------|----------------|
| `task_plan.md` | Goal, architecture, phases, decisions, errors | After each phase or decision |
| `findings.md` | Research, discoveries, external sources | After ANY discovery |
| `progress.md` | Session log, test results, commands | Throughout session |

## Critical Rules

### 1. Create Plan First
Never start a complex task without `task_plan.md`. Fill in Goal, Architecture,
and Phases before executing.

### 2. task_plan.md Is the Anchor
Before major decisions, re-read `task_plan.md`. It keeps goals and architecture
in your attention window. All decisions and errors belong here.

### 3. The 2-Action Rule
> "After every 2 view/browser/search operations, IMMEDIATELY save key findings
to `findings.md`."

This prevents visual/multimodal information from being lost.

### 4. Update After Act
After completing any phase:
- Mark phase status: `pending` -> `in_progress` -> `complete`
- Log any errors encountered in `task_plan.md`
- Note files created/modified in `progress.md`

### 5. Log ALL Errors
Every error goes in `task_plan.md`. This builds knowledge and prevents
repetition.

```markdown
## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
```

### 6. Never Repeat Failures
```
if action_failed:
    next_action != same_action
```
Track what you tried in `progress.md`. Mutate the approach.

## Update Discipline

- Write external/web/search content to `findings.md`, not `task_plan.md`.
- Keep `task_plan.md` self-contained: a fresh agent should be able to continue
  from this file alone.
- Log failed attempts in `progress.md` before trying a materially different
  approach.
- Do not create root-level `task_plan.md`, `findings.md`, or `progress.md` for
  this repo-local workflow.

## Read vs Write Decision Matrix

| Situation | Action | Reason |
|-----------|--------|--------|
| Just wrote a file | DON'T read | Content still in context |
| Viewed image/PDF | Write findings NOW | Multimodal -> text before lost |
| Browser returned data | Write to findings.md | Screenshots don't persist |
| Starting new phase | Read task_plan.md | Re-orient if context stale |
| Error occurred | Read task_plan.md | Need current state to fix |
| Resuming after gap | Read all planning files | Recover state |

## Templates

Copy these templates to start:

- [templates/task_plan.md](templates/task_plan.md) - Main plan: goal, architecture, phases, decisions
- [templates/findings.md](templates/findings.md) - Research and discoveries
- [templates/progress.md](templates/progress.md) - Session logging
