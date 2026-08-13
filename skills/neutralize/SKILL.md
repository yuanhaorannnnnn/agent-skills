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
2. Define the observable target: current failure evidence, expected result, and fastest rerun command. Reproduce if practical; otherwise record why reproduction is unavailable.
3. Identify root cause.
4. Apply the minimum safe correction as one verifiable slice.
5. Verify the exact symptom first, then the smallest relevant regression scope.
6. Search adjacent files and similar call sites for the same error shape.
7. If a public interface changed, record whether it expanded, stayed stable, or shrank and what complexity remains hidden behind it.
8. Write gate evidence file — `failure_observation`, `reproduction_command` or `reproduction_skipped_reason`, `rerun_command`, `rerun_exit_code`, `adjacent_searches`, `adjacent_findings`, `public_interface_changed`, `boundary_assessment`, `remaining_risk` → `.agent-state/neutralize-gate.json`.
9. Run gate:
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
  "failure_observation": "pytest fails with AssertionError at tests/test_foo.py:42",
  "reproduction_command": "pytest tests/test_foo.py -v",
  "reproduction_skipped_reason": "",
  "rerun_command": "pytest tests/test_foo.py -v",
  "rerun_exit_code": 0,
  "rerun_output_sample": "...",
  "adjacent_searches": ["rg 'same_pattern' src/", "rg 'similar_call' lib/"],
  "adjacent_findings": ["src/bar.py:42 same pattern"],
  "public_interface_changed": false,
  "boundary_assessment": "public interface unchanged; correction remains inside parser module",
  "remaining_risk": "only checked Python side; C++ callers not scanned"
}
```

## Rule Sources

- Canon `/media/yhr/2T/Canon/{projects,tasks,decisions,patterns,incidents}` — primary source for durable context, known failure modes, reusable fixes. Query first.
- Canon overrides `.agent-state/` when both exist. Code overrides Canon when they conflict — Canon captures intent, code captures current reality.
- `.agent-state/MEMORY.md` and `.agent-state/rules/mistakes.md` — compatibility fallback only.


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
