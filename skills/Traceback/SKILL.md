---
name: Traceback
description: |
  Three-way artifact alignment check: design document → implementation code →
  test coverage. Finds gaps where the design says X but the code doesn't do X,
  or the code does Y but no test covers it. Outputs structured checklists to
  the Canon task page (§ Findings or dedicated traceback section).

  Use this skill whenever the user wants to verify that design, implementation,
  and tests are consistent — at phase completion, before merge, or during review.
  Trigger on: "delivery check", "delivery align", "检查交付一致性",
  "对齐检查", "gap scan", "追溯检查", "三阶段对齐", "design-implementation gap",
  "are we missing anything from the spec", "检查有没有漏掉的",
  "compare spec with code", "方案和代码一致吗", "检查覆盖".
---

# Delivery Align

Check that three artifacts — design document, implementation code, and test
files — are consistent. Not a linter, not a test runner. A gap detector.

## Core Rule

Only report what you can prove from the actual files. If a requirement has no
matching code, say so. If code exists but has no test, say so. Never fabricate
a match to make things look consistent.

## Input

Resolve the design document via Canon task page:

1. **Canon task page** — read `/media/yhr/2T/Canon/tasks/<task>.md` § Artifacts for `design_doc_path`
2. **Project + branch → task page** — use task page resolution logic (matching Secure) to find the relevant task page
3. **Explicit path** — user provides design document path directly

From the design document and task context, identify:
- The **design document(s)** — referenced in task page § Artifacts or provided explicitly
- The **implementation directory** — inferred from project structure and task context
- The **test directory** — same inference

If no design document is found, ask the user to specify one.

## Workflow

### Step 1: Extract requirements from the design document

Read the design document(s) and produce `document-dev-checklist.md`:

- Extract every testable requirement, scenario, acceptance criterion, or
  functional specification.
- Assign each a stable ID (e.g. `REQ-001`).
- For each requirement, note the expected behavior, inputs/outputs, and any
  specific constraints mentioned in the design.
- If the document references specific file names, module names, or API
  endpoints, preserve them — they'll be used for matching.

Output structure:
```markdown
# Document → Development Checklist
| ID | Requirement | Expected Behavior | Design Reference |
|----|------------|-------------------|-----------------|
| REQ-001 | ... | ... | doc.md §3.2 |
```

### Step 2: Map implementation against requirements

Scan the implementation files and produce `dev-test-coverage-checklist.md`:

- For each `REQ-XXX`, search the codebase for matching implementation.
- Match by: function names, class names, comments referencing the design,
  parameter names, file names, module structure.
- Tag each with a confidence level:
  - `direct` — explicit reference to the requirement (e.g. function named after it)
  - `inferred` — semantic match based on behavior and context
  - `none` — no matching implementation found
- For matched requirements, list the exact file paths and symbols.
- For unmatched requirements, note what's missing.

Output structure:
```markdown
# Development → Test Coverage Checklist
| REQ-ID | Implementation | Confidence | Test Coverage |
|--------|---------------|------------|---------------|
| REQ-001 | `src/accel.py:run_simulation()` | direct | `test_accel.py` |
| REQ-002 | (not found) | none | - |
```

The *Test Coverage* column is filled in Step 3.

### Step 3: Check test coverage against implementation

For each requirement that HAS an implementation, check if there are tests:

- Search for test files that exercise the identified implementation symbols.
- A test is considered covering if it calls the function, asserts on related
  output, or tests the scenario described in the requirement.
- Tag each with confidence: `direct`, `inferred`, `missing`.
- Note any implementation code that has NO corresponding test at all.

### Step 4: Generate alignment summary

Produce `align-summary.md`:

```markdown
# Alignment Summary
**Conversation**: `<id>`
**Date**: YYYY-MM-DD

## Overall
| Stage | Total | Covered | Missing | Rate |
|-------|-------|---------|---------|------|
| Design → Dev | N | X | Y | Z% |
| Dev → Test | N | X | Y | Z% |

## Critical Gaps
Requirements with no implementation AND no test.
[list]

## Implementation Without Tests
Code that exists but has zero test coverage.
[list]

## Recommendations
[what to fix first]
```

All three files go to `.planning/conversations/<id>/`.


## Workflow Gate Contract

Traceback is the design/code/test alignment gate and follows the shared workflow output contract:

```text
/home/yhr/.agents/repos/agent-skills/references/skill-output-contract.md
```

It should run after implementation and Review Gate when a design doc, fix plan, or acceptance checklist exists. Its output is evidence for Sanitize, Turnover, Closeout, or explicit residual-risk handoff.

## Gotchas

- Do not invent requirements from code. Requirements come from the design/fix plan/user-approved checklist.
- Do not claim test coverage from file proximity or naming alone. Coverage requires a test that calls the symbol, asserts the behavior, or exercises the scenario.
- `Design -> Dev` passing does not imply `Dev -> Test` passing. Report both stages separately.
- Keep checklist IDs stable across reruns; updating existing artifacts is better than regenerating incompatible IDs.
- Critical gaps must be written to Canon, not left only in `.planning/` files.

## Canon 输出边界

读取共享契约：`/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md`。

- `document-dev-checklist.md`、`dev-test-coverage-checklist.md`、`align-summary.md` 是 alignment artifacts，仍写入 `.planning/conversations/<id>/`。
- Critical gaps、missing tests、design decisions 和 residual risk 应同步到 Canon task/project/incident/update-card。
- 创建或更新 `/media/yhr/2T/Canon/raw/update-cards/<date>-traceback-<conversation-id>.md`，引用三份 checklist 的绝对路径。
- 如果检查结果只是临时草稿，最终回复要说明未做 Canon promotion。

## Constraints

- Work from actual files, not assumptions. If you can't find a match, say so.
- Keep IDs stable across runs — use the same naming convention so checklists
  accumulate over time rather than being recreated from scratch.
- If a previous checklist exists, update it in place rather than overwriting.
- Don't invent requirements that aren't in the design document.
- Don't claim test coverage unless you've found actual test code.
- Do not present `.planning/` checklist files as long-term source of truth; Canon owns durable gap and decision state.
