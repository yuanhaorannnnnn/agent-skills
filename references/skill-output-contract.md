# Skill Output Contract

Shared contract for workflow skills that move work across phases, agents, repos, or external systems.

## Purpose

Workflow skills are not just instructions. They create state transitions. Every mode that changes code, external status, handoff files, or durable memory must make its contract explicit enough for the next agent to verify.

Use this contract together with:

```text
/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md
/home/yhr/.agents/repos/agent-skills/references/review-gate.md
/media/yhr/2T/Canon/SCHEMA.md
```

## Required Surfaces

For each mode or phase, define these surfaces:

| Surface | Required question |
|---------|-------------------|
| Input | What ID/path/branch/state file must exist before starting? |
| Output | What files, comments, links, build artifacts, or task pages must exist after completion? |
| State change | Which local state fields or external workflow statuses may be changed? |
| Gate file | Which file proves the phase is ready for the next phase? |
| Canon update | Which task/update-card/artifact refs must be written for durable state? |
| Review/verification | Which validation, Sentinel task, Traceback, or Review Gate result proves the work is safe to hand off? |

If a mode does not change state, say so. If a mode cannot update Canon, record the reason in the final response and keep repo-local artifacts as temporary evidence.

## Workflow Spine

Code-producing workflows should converge on this spine unless the skill explicitly opts out:

```text
Plan/Fix brief
  -> implementation
  -> local validation or Sentinel
  -> Review Gate
  -> Traceback when a design/fix plan exists
  -> Sanitize or workflow-specific closeout
```

`Repair Closeout` and `Tasking Turnover` are external handoff phases. They must not start new builds. They consume validation and review evidence produced earlier.

## Canon Task Fields

When a skill creates or updates a Canon task page, include these fields when known:

```yaml
title: <human task title>
type: task
status: active | done | blocked
project: <project slug>
source: manual | yunxiao | conversation | repo-scan
workflows: [<workflow-id>]
report_scope: work | infra | personal | ignore
weekly: true | false
artifacts: []
decisions: []
created: YYYY-MM-DD
updated: YYYY-MM-DD
```

For normal work reports, inclusion is strict:

```text
report_scope == work AND weekly == true
```

Infra tasks should use `report_scope: infra` and `weekly: false` unless the user explicitly wants an infra report.

## Review Gate Contract

When Review Gate applies, record the result in the Canon task page:

```text
Findings: blocker/non-blocker summary
Evidence: review command, reviewer/runtime, validation artifacts, Sentinel ids
Timeline: review_passed | review_blocked | review_skipped
```

Do not proceed to commit, Closeout, Turnover, or Sanitize when Review Gate is blocked unless the user explicitly waives the blocker.

## Handoff Rule

A downstream agent should be able to resume from only:

1. Canon task page
2. Gate file / state.json / goal.md / machine-readable plan (fix_plan.json or equivalent)
3. Linked artifacts by absolute path or URL

If that is not true, the workflow output is incomplete.

## Gotchas

- Do not treat runtime scratchpads (`.proposal`, `.planning`, `.agent-state`) as durable source of truth. They are execution buffers; Canon owns long-term state.
- Do not mutate external systems by display name when the API requires IDs. Resolve Yunxiao status/user IDs first.
- Do not claim a phase advanced unless its gate file and Canon evidence both reflect the transition.
- Do not run Review Gate after Sanitize/Closeout as a formality. It must run before irreversible handoff or commit.
