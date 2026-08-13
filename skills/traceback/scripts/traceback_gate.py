#!/usr/bin/env python3
"""Validate Traceback alignment evidence and emit traceback-gate.json."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from render_alignment import render as render_alignment

RUNTIME_PREFIXES = (".planning/", ".proposal/", ".agent-state/")
ALLOWED_INPUT_KINDS = {"design", "fix-plan", "acceptance", "contract"}
ALLOWED_SEVERITIES = {"P1", "P2", "P3"}
ALLOWED_IMPL_STATUS = {"implemented", "missing", "not-applicable", "waived"}
ALLOWED_TEST_STATUS = {"covered", "missing", "not-applicable", "waived"}
ALLOWED_RUN_RESULT = {"passed", "failed", "not-run"}
ALLOWED_DRIFT_STATUS = {"open", "accepted", "waived"}


def canonical_digest(data):
    payload = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def git(repo, *args, binary=False):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        check=False,
        text=not binary,
    )
    if result.returncode != 0:
        detail = (
            result.stderr
            if not binary
            else result.stderr.decode("utf-8", "replace")
        )
        raise RuntimeError(detail.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def workspace_snapshot(repo):
    repo = Path(repo).resolve()
    head = git(repo, "rev-parse", "HEAD").strip()
    diff = git(
        repo,
        "diff",
        "--binary",
        "HEAD",
        "--",
        ".",
        ":(exclude).planning/**",
        ":(exclude).proposal/**",
        ":(exclude).agent-state/**",
        binary=True,
    )
    untracked_raw = git(repo, "ls-files", "--others", "--exclude-standard", "-z")
    untracked = sorted(
        path
        for path in untracked_raw.split("\0")
        if path and not path.startswith(RUNTIME_PREFIXES)
    )
    digest = hashlib.sha256()
    digest.update(diff)
    for rel in untracked:
        path = repo / rel
        if not path.is_file():
            continue
        digest.update(rel.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return {
        "checked_commit": head,
        "workspace_fingerprint": digest.hexdigest(),
        "untracked_files": untracked,
    }


def resolve_path(value, repo):
    path = Path(str(value or ""))
    return path if path.is_absolute() else Path(repo) / path


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def valid_waiver(value):
    return (
        isinstance(value, dict)
        and bool(value.get("by"))
        and bool(value.get("reason"))
        and bool(value.get("date"))
    )


def validate_evidence(entries, label, repo, errors):
    if not isinstance(entries, list) or not entries:
        errors.append(f"{label}: evidence required")
        return
    for index, item in enumerate(entries):
        prefix = f"{label}.evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: object required")
            continue
        path = resolve_path(item.get("path"), repo)
        if not item.get("path") or not path.is_file():
            errors.append(
                f"{prefix}: file not found: {item.get('path', '')}"
            )
        line = item.get("line")
        if line is not None and (not isinstance(line, int) or line < 1):
            errors.append(f"{prefix}: line must be a positive integer")


def validate_checked_at(value, errors):
    if not value:
        errors.append("checked_at: required")
        return
    try:
        datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        errors.append("checked_at: ISO-8601 timestamp required")


def validate_alignment(data, repo, current):
    errors = []
    warnings = []
    findings = []
    waivers = []

    if not isinstance(data, dict):
        return ["alignment.json: root object required"], [], [], "blocked"

    if data.get("schema_version") != 1:
        errors.append("schema_version: expected 1")

    mode = data.get("mode")
    if mode not in {"alignment", "skipped"}:
        errors.append("mode: expected alignment or skipped")

    task = data.get("task")
    if not isinstance(task, dict) or not task.get("id"):
        errors.append("task.id: required")
        task = {}
    canon_task = resolve_path(task.get("canon_task_path"), repo)
    if not task.get("canon_task_path") or not canon_task.is_file():
        errors.append("task.canon_task_path: existing file required")

    validate_checked_at(data.get("checked_at"), errors)
    if data.get("checked_commit") != current["checked_commit"]:
        errors.append("checked_commit: stale or missing")
    if data.get("workspace_fingerprint") != current["workspace_fingerprint"]:
        errors.append("workspace_fingerprint: stale or missing")

    canon = data.get("canon")
    if not isinstance(canon, dict):
        errors.append("canon: object required")
        canon = {}

    inputs = data.get("inputs")
    requirements = data.get("requirements")
    runs = data.get("validation_runs")
    drift = data.get("boundary_drift")

    if mode == "skipped":
        if inputs not in ([], None):
            errors.append("skipped mode: inputs must be empty")
        if requirements not in ([], None):
            errors.append("skipped mode: requirements must be empty")
        if not canon.get("recorded"):
            errors.append("skipped mode: canon.recorded must be true")
        if not canon.get("skip_reason"):
            errors.append("skipped mode: canon.skip_reason required")
        verdict = "blocked" if errors else "skipped"
        return errors, warnings, findings, verdict

    if not isinstance(inputs, list) or not inputs:
        errors.append("inputs: at least one approved source required")
        inputs = []
    for index, item in enumerate(inputs):
        prefix = f"inputs[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: object required")
            continue
        if item.get("kind") not in ALLOWED_INPUT_KINDS:
            errors.append(f"{prefix}.kind: invalid")
        path = resolve_path(item.get("path"), repo)
        if not item.get("path") or not path.is_file():
            errors.append(f"{prefix}.path: file not found")
        elif item.get("sha256") != file_sha256(path):
            errors.append(f"{prefix}.sha256: stale or invalid")

    if not isinstance(runs, list):
        errors.append("validation_runs: array required")
        runs = []
    run_map = {}
    for index, run in enumerate(runs):
        prefix = f"validation_runs[{index}]"
        if not isinstance(run, dict):
            errors.append(f"{prefix}: object required")
            continue
        run_id = run.get("id")
        if not run_id:
            errors.append(f"{prefix}.id: required")
        elif run_id in run_map:
            errors.append(f"{prefix}.id: duplicate {run_id}")
        else:
            run_map[run_id] = run
        if not run.get("command"):
            errors.append(f"{prefix}.command: required")
        if run.get("result") not in ALLOWED_RUN_RESULT:
            errors.append(f"{prefix}.result: invalid")
        if run.get("result") == "failed":
            findings.append(
                {
                    "id": run_id or prefix,
                    "category": "validation",
                    "severity": "P1",
                }
            )
        artifact = run.get("artifact")
        if artifact and not resolve_path(artifact, repo).is_file():
            errors.append(f"{prefix}.artifact: file not found")

    if not isinstance(requirements, list) or not requirements:
        errors.append("requirements: at least one requirement required")
        requirements = []

    seen_ids = set()
    for index, req in enumerate(requirements):
        prefix = f"requirements[{index}]"
        if not isinstance(req, dict):
            errors.append(f"{prefix}: object required")
            continue
        req_id = req.get("id")
        if not req_id:
            errors.append(f"{prefix}.id: required")
            req_id = prefix
        elif req_id in seen_ids:
            errors.append(f"{prefix}.id: duplicate {req_id}")
        seen_ids.add(req_id)
        if not req.get("source_ref"):
            errors.append(f"{prefix}.source_ref: required")
        if not req.get("requirement"):
            errors.append(f"{prefix}.requirement: required")
        severity = req.get("severity")
        if severity not in ALLOWED_SEVERITIES:
            errors.append(f"{prefix}.severity: invalid")
            severity = "P1"

        impl = req.get("implementation")
        if not isinstance(impl, dict):
            errors.append(f"{prefix}.implementation: object required")
            impl = {}
        impl_status = impl.get("status")
        if impl_status not in ALLOWED_IMPL_STATUS:
            errors.append(f"{prefix}.implementation.status: invalid")
        elif impl_status == "implemented":
            if impl.get("confidence") not in {"direct", "inferred"}:
                errors.append(
                    f"{prefix}.implementation.confidence: "
                    "direct or inferred required"
                )
            validate_evidence(
                impl.get("evidence"),
                f"{prefix}.implementation",
                repo,
                errors,
            )
        elif impl_status == "missing":
            findings.append(
                {
                    "id": req_id,
                    "category": "implementation",
                    "severity": severity,
                }
            )
        elif impl_status == "not-applicable" and not impl.get("reason"):
            errors.append(f"{prefix}.implementation.reason: required")
        elif impl_status == "waived":
            if not valid_waiver(impl.get("waiver")):
                errors.append(f"{prefix}.implementation.waiver: incomplete")
            else:
                waivers.append(f"{req_id}:implementation")

        tests = req.get("tests")
        if not isinstance(tests, dict):
            errors.append(f"{prefix}.tests: object required")
            tests = {}
        test_status = tests.get("status")
        if test_status not in ALLOWED_TEST_STATUS:
            errors.append(f"{prefix}.tests.status: invalid")
        elif test_status == "covered":
            if tests.get("confidence") not in {"direct", "inferred"}:
                errors.append(
                    f"{prefix}.tests.confidence: direct or inferred required"
                )
            validate_evidence(
                tests.get("evidence"),
                f"{prefix}.tests",
                repo,
                errors,
            )
            run_ids = tests.get("run_ids")
            if not isinstance(run_ids, list) or not run_ids:
                errors.append(
                    f"{prefix}.tests.run_ids: passed validation run required"
                )
            else:
                for run_id in run_ids:
                    run = run_map.get(run_id)
                    if not run:
                        errors.append(
                            f"{prefix}.tests.run_ids: unknown {run_id}"
                        )
                    elif run.get("result") != "passed":
                        errors.append(
                            f"{prefix}.tests.run_ids: {run_id} is not passed"
                        )
        elif test_status == "missing" and impl_status == "implemented":
            findings.append(
                {"id": req_id, "category": "tests", "severity": severity}
            )
        elif test_status == "not-applicable" and not tests.get("reason"):
            errors.append(f"{prefix}.tests.reason: required")
        elif test_status == "waived":
            if not valid_waiver(tests.get("waiver")):
                errors.append(f"{prefix}.tests.waiver: incomplete")
            else:
                waivers.append(f"{req_id}:tests")

    if not isinstance(drift, list):
        errors.append("boundary_drift: array required")
        drift = []
    seen_drift = set()
    for index, item in enumerate(drift):
        prefix = f"boundary_drift[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{prefix}: object required")
            continue
        drift_id = item.get("id")
        if not drift_id:
            errors.append(f"{prefix}.id: required")
            drift_id = prefix
        elif drift_id in seen_drift:
            errors.append(f"{prefix}.id: duplicate {drift_id}")
        seen_drift.add(drift_id)
        if not item.get("description"):
            errors.append(f"{prefix}.description: required")
        severity = item.get("severity")
        if severity not in ALLOWED_SEVERITIES:
            errors.append(f"{prefix}.severity: invalid")
            severity = "P1"
        status = item.get("status")
        if status not in ALLOWED_DRIFT_STATUS:
            errors.append(f"{prefix}.status: invalid")
        validate_evidence(item.get("evidence"), prefix, repo, errors)
        if status == "open":
            findings.append(
                {
                    "id": drift_id,
                    "category": "boundary-drift",
                    "severity": severity,
                }
            )
        elif status == "accepted" and not item.get("reason"):
            errors.append(f"{prefix}.reason: required")
        elif status == "waived":
            if not valid_waiver(item.get("waiver")):
                errors.append(f"{prefix}.waiver: incomplete")
            else:
                waivers.append(f"{drift_id}:boundary-drift")

    durable_drift = any(
        isinstance(item, dict)
        and item.get("status") in {"open", "accepted", "waived"}
        for item in drift
    )
    if findings or waivers or durable_drift:
        if not canon.get("recorded"):
            errors.append(
                "canon.recorded: required for gaps, drift, or waivers"
            )
    update_card = canon.get("update_card_path")
    if update_card and not resolve_path(update_card, repo).is_file():
        errors.append("canon.update_card_path: file not found")

    p1 = sum(1 for item in findings if item["severity"] == "P1")
    p2 = sum(1 for item in findings if item["severity"] == "P2")
    for item in findings:
        warnings.append(
            f"{item['severity']} {item['id']} {item['category']}"
        )
    for item in waivers:
        warnings.append(f"waived {item}")

    verdict = "blocked" if errors or p1 > 0 or p2 >= 3 else "pass"
    return errors, warnings, findings, verdict


def write_json_atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", help="Path to .planning/<slug>/")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--fingerprint", action="store_true")
    args = ap.parse_args()

    repo = Path(args.repo).resolve()
    try:
        current = workspace_snapshot(repo)
    except Exception as exc:
        result = {
            "verdict": "blocked",
            "errors": [f"workspace: {exc}"],
            "warnings": [],
        }
        if args.json or args.fingerprint:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"Traceback Gate: BLOCKED\n  workspace: {exc}")
        return 1

    if args.fingerprint:
        print(json.dumps(current, indent=2, ensure_ascii=False))
        return 0
    if not args.dir:
        ap.error("--dir is required unless --fingerprint is used")

    directory = Path(args.dir)
    alignment_path = directory / "alignment.json"
    markdown_path = directory / "alignment.md"
    gate_path = directory / "traceback-gate.json"

    errors = []
    warnings = []
    findings = []
    data = None
    digest = ""
    if not alignment_path.is_file():
        errors.append("alignment.json: missing")
        verdict = "blocked"
    else:
        try:
            data = json.loads(alignment_path.read_text(encoding="utf-8"))
            digest = canonical_digest(data)
            errors, warnings, findings, verdict = validate_alignment(
                data, repo, current
            )
        except Exception as exc:
            errors.append(f"alignment.json: {exc}")
            verdict = "blocked"

    if data is not None:
        if not markdown_path.is_file():
            errors.append("alignment.md: missing")
            verdict = "blocked"
        else:
            actual_markdown = markdown_path.read_text(encoding="utf-8")
            expected_markdown = render_alignment(data)
            if actual_markdown != expected_markdown:
                errors.append(
                    "alignment.md: stale or not generated from alignment.json"
                )
                verdict = "blocked"

    result = {
        "verdict": verdict,
        "task_id": (data or {}).get("task", {}).get("id", ""),
        "alignment_path": str(alignment_path.resolve()),
        "alignment_sha256": digest,
        "checked_commit": current["checked_commit"],
        "workspace_fingerprint": current["workspace_fingerprint"],
        "errors": errors,
        "warnings": warnings,
        "findings": findings,
    }
    write_json_atomic(gate_path, result)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Traceback Gate: {verdict.upper()}")
        for error in errors:
            print(f"  [FAIL] {error}")
        for warning in warnings:
            print(f"  [WARN] {warning}")
        print(f"  gate -> {gate_path}")
    return 1 if verdict == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
