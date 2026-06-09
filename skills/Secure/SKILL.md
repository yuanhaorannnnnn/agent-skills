---
name: Secure
description: |
  Save current work progress to Canon task pages. Evaluates which task page
  to update (or create), writes a compact progress snapshot, and promotes
  durable facts to Canon projects/decisions/patterns/incidents when present.
  Trigger when user says "save conversation", "保存会话", "记住进度",
  "store context", finishes a session, or during workflow phase closeout.
  Covers both workflow-internal (Tasking/Repair phase side-effect) and
  workflow-external (ad-hoc discussion, research, non-workflow work).
---

# Canon Task Page Updater

Secure writes progress directly to Canon task pages. It replaces the old two-layer model (`.agent-state/conversations/<id>.md` + Canon promotion) with a single Canon-first write path.

Read the shared Canon contract:

```text
/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md
```

## Task Page Resolution

Resolve which task page to update. See the canonical implementation guide:

```text
/home/yhr/.agents/repos/agent-skills/references/canon-task-resolution.md
```

Priority order: demand_id/bug_id → explicit path → project+branch → semantic match → create new.

If the user provides an explicit task name or path, use it directly and skip resolution.

## Task Page Update

Write or update the Canon task page at `/media/yhr/2T/Canon/tasks/<task>.md`. A task page has these sections:

### YAML frontmatter (rewrite on every save)

```yaml
---
title: <task title>
type: task
status: active | blocked | done
project: <canon-project-slug>
source: yunxiao | user | branch | repo
workflows: []
artifacts:
  - /absolute/path/to/artifact
decisions:
  - <decision-slug>
created: YYYY-MM-DD
updated: YYYY-MM-DD
---
```

### Stable summary (rewrite every save)

- `## Goal` — one paragraph describing the end state
- `## Current State` — 1-3 sentences on where things stand now
- `## Next Step` — the single most important next action
- `## Key Decisions` — only decisions that still matter; link Canon decision pages

### Action layer (append/update)

- `## Tasks` — task-grouped checklists with status markers `[ ]` / `[x]`
- `## Plan` — only present when `--plan` was used; follows plan-template structure
- `## Findings` — research notes, code observations, open questions
- `## Progress` — chronological session log with timestamps
- `## Artifacts` — absolute path references to key deliverables
- `## Evidence` — links to Canon decisions/incidents/patterns/update-cards that support this task
- `## Timeline` — dated entry for each material state change (phase transitions, key commits)

**Merge, don't append.** Fold new information into existing summaries rather than adding raw recent context. The file should stay readable as a standalone document.

## Canon Promotion

After updating the task page, promote durable facts to other Canon page types when relevant:

- Project status or long-term constraints → update `/media/yhr/2T/Canon/projects/<project>.md`
- Accepted or pending decisions → update or create `decisions/<decision>.md`
- Reusable workflow or pattern → update `workflows/` or `patterns/`
- Failures, root causes, fixes → update or create `incidents/`
- Build outputs, proposals, reports → add absolute-path references to `artifacts/artifact-index.md`

If any durable target is updated, create a bridge update card:

```text
/media/yhr/2T/Canon/raw/update-cards/YYYYMMDD-<slug>.md
```

## Gate

写入后跑 gate——验证 task page 确实写进去了：

```bash
python3 ~/.claude/skills/Secure/scripts/write_gate.py --task <canon-task-path>
```
blocked → task page 缺失 / frontmatter 缺 status 或 updated / 缺 Goal/Current State/Next Step 节。

## Workflow Integration

Workflow skills call Secure as a phase-closeout side effect:

```
Tasking Orient   → task page created + § Goal/State written
Tasking Engage   → § Plan populated (via Execute --plan)
Tasking Turnover → § Status updated + § Progress appended
Repair Intake    → task page created + § Goal/State written
Repair Closeout  → § Status updated + § Progress appended
Sanitize         → § Progress appended + § Artifacts updated
```

For workflow-external work, the user calls Secure explicitly.

## Constraints

- **Do not duplicate artifact contents.** Reference absolute paths; summarize only the durable fact.
- **Merge, don't append.** Fold new information into existing sections.
- **Compress aggressively.** The task page should be readable in one scroll.
- **Canon by reference.** Do not copy repo-local artifacts into Canon unless explicitly asked.
- **If Canon is unavailable**, write a local fallback to `.agent-state/conversations/<slug>.md` and state that Canon promotion was not done.
- **Never delete old `.agent-state/conversations/` files.** They remain readable as historical runtime recaps.
- **`.planning/conversations/` is a runtime scratch buffer only.** Do not treat it as durable task state.
