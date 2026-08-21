#!/usr/bin/env python3
"""Shared validation for the accepted execution specification.

The specification is intentionally JSON-only so the gate has no third-party
runtime dependency. spec_hash covers the canonical payload without the hash
field itself.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
LIST_FIELDS = ("scope", "constraints", "acceptance", "non_goals")
ARTIFACT_MODES = frozenset(("delivery", "audit", "knowledge"))


def canonical_payload(spec: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in spec.items() if key != "spec_hash"}


def compute_spec_hash(spec: dict[str, Any]) -> str:
    encoded = json.dumps(
        canonical_payload(spec),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_spec(
    spec: Any,
    path: str | Path | None = None,
    *,
    require_artifact_mode: bool = False,
) -> list[str]:
    label = str(path) if path else "accepted_spec"
    errors: list[str] = []
    if not isinstance(spec, dict):
        return [f"{label}: root object required"]

    if spec.get("schema_version") != SCHEMA_VERSION:
        errors.append(
            f"{label}.schema_version: expected {SCHEMA_VERSION}"
        )
    if not isinstance(spec.get("task_id"), str) or not spec["task_id"].strip():
        errors.append(f"{label}.task_id: non-empty string required")
    if (
        not isinstance(spec.get("spec_version"), int)
        or isinstance(spec.get("spec_version"), bool)
        or spec["spec_version"] < 1
    ):
        errors.append(f"{label}.spec_version: positive integer required")
    if spec.get("state") != "accepted":
        errors.append(f"{label}.state: expected accepted")

    mode = spec.get("artifact_mode")
    if mode is None:
        if require_artifact_mode:
            errors.append(f"{label}.artifact_mode: required")
    elif mode not in ARTIFACT_MODES:
        errors.append(
            f"{label}.artifact_mode: expected one of {sorted(ARTIFACT_MODES)}"
        )

    for field in LIST_FIELDS:
        value = spec.get(field)
        if not isinstance(value, list) or any(
            not isinstance(item, str) or not item.strip() for item in value
        ):
            errors.append(f"{label}.{field}: list of non-empty strings required")
    if not spec.get("scope"):
        errors.append(f"{label}.scope: at least one path pattern required")

    approved = spec.get("approved_dependencies", [])
    if not isinstance(approved, list) or any(
        not isinstance(item, str) or not item.strip() for item in approved
    ):
        errors.append(
            f"{label}.approved_dependencies: list of strings required"
        )

    artifacts = spec.get("artifacts", [])
    if not isinstance(artifacts, list):
        errors.append(f"{label}.artifacts: list required")
    else:
        for index, artifact in enumerate(artifacts):
            if isinstance(artifact, str):
                if not artifact.strip():
                    errors.append(
                        f"{label}.artifacts[{index}]: non-empty path required"
                    )
                continue
            if not isinstance(artifact, dict) or not isinstance(
                artifact.get("path"), str
            ) or not artifact["path"].strip():
                errors.append(
                    f"{label}.artifacts[{index}].path: non-empty string required"
                )

    supplied_hash = spec.get("spec_hash")
    if not isinstance(supplied_hash, str) or not HASH_RE.fullmatch(supplied_hash):
        errors.append(f"{label}.spec_hash: lowercase SHA-256 hex required")
    elif supplied_hash != compute_spec_hash(spec):
        errors.append(f"{label}.spec_hash: stale or mismatched")
    return errors


def load_spec(
    path: str | Path,
    *,
    require_artifact_mode: bool = False,
) -> tuple[dict[str, Any] | None, list[str]]:
    spec_path = Path(path).expanduser().resolve()
    if not spec_path.is_file():
        return None, [f"{spec_path}: file not found"]
    try:
        data = json.loads(spec_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"{spec_path}: {exc}"]
    errors = validate_spec(
        data,
        spec_path,
        require_artifact_mode=require_artifact_mode,
    )
    return (data if not errors else None), errors


def artifact_mode(spec: dict[str, Any]) -> str | None:
    """Return the declared artifact mode, if present."""

    value = spec.get("artifact_mode")
    return value if isinstance(value, str) else None


def artifact_map(spec: dict[str, Any]) -> list[dict[str, str]]:
    result = []
    for artifact in spec.get("artifacts", []):
        if isinstance(artifact, str):
            result.append({"path": artifact})
        else:
            result.append(
                {
                    key: str(value)
                    for key, value in artifact.items()
                    if value is not None
                }
            )
    return result
