---
name: fix-issue
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

## Goal

Treat the provided error evidence as the starting point, fix the current issue
with the smallest safe change, then scan for similar patterns nearby.

## Inputs

Typical inputs include:

- error logs
- stack traces
- console output
- test failure output
- build failure output
- screenshots showing error text or obvious UI breakage
- a short user description of when the issue appears

When the input is a screenshot, extract the visible error text, labels, and
other debugging clues first. Do not treat the screenshot as decorative context.

## Workflow

1. Inspect the error evidence first.
   - For logs or stack traces: extract exception type, file paths, function
     names, line numbers, repeated keywords, and any reproducible trigger.
   - For screenshots: extract visible error text, status text, labels, broken
     UI states, and any code-like identifiers that can be searched.
2. Reproduce the failure when practical, or inspect the failure mode directly if
   reproduction is too expensive or the evidence is already sufficient.
3. Identify the root cause, not only the symptom.
4. Implement the minimum safe correction.
5. Verify the fix by rerunning the relevant test, command, or reproduction step
   whenever possible.
6. Search adjacent files and similar call sites for the same error shape.
   Good search anchors include:
   - the same API usage pattern
   - the same exception keyword
   - the same missing guard or assumption
   - the same configuration or path handling pattern
7. Summarize what was fixed, what similar issues were checked, what additional
   similar issues were found, and any remaining risk.

## Repo-Local Rule Sources

When this repository has a local agent-system layout, prefer these sources
before falling back to `.agent-state/*`:

- `AGENTS.md` for routing
- `.agent-state/MEMORY.md` for repo-level durable constraints
- `.agent-state/rules/mistakes.md` for reusable mistake guardrails

Treat `.agent-state/MEMORY.md` as the primary long-term rule source.

## Output

Prefer this structure:

- `Observed Error`: the relevant log line, screenshot clue, or failure symptom
- `Root Cause`: the specific cause in code or configuration
- `Fix Applied`: what was changed
- `Similar Issues Checked`: where you looked for the same error shape
- `Additional Similar Issues Found`: similar mistakes fixed or flagged
- `Validation`: what you reran or why full verification was not possible
- `Remaining Risk`: anything still uncertain

## Similar-Issue Scan

Do not stop after fixing the first occurrence. Use the current failure to build
search patterns and check for nearby repetitions.

Examples:

- If the bug is a null access, search for the same object being dereferenced in
  nearby files without guards.
- If the bug is a path-resolution failure, search for the same path-building
  pattern elsewhere.
- If the bug is caused by misuse of one API, search other call sites of that
  API in the same subsystem.

The goal is not a giant codebase-wide audit. The goal is a focused scan for the
same mistake shape in the most likely nearby locations.

## References

- Review `.agent-state/MEMORY.md` for project constraints before changing behavior.
- Review `.agent-state/rules/mistakes.md` for durable mistake guardrails.
- If the same mistake should be remembered, record the raw incident in `.agent-state/rules/mistakes.md`.
