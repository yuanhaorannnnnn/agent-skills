#!/usr/bin/env python3
"""Scan agent runtime directories for specified skills and output their metadata as JSON."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

RUNTIME_DIRS = [
    Path.home() / ".agents" / "skills",
    Path.home() / ".claude" / "skills",
    Path.home() / ".codex" / "skills",
    Path.home() / ".kimi" / "skills",
    Path.home() / ".pi" / "agent" / "skills",
    Path.home() / ".hermes" / "skills",
]


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
    """Parse YAML frontmatter from a SKILL.md file.

    Supports multiline values with the `|` syntax (indentation-based).
    """
    text = skill_md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        return {}
    frontmatter = parts[0].removeprefix("---\n")
    data: dict[str, str] = {}
    current_key = None
    multiline = False
    buffer: list[str] = []

    for raw_line in frontmatter.splitlines():
        line = raw_line.rstrip("\n")
        if multiline:
            if line.startswith("  "):
                buffer.append(line[2:])
                continue
            if current_key is not None:
                data[current_key] = "\n".join(buffer).strip()
            current_key = None
            multiline = False
            buffer = []

        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if not match:
            continue
        key, value = match.groups()
        if value == "|":
            current_key = key
            multiline = True
            buffer = []
            continue
        value = value.strip().strip('"').strip("'")
        data[key] = value

    if multiline and current_key is not None:
        data[current_key] = "\n".join(buffer).strip()

    return data


def find_skill(name: str) -> dict[str, str] | None:
    """Find a skill by name across all runtime directories.

    Returns the first match found (runtime priority order).
    """
    for root in RUNTIME_DIRS:
        if not root.exists():
            continue
        skill_dir = root / name
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        data = parse_frontmatter(skill_md)
        return {
            "name": data.get("name", name),
            "description": data.get("description", "").strip(),
            "version": data.get("version", "-"),
            "user_invocable": str(data.get("user_invocable", "false")).lower() == "true",
            "category": data.get("category", "uncategorized"),
            "path": str(skill_dir),
        }
    return None


def scan(target_names: list[str]) -> tuple[list[dict], list[str]]:
    """Scan for the specified skill names.

    Returns a tuple of (found_skills, missing_names).
    """
    found: list[dict] = []
    missing: list[str] = []

    for name in target_names:
        skill = find_skill(name)
        if skill:
            found.append(skill)
        else:
            missing.append(name)

    return found, missing


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Scan runtime skill directories for specified skills."
    )
    parser.add_argument("names", nargs="+", help="Skill names to find")
    parser.add_argument(
        "--warn-missing",
        action="store_true",
        default=True,
        help="Print warnings for missing skills to stderr",
    )
    args = parser.parse_args()

    found, missing = scan(args.names)

    if args.warn_missing and missing:
        for name in missing:
            print(f"Warning: skill '{name}' not found in any runtime directory", file=sys.stderr)

    if not found:
        print("Error: no skills found", file=sys.stderr)
        return 1

    print(json.dumps(found, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
