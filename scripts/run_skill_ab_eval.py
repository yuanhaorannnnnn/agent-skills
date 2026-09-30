#!/usr/bin/env python3
"""Run isolated baseline-vs-skill Codex responses for existing eval cases."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time
import hashlib
from datetime import datetime, timezone
from pathlib import Path


def fixture_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError("fixture paths must stay inside workdir")
    return path


def check_artifacts(workdir: Path, checks: list[dict]) -> list[dict]:
    results = []
    for check in checks:
        try:
            path = fixture_path(workdir, check["path"])
            content = path.read_text() if path.is_file() else None
            passed = content is not None
            if "equals" in check:
                passed = content == check["equals"]
            if "contains" in check:
                passed = passed and check["contains"] in (content or "")
            if check.get("absent"):
                passed = not path.exists()
            results.append({"check": check, "passed": passed, "content": content})
        except (ValueError, OSError, UnicodeError):
            results.append({"check": check, "passed": False, "content": None, "error": "invalid_artifact"})
    return results


def run_arm(
    codex: Path,
    auth_file: Path,
    skill_dir: Path,
    prompt: str,
    model: str,
    arm: str,
    case: dict | None = None,
    timeout: int = 240,
) -> dict:
    with tempfile.TemporaryDirectory(prefix=f"skill-ab-{arm}-") as tmp:
        root = Path(tmp)
        isolated_home = root / "home"
        isolated_codex = isolated_home / ".codex"
        workdir = root / "work"
        output = root / "response.txt"
        isolated_codex.mkdir(parents=True)
        workdir.mkdir()
        case = case or {}
        for name, content in case.get("fixtures", {}).items():
            path = fixture_path(workdir, name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        # Both arms share the same workspace boundary; no real project writes.
        (workdir / "AGENTS.md").write_text(
            "This is an isolated eval fixture. Work only inside this directory. "
            "Do not write to Canon, real repositories, or external services. "
            "Do not send email, commit, push, or delegate. Missing evidence must be disclosed.\n"
        )
        (isolated_codex / "auth.json").symlink_to(auth_file)

        arm_prompt = prompt
        if arm == "skill":
            skills_root = isolated_home / ".agents" / "skills"
            skills_root.mkdir(parents=True)
            (skills_root / skill_dir.name).symlink_to(skill_dir, target_is_directory=True)
            shared = skill_dir.parent.parent / "references"
            if shared.is_dir():
                (skills_root / "references").symlink_to(shared, target_is_directory=True)
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
            "--json",
            "-c",
            'model_reasoning_effort="medium"',
            "-s",
            case.get("sandbox", "read-only"),
            "-o",
            str(output),
            "-",
        ]
        started = time.monotonic()
        try:
            process = subprocess.Popen(
                command, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, text=True, start_new_session=os.name == "posix",
            )
        except OSError:
            returncode, stdout, error = 127, "", "codex_launch_failed"
        else:
            with process:
                try:
                    stdout, _ = process.communicate(input=arm_prompt, timeout=timeout)
                    returncode = process.returncode
                    error = "" if returncode == 0 else "codex_exec_failed"
                except subprocess.TimeoutExpired:
                    # Kill descendants too: a timed-out CLI must not outlive its fixture.
                    if os.name == "posix":
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    else:
                        process.kill()
                    stdout, _ = process.communicate()
                    returncode, error = 124, "timeout"
        usage = None
        command_executions = []
        for line in stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            item = event.get("item", {})
            if event.get("type") == "item.completed" and item.get("type") == "command_execution":
                command_executions.append({"command": item.get("command"), "exit_code": item.get("exit_code")})
            if event.get("type") == "turn.completed":
                usage = event.get("usage")
        response = output.read_text(errors="replace") if output.exists() else ""
        if returncode == 0 and not response.strip():
            returncode, error = 65, "empty_response"
        checks = check_artifacts(workdir, case.get("checks", []))
        return {
            "returncode": returncode,
            "response": response.strip(),
            "error": error,
            "elapsed_seconds": round(time.monotonic() - started, 3),
            "usage": usage,
            "cost": None,
            "command_executions": command_executions,
            "artifacts": {c["check"]["path"]: c["content"] for c in checks if c["content"] is not None},
            "artifact_checks": checks,
            "artifact_pass": all(c["passed"] for c in checks) if checks else None,
            "behavior_pass": None,
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--evals", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", default="gpt-6.1-sol")
    parser.add_argument("--codex", default=shutil.which("codex") or "codex")
    default_codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    parser.add_argument("--auth-file", type=Path, default=default_codex_home / "auth.json")
    parser.add_argument("--timeout", type=int, default=240)
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

    if args.timeout <= 0:
        parser.error("timeout must be positive")
    results = []
    for case in cases:
        prompt = case["prompt"]
        results.append(
            {
                "id": case["id"],
                "prompt": prompt,
                "expected_output": case["expected_output"],
                "baseline": run_arm(args.codex, args.auth_file, skill_dir, prompt, args.model, "baseline", case, args.timeout),
                "skill": run_arm(args.codex, args.auth_file, skill_dir, prompt, args.model, "skill", case, args.timeout),
            }
        )
        report = {
            "schema_version": 2,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "skill": skill_dir.name,
            "model": args.model,
            "reasoning_effort": "medium",
            "eval_sha256": hashlib.sha256(args.evals.read_bytes()).hexdigest(),
            "isolation": "temporary HOME/CODEX_HOME/workdir; only target skill mounted; sandboxed CLI, not a host security boundary",
            "cases": results,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))

    return 0 if all(arm["returncode"] == 0 for case in results for arm in (case["baseline"], case["skill"])) else 1


if __name__ == "__main__":
    raise SystemExit(main())
