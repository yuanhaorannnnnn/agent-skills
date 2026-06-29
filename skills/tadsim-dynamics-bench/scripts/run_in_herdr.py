#!/usr/bin/env python3
"""Run a CarSim-TadSim benchmark case in a herdr carla-client pane."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

REPO = Path("/media/yhr/2T/CarlaUE5")
RUNNER = "PythonAPI/test/validation/tadsim/run_carsim_tadsim_case.py"


def run_json(cmd: List[str]) -> Dict[str, Any]:
    result = subprocess.run(cmd, text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def run_text(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, check=check)


def find_pane(target: str) -> str:
    data = run_json(["herdr", "pane", "list"])
    panes = data.get("result", {}).get("panes", [])
    for pane in panes:
        if pane.get("pane_id") == target or pane.get("label") == target:
            return pane["pane_id"]
    labels = [f"{p.get('pane_id')} label={p.get('label')} cwd={p.get('foreground_cwd') or p.get('cwd')}" for p in panes]
    raise SystemExit("target pane not found: " + target + "\n" + "\n".join(labels))


def shell_join(parts: List[str]) -> str:
    return " ".join(shlex.quote(str(p)) for p in parts)


def build_repo_command(args: argparse.Namespace) -> str:
    cmd = ["python3", RUNNER, "--case", args.case]
    if args.reference_dir:
        cmd.extend(["--reference-dir", args.reference_dir])
    if args.reference_csv:
        cmd.extend(["--reference-csv", args.reference_csv])
    if args.output_dir:
        cmd.extend(["--output-dir", args.output_dir])
    if args.dry_run:
        cmd.append("--dry-run")
    return f"cd {shlex.quote(str(REPO))} && {shell_join(cmd)}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True, help="Benchmark case key, e.g. M1 or M2")
    parser.add_argument("--reference-dir", default=None, help="CarSim Run directory override")
    parser.add_argument("--reference-csv", default=None, help="CarSim LastRun.csv override")
    parser.add_argument("--output-dir", default=None, help="Output directory override")
    parser.add_argument("--client-pane", default="carla-client", help="herdr pane label or pane id")
    parser.add_argument("--timeout-ms", type=int, default=600000)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    if os.environ.get("HERDR_ENV") != "1":
        raise SystemExit("HERDR_ENV is not 1; run this from inside herdr or use the repo runner directly")

    args = parse_args()
    pane = find_pane(args.client_pane)
    command = build_repo_command(args)
    token_prefix = "__TADSIM_BENCH_DONE_"
    token_suffix = f"{uuid4().hex}__"
    token = token_prefix + token_suffix
    wrapped = (
        f"__tadsim_bench_token_a={shlex.quote(token_prefix)}; "
        f"__tadsim_bench_token_b={shlex.quote(token_suffix)}; "
        f"{command}; rc=$?; "
        'echo "${__tadsim_bench_token_a}${__tadsim_bench_token_b}:$rc"'
    )

    print(json.dumps({"pane": pane, "command": command, "wait_marker": token}, indent=2))
    run_text(["herdr", "pane", "run", pane, wrapped])
    wait = run_text(["herdr", "wait", "output", pane, "--match", token, "--timeout", str(args.timeout_ms)], check=False)
    if wait.returncode != 0:
        recent = run_text(["herdr", "pane", "read", pane, "--source", "recent-unwrapped", "--lines", "120"], check=False)
        print(recent.stdout)
        if recent.stderr:
            print(recent.stderr, file=sys.stderr)
        raise SystemExit(wait.returncode)

    recent = run_text(["herdr", "pane", "read", pane, "--source", "recent-unwrapped", "--lines", "120"], check=False)
    print(recent.stdout)
    marker_prefix = f"{token}:"
    for line in reversed(recent.stdout.splitlines()):
        if marker_prefix in line:
            value = line.split(marker_prefix, 1)[1].strip().split()[0]
            try:
                rc = int(value)
            except ValueError as exc:
                raise SystemExit(f"invalid benchmark exit marker: {line}") from exc
            if rc != 0:
                raise SystemExit(rc)
            return
    raise SystemExit("benchmark exit marker was observed by wait but not found in recent output")


if __name__ == "__main__":
    main()
