---
name: Neutralize
description: |
  Use when the user asks to fix a bug, regression, failing behavior, broken
  feature, runtime error, or repeated mistake pattern. Especially use this when
  the user provides error logs, stack traces, console output, build failures,
  runtime exceptions, or screenshots of an error and wants the issue fixed, not
  just explained. Trigger on requests like "fix this", "debug this", "find the
  root cause", "here is the error log", "here is a screenshot", or "check for
  similar issues nearby". Focus on root cause, apply the fix, then scan for
  similar mistakes in nearby code.
---

# Fix Issue

Find the root cause, not just the symptom. Apply the smallest safe fix, then
scan nearby code for the same mistake pattern.

## Workflow

1. Extract evidence: exception type, file paths, line numbers, error text.
   For screenshots, read visible error text and identifiers first.
2. Reproduce the failure if practical.
3. Identify root cause.
4. Apply the minimum safe correction.
5. Verify by rerunning the relevant test or command.
6. Search adjacent files and similar call sites for the same error shape.
7. Summarize: what was fixed, what similar issues were checked, remaining risk.

## Output

- **Observed Error** — the relevant log line, screenshot clue, or failure symptom
- **Root Cause** — the specific cause in code or configuration
- **Fix Applied** — what was changed
- **Similar Issues Checked** — where you looked for the same error shape
- **Additional Similar Issues Found** — similar mistakes fixed or flagged
- **Validation** — what you reran
- **Remaining Risk** — anything still uncertain

## Rule Sources

- Canon `/media/yhr/2T/Canon/projects`, `patterns`, and `incidents` — durable cross-project constraints and known failure modes
- `.agent-state/MEMORY.md` — repo-local runtime/project constraints before changing behavior
- `.agent-state/rules/mistakes.md` — compatibility mirror for project-local mistake guardrails
- If the same mistake should be remembered, record it via `Codify` and promote durable lessons to Canon.


## Workflow Gate Contract

For bug fixes that produce code or durable lessons, follow the shared workflow output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

Small local fixes may stop at validation. Complex fixes, repeated mistake patterns, build failures, and cross-project lessons must promote evidence to Canon before handoff.

## Gotchas

- Do not patch from the symptom alone. If reproduction is impractical, record the strongest available evidence and the reason reproduction was skipped.
- Do not turn a bugfix into a broad refactor. Fix the minimum root cause first; adjacent cleanup is only allowed when it reduces the same failure pattern.
- Do not claim validation from a narrow command when the changed behavior requires a broader build/test. State the validation scope and remaining risk explicitly.
- If the same mistake appears in multiple places, either fix all confirmed instances or trigger `Codify`/Canon incident so the pattern is not lost.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- Ordinary small fixes do not need Canon updates.
- Complex root causes, repeated mistake patterns, build failures, and cross-project lessons should create/update `/media/yhr/2T/Canon/raw/update-cards/<date>-neutralize-<topic>.md`, `incidents/`, or `patterns/`.
- Validation logs, commits, screenshots, and local reports stay as artifact refs; do not copy them into Canon by default.
