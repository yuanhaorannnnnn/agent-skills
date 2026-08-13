#!/usr/bin/env python3
"""Run isolated baseline-vs-skill Codex responses for existing eval cases."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def run_arm(
    codex: Path,
    auth_file: Path,
    skill_dir: Path,
    prompt: str,
    model: str,
    arm: str,
) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"skill-ab-{arm}-") as tmp:
        root = Path(tmp)
        isolated_home = root / "home"
        isolated_codex = isolated_home / ".codex"
        workdir = root / "work"
        output = root / "response.txt"
        isolated_codex.mkdir(parents=True)
        workdir.mkdir()
        (isolated_codex / "auth.json").symlink_to(auth_file)

        arm_prompt = prompt
        if arm == "skill":
            skills_root = isolated_home / ".agents" / "skills"
            skills_root.mkdir(parents=True)
            (skills_root / skill_dir.name).symlink_to(skill_dir, target_is_directory=True)
            arm_prompt = f"Use the {skill_dir.name} skill for this request.\n\n{prompt}"

        env = dict(os.environ)
        env["HOME"] = str(isolated_home)
        env["CODEX_HOME"] = str(isolated_codex)
        command = [
            str(codex),
            "exec",
            "--ignore-user-config",
            "--ephemeral",
            "--skip-git-repo-check",
            "-C",
            str(workdir),
            "-m",
            model,
            "-s",
            "read-only",
            "-o",
            str(output),
            arm_prompt,
        ]
        result = subprocess.run(
            command,
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
        response = output.read_text() if output.exists() else ""
        return {
            "returncode": result.returncode,
            "response": response.strip(),
            "error": "" if result.returncode == 0 else (result.stderr or result.stdout)[-2000:],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--evals", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--codex", default=shutil.which("codex") or "codex")
    default_codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    parser.add_argument("--auth-file", type=Path, default=default_codex_home / "auth.json")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--case-id", type=int, action="append")
    args = parser.parse_args()

    skill_dir = args.skill_dir.resolve()
    if not (skill_dir / "SKILL.md").is_file():
        parser.error("skill-dir must contain SKILL.md")
    if not args.auth_file.is_file():
        parser.error("auth-file missing")
    payload = json.loads(args.evals.read_text())
    cases = payload.get("evals", [])
    if args.case_id:
        selected = set(args.case_id)
        cases = [case for case in cases if case["id"] in selected]
    if args.limit is not None:
        cases = cases[: args.limit]
    if not cases:
        parser.error("no eval cases")

    results = []
    for case in cases:
        prompt = case["prompt"]
        results.append(
            {
                "id": case["id"],
                "prompt": prompt,
                "expected_output": case["expected_output"],
                "baseline": run_arm(args.codex, args.auth_file, skill_dir, prompt, args.model, "baseline"),
                "skill": run_arm(args.codex, args.auth_file, skill_dir, prompt, args.model, "skill"),
            }
        )

    report = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "skill": skill_dir.name,
        "model": args.model,
        "isolation": "temporary HOME; baseline has no self-owned skills; treatment mounts only target skill",
        "cases": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if all(arm["returncode"] == 0 for case in results for arm in (case["baseline"], case["skill"])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
