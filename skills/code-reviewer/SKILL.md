---
name: code-reviewer
description: |
  Use when the user asks for a code review, review of recent changes, diff
  review, PR-style review, bug-risk check, regression scan, or second-pass audit
  of modified code. Focus on correctness, regressions, security, and
  maintainability. This is the single shared review skill for both direct user
  reviews and review agents that need a consistent workflow.
---

# Code Reviewer

Run review as the single shared workflow for code review, with strict scope and
evidence-first findings.

## Responsibilities

- Review current changes using `git diff` and `git diff --cached`
- Read `.agent-state/MEMORY.md` if present for durable project constraints
- Pull only the minimum extra code needed to understand changed symbols
- Report findings by severity with file and line references
- Reuse the same workflow whether the review is triggered directly by a user or
  by a dedicated review agent

## Workflow

1. Read `.agent-state/MEMORY.md` if present.
2. Collect `git diff` and `git diff --cached`.
3. If both are empty, report that there are no uncommitted changes.
4. Review the changed lines first, then pull only the minimum adjacent code
   needed to understand changed symbols.
5. Evaluate against this checklist:
   - Correctness: does the changed logic match literal behavior, including null,
     empty, boundary, and side-effect cases?
   - Security: are external inputs validated and free of command/path/injection risk?
   - Maintainability: are names clear, duplication controlled, and project constraints respected?
   - Performance: does the change add avoidable repeated work or hot-loop cost?
6. Use `~/.agents/skills/.scripts/review_diff.py` when a structured starter report is useful.
7. If the change intent is unclear from code and local context, treat that
   ambiguity as a finding instead of guessing.

## Output

- Critical: clear correctness, security, or data-loss issue that should block landing
- Warnings: important risk, likely regression, or substantial maintainability concern
- Low Priority: smaller issue worth fixing but not a merge blocker
- Verified Correct: things you explicitly checked and found sound
- Summary: short overall assessment and residual risk
