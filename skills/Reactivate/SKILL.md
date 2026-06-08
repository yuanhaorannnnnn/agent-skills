---
name: Reactivate
description: |
  Resume work from a Canon task page and reconnect it to the current repo
  context. Use when the user wants to restore a previous session, recover
  context after /clear, pick up where they left off, or find the next step.
  Trigger on "restore conversation", "恢复现场", "接着上次继续",
  "what were we doing".
---

# Resume from Canon Task Page

Reactivate reads the durable Canon task page first, then uses Passdown to attach hot runtime context from the most recent agent session.

Read the shared Canon contract:

```text
/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md
```

## Task Resolution

Resolve which task to restore. See the canonical implementation guide:

```text
/home/yhr/.agents/repos/agent-skills/references/canon-task-resolution.md
```

Priority: explicit path → demand_id/bug_id → project+branch → semantic match → recent tasks.

If no task page resolves, report available task pages and ask the user to choose or create one.

## Restore Flow

### Step 1: Read the Canon task page

Open `/media/yhr/2T/Canon/tasks/<task>.md` and surface:

- `## Current State` — where things stand
- `## Next Step` — the most important next action
- `## Tasks` — first incomplete item
- `## Key Decisions` — active decisions
- `## Artifacts` — key deliverable paths
- `## Plan` — active phase and status (if present)

### Step 2: Attach hot runtime context via Passdown

Invoke the Passdown skill to find the most recent agent session for this repo/task. Passdown auto-detects the source runtime from available session JSONL files — do not hardcode a specific runtime. Use `--focus` with the task title from the Canon task page.

### Step 3: Reconnect to Canon

1. Identify the current repo path.
2. Open `/media/yhr/2T/Canon/index.md` and the matching `projects/<project>.md` page.
3. Follow linked active tasks, workflows, patterns, decisions, incidents as needed.
4. If the task page references artifacts that don't exist on disk, report the gap.

## Output Format

```markdown
## 恢复现场 — <task-title>

**Task page**: `/media/yhr/2T/Canon/tasks/<task>.md`
**Status**: <status>
**Project**: <project>

### Current State
<from task page § Current State>

### Next Step
<from task page § Next Step>

### Active Tasks
- [ ] <first incomplete task>
- Remaining: <N> open items

### Recent Context (Passdown)
<hot context summary from recent agent session>

### Artifacts
- <absolute path references>
```

## What Not To Do

- Do not restore git state snapshots — only context.
- Do not read `.agent-state/conversations/` or `.planning/conversations/` for task identity — Canon task page is the source of truth.
- Do not treat runtime recap files as durable state when a Canon task page exists.
- Do not copy artifacts into Canon; reference absolute paths.
- Do not silently override the task page; report conflicts between Canon and runtime state.
