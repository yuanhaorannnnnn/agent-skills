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

For each mode or phase that moves durable state or hands work to another agent, define these surfaces. A local direct edit completed and verified in the current conversation does not need a Canon task or gate file:

| Surface | Required question |
|---------|-------------------|
| Input | What ID/path/branch/state file must exist before starting? |
| Output | What files, comments, links, build artifacts, or task pages must exist after completion? |
| State change | Which local state fields or external workflow statuses may be changed? |
| Gate file | Which file proves the phase is ready for the next phase? |
| Canon update | Which task/update-card/artifact refs must be written for durable state? |
| Review/verification | Which validation, monitored validation task, traceback, or Review Gate result proves the work is safe to hand off? |

If a mode does not change durable state, say so. If durable work cannot update Canon, record the reason in the final response and keep repo-local artifacts as temporary evidence.

Commands inside a skill should resolve self-owned scripts through `<skill-dir>`
and sibling skills through `<skills-root>`. Absolute installed-runtime roots are
allowed only for external service configuration that cannot know the loaded
skill path.

## Workflow Spine

Code-producing workflows should converge on this spine unless the skill explicitly opts out:

```text
Plan/Fix brief
  -> implementation
  -> local or monitored validation
  -> Review Gate
  -> traceback when a design/fix plan exists
  -> sanitize or workflow-specific closeout
```

`repair Closeout` and `tasking Turnover` are external handoff phases. They must not start new builds. They consume validation and review evidence produced earlier.

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

When Review Gate applies to durable work, record the result in the Canon task page; local direct work reports it in the current response:

```text
Findings: blocker/non-blocker summary
Evidence: review command, reviewer/runtime, validation artifacts, validation task ids
Timeline: review_passed | review_blocked | review_skipped
```

Do not proceed to commit, Closeout, Turnover, or sanitize when Review Gate is blocked unless the user explicitly waives the blocker.

## Handoff Rule

A downstream agent should be able to resume durable or handed-off work from only:

1. Canon task page
2. Gate file / state.json / goal.md / machine-readable plan (fix_plan.json or equivalent)
3. Linked artifacts by absolute path or URL

If that is not true, the workflow output is incomplete.

## Telemetry

After a mode reaches its final local verdict, emit one event using the shared
contract in `references/skill-telemetry.md`. Use `trigger=workflow` when called by
another skill. Telemetry does not replace gate files or Canon evidence and must
not contain task content.

## Gotchas

- Do not treat runtime scratchpads (`.proposal`, `.planning`, `.agent-state`) as durable source of truth. They are execution buffers; Canon owns cross-project context. Project rules may instead define tracked documents (such as CARLA `Docs/`) as the project source of truth; preserve those documents and index decisions/artifact references in Canon.
- Do not mutate external systems by display name when the API requires IDs. Resolve Yunxiao status/user IDs first.
- Do not claim a phase advanced unless its gate file and Canon evidence both reflect the transition.
- Do not run Review Gate after sanitize/Closeout as a formality. It must run before irreversible handoff or commit.

## 钉钉文档交付终点

所有已授权的钉钉文档输出遵循 `/home/yhr/.agents/repos/agent-skills/references/dingtalk-delivery-routing.md`：先按实际协作范围选择“我的文档”或“OASIS仿真产品开发”知识库，再在目标内查找合适目录和已有文档。不是固定放个人空间，也不限两个业务目录。明确私有的周报草稿与只读同步保持原约束；路由本身不授权新增发送、通知或历史批量迁移。保留原有防重、人工内容和链接，逐份核验目标受众与权限。
