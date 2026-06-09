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
7. Write gate evidence file — `rerun_command`, `rerun_exit_code`, `adjacent_searches`, `adjacent_findings`, `remaining_risk` → `.agent-state/neutralize-gate.json`.
8. Run gate:
   ```bash
   python3 ~/.claude/skills/Neutralize/scripts/verify_fix_gate.py
   ```
   blocked → 补证据后重跑。pass → 继续总结。

## Output

Human-readable summary:
- **Observed Error** / **Root Cause** / **Fix Applied**
- **Similar Issues Checked** / **Additional Similar Issues Found**
- **Validation** / **Remaining Risk**

Machine-readable evidence (`.agent-state/neutralize-gate.json`):
```json
{
  "rerun_command": "pytest tests/test_foo.py -v",
  "rerun_exit_code": 0,
  "rerun_output_sample": "...",
  "adjacent_searches": ["rg 'same_pattern' src/", "rg 'similar_call' lib/"],
  "adjacent_findings": ["src/bar.py:42 same pattern"],
  "remaining_risk": "only checked Python side; C++ callers not scanned"
}
```

## Rule Sources

- Canon `/media/yhr/2T/Canon/incidents` and `patterns` — primary source for known failure modes and reusable fixes. Query first.
- `.agent-state/MEMORY.md` and `.agent-state/rules/mistakes.md` — compatibility fallback. Canon overrides when both exist.


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
