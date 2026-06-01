---
name: Staging
description: |
  Create a durable planning workspace for complex, multi-step tasks.
  Use for tasks spanning 3+ sessions, architecture work, research, or
  anything needing cross-agent handoff. Prefer this over root-level
  task_plan.md files. Trigger on "plan this out", "create a workspace",
  "set up planning docs".
---

# Plan Workspace

Shape before you plan, plan before you build.

## Step 0: Shape

Before creating task_plan.md, answer three questions in a `shape.md`:

1. **What problem are we solving?** — Concrete and specific. Not "build auth system" but "users can't log in across devices, session tokens are device-bound."
2. **Why now?** — What makes this the right moment? What would break if we delayed?
3. **How do we know it's done?** — Observable, testable finish line. "User can log in from phone and laptop with the same account and see their data on both."

Keep shape.md short — three paragraphs max. If any answer is vague, ask the user before proceeding.

Then create three files under `.planning/conversations/<id>/`:

| File | Purpose |
|------|---------|
| `shape.md` | Three shaping questions: what problem, why now, how done. Answers before committing to a plan. |
| `task_plan.md` | Goal, architecture decisions, phases (3-7), errors. Read before every major decision. |
| `findings.md` | Research notes, code observations, external-source summaries. |
| `progress.md` | Session log, test results, handoff notes. Chronological. |

## Workflow

1. Resolve conversation id (explicit `--conversation` > ACTIVE_CONVERSATION > branch)
2. Initialize the 3 files from `templates/`
3. Fill `task_plan.md` before executing: Goal, Architecture, Phases, Validation
4. During execution: update findings after every 2 discoveries, progress after each action
5. Before major decisions: re-read `task_plan.md`

## Rules

- **Create plan first.** Never start a complex task without `task_plan.md`.
- **task_plan.md is the anchor.** All decisions and errors go there.
- **Never repeat failures.** Track what you tried in `progress.md`. Mutate approach.
