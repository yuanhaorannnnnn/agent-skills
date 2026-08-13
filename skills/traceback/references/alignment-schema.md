# Traceback Alignment Schema

Read before writing 'alignment.json'. The gate rejects unknown statuses,
missing evidence, stale hashes, and inconsistent delivery states.

## Root object

~~~json
{
  "schema_version": 1,
  "mode": "alignment",
  "task": {
    "id": "JHBN-0000",
    "canon_task_path": "/media/yhr/2T/Canon/tasks/JHBN-0000.md"
  },
  "checked_at": "2026-07-22T11:30:00+08:00",
  "checked_commit": "<git HEAD>",
  "workspace_fingerprint": "<sha256>",
  "inputs": [],
  "requirements": [],
  "validation_runs": [],
  "boundary_drift": [],
  "canon": {
    "recorded": false,
    "update_card_path": ""
  }
}
~~~

Modes:

- 'alignment': requires approved inputs and requirements.
- 'skipped': requires empty inputs/requirements, 'canon.recorded: true', and
  'canon.skip_reason'.

## Inputs

~~~json
{
  "kind": "design",
  "path": "/absolute/or/repo-relative/design.md",
  "sha256": "<64 lowercase hex>",
  "label": "Optional label"
}
~~~

Allowed kinds: 'design', 'fix-plan', 'acceptance', 'contract'. The gate resolves
relative paths from '--repo', checks existence, and recomputes SHA-256.

## Requirements

~~~json
{
  "id": "REQ-001",
  "source_ref": "design.md §3.2",
  "requirement": "Observable behavior",
  "severity": "P1",
  "implementation": {
    "status": "implemented",
    "confidence": "direct",
    "evidence": [{"path": "src/module.py", "symbol": "run", "line": 42}]
  },
  "tests": {
    "status": "covered",
    "confidence": "direct",
    "evidence": [{"path": "tests/test_module.py", "symbol": "test_run", "line": 18}],
    "run_ids": ["RUN-001"]
  }
}
~~~

Severities: 'P1', 'P2', 'P3'.

Implementation statuses:
- 'implemented': evidence plus 'direct|inferred' confidence.
- 'missing': open gap.
- 'not-applicable': reason required.
- 'waived': waiver required.

Test statuses:
- 'covered': test evidence and a referenced passed run.
- 'missing': gap when implementation exists.
- 'not-applicable': reason required.
- 'waived': waiver required.

Evidence requires an existing path. Symbol and positive line are optional.

Waiver:

~~~json
{"by": "owner", "reason": "Accepted residual risk", "date": "2026-07-22"}
~~~

## Validation runs

~~~json
{
  "id": "RUN-001",
  "command": "python3 -m pytest tests/test_module.py -q",
  "result": "passed",
  "artifact": "/optional/log.txt"
}
~~~

Results: 'passed', 'failed', 'not-run'. Any failed run blocks. A covered P1/P2
test must reference a passed run.

## Boundary drift

~~~json
{
  "id": "DRIFT-001",
  "description": "New public method is absent from the design",
  "severity": "P2",
  "status": "open",
  "evidence": [{"path": "src/api.py", "symbol": "new_method"}]
}
~~~

Statuses: 'open', 'accepted', 'waived'. Accepted requires a reason; waived
requires a waiver.

## Canon state

Set 'canon.recorded: true' when Traceback is skipped, gaps remain, a waiver
exists, or boundary drift is open/accepted. 'task.canon_task_path' must always
identify an existing file.

## Workspace identity

Generate immediately before writing the alignment:

    python3 <skill-dir>/scripts/traceback_gate.py --repo <repo-root> --fingerprint

The fingerprint includes tracked changes and non-ignored untracked files.
Runtime buffers under '.planning/', '.proposal/', and '.agent-state/' are
excluded. Input hashes independently protect approved source artifacts.
