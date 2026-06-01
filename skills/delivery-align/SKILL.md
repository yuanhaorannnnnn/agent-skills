---
name: delivery-align
description: |
  Three-way artifact alignment check: design document → implementation code →
  test coverage. Finds gaps where the design says X but the code doesn't do X,
  or the code does Y but no test covers it. Outputs structured checklists to
  `.planning/conversations/<id>/`.

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

Resolve the conversation id to find relevant design documents:
1. Explicit `--conversation <name>` → read `.planning/conversations/<id>/`
2. Read `.agent-state/ACTIVE_CONVERSATION` if no explicit id
3. Fall back to scanning recent planning directories

From the planning context, identify:
- The **design document(s)** — any `.md` in the conversation directory or
  referenced from task_plan.md
- The **implementation directory** — inferred from project structure and
  conversation context
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

## Constraints

- Work from actual files, not assumptions. If you can't find a match, say so.
- Keep IDs stable across runs — use the same naming convention so checklists
  accumulate over time rather than being recreated from scratch.
- If a previous checklist exists, update it in place rather than overwriting.
- Don't invent requirements that aren't in the design document.
- Don't claim test coverage unless you've found actual test code.
