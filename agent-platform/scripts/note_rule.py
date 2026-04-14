#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from common import ensure_state_dirs, repo_root


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a durable mistake rule to .agent-state/rules/mistakes.md.")
    parser.add_argument("--repo", default=".", help="Repository path")
    parser.add_argument("--wrong", required=True, help="What went wrong")
    parser.add_argument("--correct", required=True, help="Preferred correct behavior")
    parser.add_argument("--trigger", required=True, help="When to apply this rule")
    parser.add_argument("--promote", action="store_true", help="Also promote the rule into docs/agent-system/mistake-patterns.md")
    args = parser.parse_args()

    root = repo_root(Path(args.repo))
    state_dir = ensure_state_dirs(root)
    rules_path = state_dir / "rules" / "mistakes.md"
    existing = rules_path.read_text(encoding="utf-8") if rules_path.exists() else "# Mistake Rules\n"

    fingerprint = f"❌ 错误做法：{args.wrong}\n✅ 正确做法：{args.correct}\n触发场景：{args.trigger}"
    if fingerprint in existing:
        print(f"Rule already exists in {rules_path}")
        return 0

    if not existing.endswith("\n"):
        existing += "\n"
    if existing.strip() and existing.strip() != "# Mistake Rules":
        existing += "\n"
    existing += "\n".join(
        [
            "## Rule",
            f"❌ 错误做法：{args.wrong}",
            f"✅ 正确做法：{args.correct}",
            f"触发场景：{args.trigger}",
            "",
        ]
    )
    rules_path.write_text(existing, encoding="utf-8")

    if args.promote:
        patterns_path = root / "docs" / "agent-system" / "mistake-patterns.md"
        if patterns_path.exists():
            promoted_block = "\n".join(
                [
                    f"### {args.correct}",
                    "",
                    f"- 错误做法：{args.wrong}",
                    f"- 正确做法：{args.correct}",
                    f"- 触发场景：{args.trigger}",
                    "",
                ]
            )
            patterns_text = patterns_path.read_text(encoding="utf-8")
            if promoted_block.strip() not in patterns_text:
                if not patterns_text.endswith("\n"):
                    patterns_text += "\n"
                patterns_text += "\n" + promoted_block
                patterns_path.write_text(patterns_text, encoding="utf-8")
    print(rules_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
