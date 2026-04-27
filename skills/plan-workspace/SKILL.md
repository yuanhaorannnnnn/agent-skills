---
name: plan-workspace
description: |
  Use when a task needs a durable, conversation-scoped planning workspace:
  creating or resuming `.planning/conversations/<conversation-id>/`, organizing
  multi-step work, writing an ExecPlan, tracking phases, findings, progress, and
  handoff state across Codex, Claude Code, Kimi Code, or other coding agents.
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

## Core Model

Keep the sources of truth separate:

```text
.agent-state/conversations/<id>.md
  Cross-agent resume summary: current objective, next focus, key context.

.planning/conversations/<id>/exec_plan.md
  Authoritative plan for complex work. It should be self-contained enough for a
  fresh agent to continue the task.

.planning/conversations/<id>/task_plan.md
  Execution index: current phase, phase statuses, and links to the main plan.

.planning/conversations/<id>/findings.md
  Evidence, research notes, code observations, external-document summaries.

.planning/conversations/<id>/progress.md
  Session log, commands run, tests, errors, and handoff notes.
```

`exec_plan.md` is the main plan. `task_plan.md` is not a second plan; keep it as
a compact phase index so it can be safely re-read often.

## Workflow

1. Resolve the conversation id:
   - explicit `--conversation <id>` when provided
   - `.agent-state/ACTIVE_CONVERSATION`
   - `CODEX_THREAD_ID`
   - current branch name as a last fallback
2. Initialize the planning workspace with:
   - `spec.md`
   - `exec_plan.md`
   - `task_plan.md`
   - `findings.md`
   - `progress.md`
3. Before execution, fill in `spec.md` and `exec_plan.md` for complex tasks.
4. During execution, update:
   - `task_plan.md` when phase status changes
   - `findings.md` after discoveries or external-source reads
   - `progress.md` after material actions, tests, errors, or handoff points
5. Before major decisions, re-read `exec_plan.md` and `findings.md`.

## Commands

Use the shared scripts through the runtime `.scripts` link:

```bash
python ~/.agents/skills/.scripts/init_planning_files.py --project-dir . --conversation infra
python ~/.agents/skills/.scripts/planning_status.py --project-dir . --conversation infra
```

The scripts are deterministic helpers. The agent is still responsible for
writing the actual plan content and keeping files current.

## Update Discipline

- Write external/web/search content to `findings.md`, not `task_plan.md`.
- Keep `task_plan.md` short enough to be injected or skimmed frequently.
- Update `exec_plan.md` only when intent, architecture, milestones, or validation
  strategy changes.
- Log failed attempts in `progress.md` before trying a materially different
  approach.
- Do not create root-level `task_plan.md`, `findings.md`, or `progress.md` for
  this repo-local workflow.
