#!/usr/bin/env python3
"""Check that the current workspace stays within an accepted specification."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path


SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))
from accepted_spec import load_spec  # noqa: E402


RUNTIME_PREFIXES = (".planning/", ".proposal/", ".agent-state/")
DEPENDENCY_FILE_RE = re.compile(
    r"(^|/)(requirements[^/]*\.txt|constraints[^/]*\.txt|"
    r"package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|"
    r"pyproject\.toml|setup\.py|go\.mod|Cargo\.toml|Cargo\.lock)$",
    re.IGNORECASE,
)
PACKAGE_NAME_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+)")


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def changed_files(repo: Path) -> list[str]:
    tracked = git(repo, "diff", "--name-only", "HEAD", "--").splitlines()
    untracked = git(
        repo, "ls-files", "--others", "--exclude-standard"
    ).splitlines()
    return sorted(
        {
            path.replace(os.sep, "/")
            for path in tracked + untracked
            if path and not path.startswith(RUNTIME_PREFIXES)
        }
    )


def in_scope(path: str, patterns: list[str]) -> bool:
    normalized = path.replace(os.sep, "/")
    for raw_pattern in patterns:
        pattern = raw_pattern.strip().replace(os.sep, "/")
        if not pattern:
            continue
        if fnmatch.fnmatchcase(normalized, pattern):
            return True
        if pattern.endswith("/**") and normalized.startswith(pattern[:-2]):
            return True
        if pattern.endswith("/") and normalized.startswith(pattern):
            return True
    return False


def dependency_name(path: str, line: str) -> str | None:
    name = Path(path).name.lower()
    content = line[1:].strip()
    if not content or content.startswith(("#", "//", "/*", "*", "{", "}", "[", "]")):
        return None
    if name.startswith(("requirements", "constraints")):
        match = PACKAGE_NAME_RE.match(content)
        return match.group(1) if match else None
    if name in {"go.mod", "cargo.toml", "cargo.lock"}:
        match = PACKAGE_NAME_RE.match(content)
        return match.group(1) if match else None
    return "manifest_changed"


def dependency_changes(
    repo: Path, files: list[str], approved: list[str]
) -> list[dict[str, str]]:
    allowed = {item.strip() for item in approved}
    manifest_files = [path for path in files if DEPENDENCY_FILE_RE.search(path)]
    if not manifest_files:
        return []
    diff = git(
        repo,
        "diff",
        "--unified=0",
        "HEAD",
        "--",
        *manifest_files,
    )
    findings = []
    tracked_files = set(git(repo, "ls-files").splitlines())

    def record(path: str, candidate: str | None):
        if candidate and candidate not in allowed and path not in allowed:
            findings.append({"path": path, "candidate": candidate})

    current_path = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current_path = line[6:]
            continue
        if not line.startswith("+") or line.startswith("+++"):
            continue
        path = current_path
        if path not in manifest_files:
            continue
        candidate = dependency_name(path, line)
        record(path, candidate)
    for path in manifest_files:
        if path in tracked_files:
            continue
        file_path = repo / path
        if not file_path.is_file():
            continue
        for raw_line in file_path.read_text(encoding="utf-8").splitlines():
            record(path, dependency_name(path, "+" + raw_line))
    return findings


def evaluate(repo: Path, spec_path: str | Path) -> dict:
    spec, spec_errors = load_spec(spec_path)
    if spec_errors:
        return {
            "verdict": "blocked",
            "spec_path": str(Path(spec_path).expanduser().resolve()),
            "spec_hash": "",
            "changed_files": [],
            "unmapped_hunks": [],
            "new_dependencies": [],
            "rejected_term_hits": [],
            "errors": spec_errors,
            "warnings": [],
        }

    files = changed_files(repo)
    unmapped = [
        {"path": path, "reason": "outside accepted scope"}
        for path in files
        if not in_scope(path, spec["scope"])
    ]
    dependencies = dependency_changes(
        repo, files, spec.get("approved_dependencies", [])
    )
    errors = []
    if unmapped:
        errors.append("changed files outside accepted scope")
    if dependencies:
        errors.append("unapproved dependency changes")
    return {
        "verdict": "blocked" if errors else "pass",
        "spec_path": str(Path(spec_path).expanduser().resolve()),
        "spec_hash": spec["spec_hash"],
        "checked_commit": git(repo, "rev-parse", "HEAD").strip(),
        "changed_files": files,
        "unmapped_hunks": unmapped,
        "new_dependencies": dependencies,
        "rejected_term_hits": [],
        "errors": errors,
        "warnings": [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--output")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    try:
        result = evaluate(Path(args.repo).resolve(), args.spec)
    except Exception as exc:
        result = {
            "verdict": "blocked",
            "errors": [f"workspace: {exc}"],
            "warnings": [],
        }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Scope Gate: {result['verdict'].upper()}")
        for error in result.get("errors", []):
            print(f"  [FAIL] {error}")
        if args.output:
            print(f"  gate -> {Path(args.output).resolve()}")
    return 0 if result["verdict"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
