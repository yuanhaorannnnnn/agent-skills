#!/usr/bin/env python3
"""Render Traceback alignment.json into a deterministic Markdown view."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def canonical_digest(data):
    payload = json.dumps(
        data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def esc(value):
    return str(value or "").replace("|", "\|").replace("\n", " ")


def evidence_text(entries):
    values = []
    for item in entries or []:
        if not isinstance(item, dict):
            continue
        value = str(item.get("path", ""))
        if item.get("symbol"):
            value += f":{item['symbol']}"
        if item.get("line"):
            value += f":{item['line']}"
        if value:
            values.append(value)
    return ", ".join(values) or "-"


def waiver_text(item):
    waiver = item.get("waiver") if isinstance(item, dict) else None
    if not isinstance(waiver, dict):
        return ""
    return (
        f"{waiver.get('by', '')}: {waiver.get('reason', '')} "
        f"({waiver.get('date', '')})"
    )


def render(data):
    digest = canonical_digest(data)
    task = data.get("task", {})
    mode = data.get("mode", "alignment")
    reqs = data.get("requirements", [])
    runs = data.get("validation_runs", [])
    drift = data.get("boundary_drift", [])
    lines = [
        f"<!-- alignment-sha256: {digest} -->",
        "# Traceback Alignment",
        "",
        f"**Task**: {task.get('id', '')}",
        f"**Canon**: {task.get('canon_task_path', '')}",
        f"**Mode**: {mode}",
        f"**Checked at**: {data.get('checked_at', '')}",
        f"**Commit**: {data.get('checked_commit', '')}",
        "",
    ]

    if mode == "skipped":
        lines += [
            "## Skipped",
            "",
            data.get("canon", {}).get("skip_reason", "No reason recorded."),
            "",
        ]
        return "\n".join(lines)

    implemented = sum(
        1 for r in reqs
        if r.get("implementation", {}).get("status") == "implemented"
    )
    covered = sum(
        1 for r in reqs if r.get("tests", {}).get("status") == "covered"
    )
    missing_impl = sum(
        1 for r in reqs
        if r.get("implementation", {}).get("status") == "missing"
    )
    missing_tests = sum(
        1 for r in reqs
        if r.get("implementation", {}).get("status") == "implemented"
        and r.get("tests", {}).get("status") == "missing"
    )
    total = len(reqs)
    impl_rate = f"{implemented / total:.0%}" if total else "0%"
    test_rate = f"{covered / total:.0%}" if total else "0%"

    lines += [
        "## Overall",
        "",
        "| Stage | Total | Covered | Missing | Rate |",
        "|---|---:|---:|---:|---:|",
        f"| Design -> Dev | {total} | {implemented} | {missing_impl} | {impl_rate} |",
        f"| Dev -> Test | {total} | {covered} | {missing_tests} | {test_rate} |",
        "",
        "## Requirements",
        "",
        "| ID | Severity | Requirement | Implementation | Tests | Source |",
        "|---|---|---|---|---|---|",
    ]

    for req in reqs:
        impl = req.get("implementation", {})
        tests = req.get("tests", {})
        impl_cell = (
            f"{impl.get('status', '')}: "
            f"{evidence_text(impl.get('evidence'))}"
        )
        test_cell = (
            f"{tests.get('status', '')}: "
            f"{evidence_text(tests.get('evidence'))}"
        )
        lines.append(
            "| {id} | {severity} | {requirement} | {impl} | {tests} | {source} |".format(
                id=esc(req.get("id")),
                severity=esc(req.get("severity")),
                requirement=esc(req.get("requirement")),
                impl=esc(impl_cell),
                tests=esc(test_cell),
                source=esc(req.get("source_ref")),
            )
        )

    critical = []
    no_tests = []
    waivers = []
    for req in reqs:
        impl = req.get("implementation", {})
        tests = req.get("tests", {})
        if impl.get("status") == "missing":
            critical.append(
                f"- {req.get('id')}: implementation missing "
                f"({req.get('severity')})"
            )
        elif (
            impl.get("status") == "implemented"
            and tests.get("status") == "missing"
        ):
            no_tests.append(
                f"- {req.get('id')}: test missing ({req.get('severity')})"
            )
        for part_name, part in (("implementation", impl), ("tests", tests)):
            if part.get("status") == "waived":
                waivers.append(
                    f"- {req.get('id')} {part_name}: {waiver_text(part)}"
                )

    lines += ["", "## Critical Gaps", ""]
    lines += critical or ["None."]
    lines += ["", "## Implementation Without Tests", ""]
    lines += no_tests or ["None."]
    lines += ["", "## Boundary Drift", ""]
    if drift:
        for item in drift:
            lines.append(
                f"- {item.get('id')}: {item.get('description')} "
                f"({item.get('severity')}, {item.get('status')}) — "
                f"{evidence_text(item.get('evidence'))}"
            )
            if item.get("status") == "waived":
                waivers.append(
                    f"- {item.get('id')} boundary drift: {waiver_text(item)}"
                )
    else:
        lines.append("None.")

    lines += ["", "## Waivers", ""]
    lines += waivers or ["None."]
    lines += ["", "## Validation Runs", ""]
    if runs:
        for run in runs:
            artifact = (
                f" — {run.get('artifact')}" if run.get("artifact") else ""
            )
            lines.append(
                f"- {run.get('id')}: {run.get('command', '')} -> "
                f"{run.get('result', '')}{artifact}"
            )
    else:
        lines.append("None.")

    lines += ["", "## Inputs", ""]
    for item in data.get("inputs", []):
        lines.append(
            f"- {item.get('kind')}: {item.get('path')} "
            f"(sha256: {item.get('sha256')})"
        )
    lines += ["", "## Canon", ""]
    canon = data.get("canon", {})
    lines.append(f"- Recorded: {bool(canon.get('recorded'))}")
    if canon.get("update_card_path"):
        lines.append(f"- Update card: {canon.get('update_card_path')}")
    lines.append("")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    body = render(data)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_name(output_path.name + ".tmp")
    tmp.write_text(body, encoding="utf-8")
    os.replace(tmp, output_path)
    print(f"alignment.md -> {output_path}")


if __name__ == "__main__":
    main()
