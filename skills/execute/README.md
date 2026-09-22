# execute

`execute` is the general entry point for carrying out a concrete task. It records a resumable Canon task and an explicit execution route, then leaves implementation and verification evidence for review.

## Choose a route

Start with the task and any applicable Canon task page:

```text
execute [--direct|--delegate] [--goal|--plan] [--executor MODEL] [<task-page-path>]
```

- `auto` (the default) chooses `direct` when the task is small, context-heavy, or hard to hand off; it chooses `delegate` only when the scope and acceptance checks can be transferred and the main agent can review the result.
- `--direct` keeps implementation and verification with the current agent.
- `--delegate` sends the execution contract to one downstream agent. Delegation depth is one; the downstream agent must not delegate again.
- `--goal` creates a persistent `goal.md`; `--plan` first records a Canon plan and also creates the goal. These are persistence options, independent of routing.

Execution itself does not imply a commit, push, branch change, deployment, message, or any other external state change. Those actions require their own explicit request and gates.

## What the flow records

Before implementation or delegation, resolve or create a Canon task and record a compact execution contract:

1. Goal, non-goals, scoped files, dirty baseline, success conditions, and validation commands.
2. A `## Routing` record with `routing_mode`, `resolved_route`, reason, owner, delegation depth, models, scope, status, and evidence.
3. Progress, artifacts, validation results, and the next recoverable step.

For `--goal` or `--plan`, the runtime brief and goal path are also recorded as artifacts. See the [task-resolution reference](../../references/canon-task-resolution.md) and [plan template](references/plan-template.md).

## Validate and hand off for review

Run the execution gate for the selected route and persistence mode. After code or configuration changes, use the [review gate](../../references/review-gate.md) to inspect the task page, current diff, and executed checks. Do not mark the task complete while a blocker remains.

The final handoff should identify the `task_path`, persistence mode, routing mode, resolved route, executor or delegation status, and validation evidence. The [output contract](../../references/skill-output-contract.md) and [Canon output contract](../../references/canon-output-contract.md) define the required shape.

## Boundaries with Yunxiao workflows

`execute` owns ordinary task execution and its Canon record. It does not own a Yunxiao demand or bug lifecycle:

- A demand ID stays under [`tasking`](../tasking/SKILL.md); its Engage phase may invoke `execute --plan`, while `tasking` retains state, identity, and phase ownership.
- A Yunxiao bug stays under [`repair`](../repair/SKILL.md); Repair Fix uses its own `fix_plan` and gates by default rather than routing through `execute`.

Use `execute` for implementation only when no more specific demand or bug orchestrator owns the task. Use read-only review, explanation, or research without `execute`.
