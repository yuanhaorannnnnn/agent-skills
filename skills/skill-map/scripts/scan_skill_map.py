#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


RUNTIME_DIRS = [
    ("agent", Path.home() / ".agents" / "skills"),
    ("claude", Path.home() / ".claude" / "skills"),
    ("pi", Path.home() / ".pi" / "agent" / "skills"),
]


def parse_frontmatter(skill_md: Path) -> dict[str, str]:
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


def scan() -> list[dict[str, str]]:
    records = []
    seen = set()

    for runtime, root in RUNTIME_DIRS:
        if not root.exists():
            continue
        for item in sorted(root.iterdir()):
            if not item.is_dir() or item.name.startswith("."):
                continue
            skill_md = item / "SKILL.md"
            if not skill_md.exists():
                continue
            if item.name in seen:
                continue

            data = parse_frontmatter(skill_md)
            records.append(
                {
                    "name": data.get("name", item.name),
                    "version": data.get("version", "-"),
                    "user_invocable": str(data.get("user_invocable", "false")).lower() == "true",
                    "description": data.get("description", "").replace("\n", " ").strip(),
                    "runtime": runtime,
                    "path": str(item),
                }
            )
            seen.add(item.name)

    return records


if __name__ == "__main__":
    print(json.dumps(scan(), ensure_ascii=False, indent=2))
