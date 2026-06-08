# Workflow Pattern Examples

These are prompt shapes, not scripts.

## Flaky Failure

```text
Use a workflow pattern to reproduce this flaky failure. Generate independent hypotheses from logs, recent diffs, and environment. Test each hypothesis in isolation. Stop when one hypothesis explains the failure and a targeted verification passes.
```

Patterns: `fan-out-and-synthesize`, `adversarial-verification`, `loop-until-done`.

## Session Mining To Rules

```text
Mine recent agent sessions for repeated corrections. Cluster candidates, verify whether each would have prevented a real mistake, then Codify only the survivors.
```

Patterns: `fan-out-and-synthesize`, `generate-and-filter`, `adversarial-verification`.

## Blog Claim Verification

```text
Extract every technical claim from this draft. Verify each claim against the codebase or cited source. Synthesize a report with unsupported claims and fixes.
```

Patterns: `fan-out-and-synthesize`, `adversarial-verification`.

## Repair Root Cause

```text
For this Yunxiao bug, split investigation into logs, code path, recent changes, and known incidents. Synthesize root-cause hypotheses, then have a verifier challenge the top hypothesis before patching.
```

Patterns: `fan-out-and-synthesize`, `adversarial-verification`.

## Breach Provenance QA

```text
Generate the page, then verify that layout comes from html-effectiveness, style comes from DESIGN.md, and the footer/comment expose layout_name, style_name, and exact hidden paths.
```

Patterns: `classify-and-act`, `adversarial-verification`.

## Candidate Sorting

```text
Bucket a large list in parallel, compare borderline items pairwise, then synthesize a ranked shortlist with evidence and unresolved cases.
```

Patterns: `classify-and-act`, `tournament`, `fan-out-and-synthesize`.
