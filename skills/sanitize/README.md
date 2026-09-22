# Sanitize

Sanitize is the completion workflow for work that is already implemented and
has evidence. It has two distinct modes:

- **Report mode** produces an evidence-backed Markdown report for a completed
  task. It covers the abstract, alternatives, method, implementation,
  evaluation, and conclusion. It does not commit, push, or mark work complete.
- **Closeout mode** scopes the finished work, runs the applicable review and
  verification gates, and publishes it with Git and Canon updates.

## Generic flow

1. Resolve the task and its intended artifact/file scope.
2. Gather direct evidence: implementation changes, tests, builds, runtime
   checks, commits, and existing reports or logs. Label anything not verified.
3. Choose the requested mode. For a formal report, follow the
   [report contract](references/formal-report.md) and run
   [`report_gate.py`](scripts/report_gate.py).
4. For closeout, review the scoped diff, keep unrelated changes out, and
   confirm the required validation has passed.
5. Update the relevant Canon task page with progress, evidence, artifacts, and
   remaining work. Durable decisions or reusable results may also need an
   update card, as described by the [Canon output contract](../../references/canon-output-contract.md).
6. Only after the requested authority is present, complete the final delivery
   and report the exact files, evidence, and remaining gaps.

## Authority boundary

Preparing a report or checking a diff does not authorize external publication.
`git commit` and `git push` happen only when the user explicitly requests
closeout or publication. Report mode never performs those mutations. Do not
claim a task is complete when validation, Git publication, or Canon recording
is still missing.

For the full routing rules, safeguards, and edge cases, see
[`SKILL.md`](SKILL.md).
