---
name: traceback
description: |
  Evidence-backed three-way delivery alignment gate: approved design/fix plan/
  acceptance contract → implementation → mapped and executed tests. Produces a
  machine-readable alignment record, deterministic Markdown view, and gate result.

  Use when an explicit design document, fix plan, acceptance checklist, or public
  contract exists and the user/workflow asks whether delivery is complete:
  "delivery check", "delivery align", "检查交付一致性", "对齐检查", "gap scan",
  "追溯检查", "三阶段对齐", "design-implementation gap",
  "are we missing anything from the spec", "方案和代码一致吗".
  Run after implementation validation and Review Gate, before sanitize/Turnover.
  Do not trigger for stack traces, runtime exceptions, or generic line coverage.
---

# traceback — Delivery Alignment Gate

Traceback consumes the clean-delivery contract as an approved-source boundary:
`/home/yhr/.agents/repos/agent-skills/references/clean-delivery-contract.md`。
`alignment.json` may preserve evidence and waivers, but `alignment.md` maps only
accepted requirements to implementation and passed validation; it is not a
transcript summary.

Verify one chain with file evidence:

    approved source -> implementation -> test mapping -> executed validation

traceback is not a linter, test runner, or duplicate code review. Review Gate
judges code quality; traceback proves delivery traceability.

## Hard rules

1. Derive requirements only from approved source artifacts.
2. Preserve stable requirement IDs across reruns.
3. Treat summaries as views; 'alignment.json' is the machine truth source.
4. Distinguish test mapping from an actually passed validation run.
5. Re-read files. Never infer coverage from naming or proximity alone.
6. Block stale evidence when source hashes, Git HEAD, or workspace fingerprint changed.
7. Record critical gaps, waivers, and skipped traceback in Canon.

## Input resolution

Resolve the first available approved source:

1. Canon task page § Artifacts: 'design_doc_path', 'fix_plan_path',
   'acceptance_checklist_path', or public contract.
2. Project + branch -> Canon task page using
   '/home/yhr/.agents/repos/agent-skills/references/canon-task-resolution.md'.
3. Explicit user-provided path.

If no approved source exists, use 'mode: skipped'; record the reason in Canon.
Do not invent a specification from code.

## Output contract

Write only:

    .planning/<task-or-workflow-slug>/
    ├── alignment.json
    ├── alignment.md
    └── traceback-gate.json

Read 'references/alignment-schema.md' before creating or updating
'alignment.json'.

- 'alignment.json': evidence and status truth source.
- 'alignment.md': deterministic human view generated from JSON.
- 'traceback-gate.json': current verdict, blockers, warnings, and fingerprint.

Do not recreate the retired document/dev/test checklist files.

## Workflow

When an execution task has a scope-gate result, pass its absolute JSON path to
the Traceback gate. A missing, blocked, stale, or malformed scope gate blocks
Traceback; without the option, existing Traceback behavior remains unchanged.

    python3 <skill-dir>/scripts/traceback_gate.py \
      --dir .planning/<slug> --repo <repo-root> \
      --scope-gate .planning/<slug>/scope-gate.json --json

### 1. Capture current workspace identity

    python3 <skill-dir>/scripts/traceback_gate.py --repo <repo-root> --fingerprint

Copy 'checked_commit' and 'workspace_fingerprint' into 'alignment.json'.
Hash every approved input file with SHA-256.

### 2. Extract stable requirements

For every testable requirement, record stable ID, exact source reference,
severity, implementation evidence, test mapping, passed validation-run IDs,
and explicit waiver when applicable. Scan public interfaces and changed module
ownership for 'boundary_drift'. Do not create code-derived requirements to hide drift.

### 3. Record validation runs

Record exact commands and results in 'validation_runs'. A test is 'covered'
only when it has direct/inferred mapping evidence and references at least one
passed validation run. Preserve failed runs; they block.

### 4. Render the human view

    python3 <skill-dir>/scripts/render_alignment.py --input .planning/<slug>/alignment.json --output .planning/<slug>/alignment.md

Never hand-edit 'alignment.md'; rerender it.

### 5. Run the gate

    python3 <skill-dir>/scripts/traceback_gate.py --dir .planning/<slug> --repo <repo-root> --json

Verdicts:

- 'pass': current evidence is valid; blocker policy passes.
- 'blocked': malformed, stale, failed validation, or blocking delivery gaps.
- 'skipped': no approved source; Canon contains the explicit skip reason.

### 6. Promote durable state

Follow '/home/yhr/.agents/repos/agent-skills/references/canon-output-contract.md'.

Update the Canon task page with blockers, missing tests, boundary drift,
waivers, skip reason, and absolute paths to all three artifacts. Create an
update-card when the result changes a durable decision or residual risk.

## Blocker policy

- Any open P1 gap -> block.
- Three or more open P2 gaps -> block.
- Any failed validation run -> block.
- Invalid/missing evidence, stale fingerprint, or stale rendered view -> block.
- P3 and at most two P2 gaps -> pass with warnings; record them in Canon.
- Waivers require 'by', 'reason', and 'date'; waived risk remains visible.

## tasking integration

tasking Engage reruns this gate from '.planning/<demand-id>/' and consumes
'traceback-gate.json'. Do not write or trust 'state.json.traceback_done'.

## Gotchas

- 'implemented' requires existing implementation evidence.
- 'covered' requires existing test evidence plus a passed validation-run ID.
- 'not-applicable' requires a reason.
- Passing tests do not excuse undocumented public-interface expansion.
- Keep IDs stable; update existing rows rather than regenerate them.
- Do not reuse a gate after code, untracked source, or approved inputs change.
- Canon is durable truth; '.planning/' remains runtime evidence.
