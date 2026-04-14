#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path

from common import git_output, repo_root


HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)")


def collect_changed_locations(diff_text: str) -> list[tuple[str, int]]:
    locations: list[tuple[str, int]] = []
    current_file = ""
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
            continue
        match = HUNK_RE.match(line)
        if current_file and match:
            locations.append((current_file, int(match.group(1))))
    return locations


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a structured review starter from current git diffs.")
    parser.add_argument("--repo", default=".", help="Repository path")
    args = parser.parse_args()

    root = repo_root(Path(args.repo))
    unstaged = git_output(root, ["diff"], default="")
    staged = git_output(root, ["diff", "--cached"], default="")
    memory_path = root / ".agent-state" / "MEMORY.md"

    if not unstaged and not staged:
        print("## Code Review Report\n\nNo uncommitted changes found.")
        return 0

    locations = collect_changed_locations(unstaged + "\n" + staged)
    files = sorted({file for file, _ in locations})

    print("## Code Review Report\n")
    print(f"**Sources used**: git diff, git diff --cached, {memory_path if memory_path.exists() else 'no MEMORY.md found'}")
    print(f"**Files reviewed**: {', '.join(files) if files else 'unable to infer files from diff headers'}\n")
    print("### Critical")
    print("- None identified automatically. Manual review still required.\n")
    print("### Warnings")
    print("- Check changed locations listed below against the review checklist.\n")
    print("### Changed Locations")
    for file, line in locations:
        print(f"- {file}:{line}")
    print("\n### Summary")
    print("- Starter report generated. Perform manual review for correctness, regressions, and missing tests.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
