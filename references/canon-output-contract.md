# Canon Output Contract

Use this contract when a skill produces or updates durable context.

## Principle

```text
repo-local .agent-state / .planning / .research / .proposal = runtime execution buffers
/media/yhr/2T/Canon = durable cross-project memory graph
```

Do not delete local runtime scratchpads. Demote them from long-term source of truth and promote durable facts into Canon.

## Durable vs Runtime

Runtime buffers are allowed for in-progress execution:

- `.agent-state/conversations/<id>.md`
- `.planning/conversations/<id>/...`
- `.research/<conversation>/...`
- `.proposal/<conversation>/...`
- build logs, temporary reports, local state files

Durable facts belong in Canon when they should survive beyond the current conversation:

- project state
- task state and next step
- decisions and approvals
- incidents and fixes
- reusable patterns
- stable workflows
- artifact references
- cross-project relationships

## Canon Targets

Use these Canon page types:

```text
projects/      project source-of-truth pages
tasks/         durable work items that outlive a conversation
workflows/     stable multi-step processes
patterns/      reusable engineering patterns
decisions/     accepted or pending decisions
incidents/     failures, regressions, and resolved traps
artifacts/     artifact index entries with absolute paths
raw/update-cards/  ingest bridge from runtime input to durable graph
```

Schema and workflow references:

```text
/media/yhr/2T/Canon/SCHEMA.md
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

## Required Behavior

When a skill finishes meaningful work, ask:

1. Which Canon project page does this update?
2. Which Canon task does this update or create?
3. Which decision, pattern, workflow, or incident is supported?
4. Which artifact proves the result?
5. Which pages need backlinks?

If the answer is non-empty, create or update a Canon update card under:

```text
/media/yhr/2T/Canon/raw/update-cards/
```

Then merge stable facts into the relevant Canon pages when the durable target is clear.

## Artifact Policy

Canon references artifacts by absolute path by default.

Do not copy repo-local artifacts into Canon unless the user explicitly asks for a portable snapshot or bundle.

Use relation verbs from Canon schema:

```text
mentions, supports, updates, supersedes, depends_on, produces, consumed_by, blocks, resolved_by, related_to
```

## Failure Mode

If Canon is unavailable, keep the runtime output in the repo-local scratchpad and state clearly that Canon promotion was not done.
