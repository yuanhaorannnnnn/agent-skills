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

- `.agent-state/MEMORY.md` — project constraints before changing behavior
- `.agent-state/rules/mistakes.md` — durable mistake guardrails
- If the same mistake should be remembered, record it via `capture-mistake-rule`.
