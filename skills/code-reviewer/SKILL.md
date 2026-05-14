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

Review `git diff` and `git diff --cached`. Pull only the minimum extra code
needed to understand changed symbols. Report findings by severity with file
and line references.

## Checklist

- **Correctness**: does changed logic handle null, empty, boundary, and side-effect cases?
- **Security**: are external inputs validated, free of injection/command/path risks?
- **Maintainability**: are names clear, duplication controlled, project constraints respected?
- **Performance**: does the change add avoidable repeated work or hot-loop cost?

## Output

- **Critical** — correctness, security, or data-loss issue that should block landing
- **Warnings** — important risk, likely regression, or substantial maintainability concern
- **Low Priority** — smaller issue worth fixing but not a merge blocker
- **Verified Correct** — things you explicitly checked and found sound
- **Summary** — short overall assessment and residual risk

If change intent is unclear from code and local context, treat that ambiguity
as a finding instead of guessing.
