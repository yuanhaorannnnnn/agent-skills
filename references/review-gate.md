# Review Gate

Shared quality gate for code-producing workflows. Use it after implementation and local validation, before handoff, closeout, or commit.

Read with the workflow output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

## When To Run

Run Review Gate when a workflow has produced code or a technical artifact that will be delivered:

- `Repair Fix`: after fix + monitored/local validation, before Closeout.
- `Tasking Engage`: after implementation, before Traceback/Sanitize.
- `Execute`: after the goal is implemented, before Traceback/Sanitize.
- `Sanitize`: before commit/push, unless an equivalent review gate already passed for the same diff.

For proposal/report-only work, use a lighter review focused on assumptions, evidence, and missing risks.

## Workflow Position

Review Gate sits after implementation and local validation, before irreversible handoff:

```text
Plan/Fix brief -> implementation -> validation/monitoring -> Review Gate -> Traceback when applicable -> Sanitize/Closeout/Turnover
```

- `Execute` and `Tasking Engage`: Review Gate runs before Traceback/Sanitize.
- `Repair Fix`: Review Gate runs before commit/push and before Closeout.
- `Sanitize`: consumes prior Review Gate evidence or runs the gate before commit/push.
- `Closeout`/`Turnover`: do not run new builds; they consume prior validation and Review Gate evidence.

If no design doc, fix plan, acceptance checklist, or public contract exists, Traceback may be skipped, but the skip reason must be recorded in Canon.

## Inputs

Collect only the evidence needed for review:

- Canon task page path.
- Current branch and base branch.
- `git diff --stat` and focused diff for changed files.
- Relevant design/fix plan/test evidence paths.
- monitored or local validation summary, when present.

Do not paste large logs or full files. Link artifacts by absolute path.

## Reviewer Selection

Use Codex review as the default gate.

1. **Non-Codex runtimes** (Claude Code, Pi): use the runtime's `/codex` slash commands:
   - `/codex:review` for normal code review.
   - `/codex:adversarial-review` when the change touches shared contracts, build systems, status transitions, data formats, public APIs, external side effects, or production handoff.
2. **Codex runtime**: use `/review` or code-review stance when slash review is available.
3. **Fallback only**: if the runtime cannot invoke Codex review or the command fails, perform local adversarial review and record the fallback reason. Do not claim Codex reviewed the change.

For Claude Code and Pi, review invocation evidence should look the same: a `/codex:review` or `/codex:adversarial-review` command plus the resulting Codex review output.

## Blocker Rules

Default blocking policy:

- Any P1 finding → BLOCK.
- Three or more P2 findings → BLOCK.
- No P1 and P2 count ≤ 2 → PASS; record findings as follow-ups.
- Diff < 20 changed lines and no new files → SKIP, unless the change touches status transitions, build scripts, security/data handling, public APIs, external side effects, or workflow gates.

Severity definitions:

- P1: correctness break, data loss, security issue, build/test failure, broken workflow state, wrong external status mutation, destructive operation risk, or behavior that blocks delivery.
- P2: likely regression, missing validation, ambiguous ownership, brittle logic, incomplete evidence, maintainability risk, or nearby-contract risk that should be fixed soon.
- P3: style, naming, cleanup, docs polish, or optional improvement.

Examples that block regardless of size:

- Yunxiao/DingTalk status or owner mutation.
- Build, packaging, deploy, or monitor command changes.
- Public API, schema, protocol, state machine, or permission changes.
- File deletion, overwrite, migration, or irreversible side effects.

Non-blocking findings can be recorded as follow-ups if they do not affect the current delivery.

## Canon Output

Write review results to the task page:

- `## Findings`: concise findings and disposition.
- `## Evidence`: review runtime, exact command (`/codex:review`, `/codex:adversarial-review`, or `/review`), result/job id or summary, linked update card, validation evidence. If fallback was used, record `Codex review: not used` and the reason.
- `## Timeline`: material state change such as `review_passed`, `review_blocked`, or `review_skipped`.

If the review blocks delivery, do not proceed to Sanitize, Closeout, or Turnover until blockers are fixed or explicitly waived by the user.
