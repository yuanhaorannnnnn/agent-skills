#!/usr/bin/env python3
"""Append one privacy-safe local skill outcome event as JSONL."""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_PATH = Path.home() / ".agents" / "skill-telemetry" / "events.jsonl"
OUTCOMES = ("pass", "blocked", "skipped", "error")
TRIGGERS = ("explicit", "implicit", "workflow")
RUNTIMES = ("codex", "claude", "pi", "kimi", "other")


def build_event(args: argparse.Namespace) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.skill):
        raise ValueError("skill must be a manifest-style name")
    if args.duration_ms is not None and args.duration_ms < 0:
        raise ValueError("duration-ms must be non-negative")
    return {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "skill": args.skill,
        "runtime": args.runtime,
        "trigger": args.trigger,
        "outcome": args.outcome,
        "duration_ms": args.duration_ms,
        "artifacts": args.artifact or [],
        "gate": args.gate,
    }


def append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")))
        stream.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path(os.environ.get("SKILL_TELEMETRY_PATH", DEFAULT_PATH)))
    parser.add_argument("--skill", required=True)
    parser.add_argument("--runtime", required=True, choices=RUNTIMES)
    parser.add_argument("--trigger", required=True, choices=TRIGGERS)
    parser.add_argument("--outcome", required=True, choices=OUTCOMES)
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--artifact", action="append")
    parser.add_argument("--gate")
    args = parser.parse_args()
    try:
        event = build_event(args)
    except ValueError as exc:
        parser.error(str(exc))
    append_event(args.path, event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
