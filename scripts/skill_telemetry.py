#!/usr/bin/env python3
"""Append one privacy-safe local skill outcome event as JSONL."""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_PATH = Path.home() / ".agents" / "skill-telemetry" / "events.jsonl"
OUTCOMES = ("pass", "blocked", "skipped", "error")
TRIGGERS = ("explicit", "implicit", "workflow")
RUNTIMES = ("codex", "claude", "pi", "kimi", "other")
ENTRIES = ("skill-name", "natural-language", "caller", "unknown")
# Closed vocabulary: never accept a prompt, source title, or arbitrary reason.
ROUTES = {
    "breach": ("general-page", "discussion-digest", "native-handoff", "inline-answer", "unresolved"),
    "acquisition": ("article", "wechat-article", "wechat-album", "video", "pdf", "clippings", "local-markdown", "chart-handoff", "deduplicated", "unresolved"),
    "execute": ("direct", "delegate", "unresolved"),
    "sanitize": ("closeout", "report", "both", "unresolved"),
}
DECISIONS = {
    "breach": {
        "content-profile": ("default", "eli5"),
        "prose": ("author", "faithful"),
        "style": ("project-design", "selected-design", "awesome-design", "digest-template", "none"),
        "charts": ("lieflat", "native", "omit", "unavailable"),
        "hairline": ("embed", "static", "omit", "unavailable"),
    },
    "acquisition": {
        "identity": ("new", "complete", "raw-only", "incomplete", "changed", "weak"),
        "delivery": ("raw-query", "raw-only", "handoff", "reuse"),
        "fetch": ("direct", "jina", "wechat-cli", "youtube", "x-download", "local", "none"),
    },
    "execute": {
        "requested": ("auto", "direct", "delegate"),
        "persistence": ("local", "task", "goal", "plan"),
    },
    "sanitize": {"publish": ("none", "commit", "push")},
}
STEPS = {
    "breach": ("paperwork", "layout", "style", "render", "charts", "hairline", "visual-check"),
    "acquisition": ("identity", "archive", "paperwork", "query", "index-log", "catalog", "handoff"),
    "execute": ("implementation", "delegation", "validation", "review", "execution-gate"),
    "sanitize": ("report", "report-gate", "review", "commit", "push", "canon"),
}
STEP_STATES = (*OUTCOMES, "pending")


def routing_fields(args: argparse.Namespace) -> dict:
    if not any((args.entry, args.route, args.expected_route, args.decision, args.step)):
        return {}
    routes = ROUTES.get(args.skill, ())
    if args.route not in routes or (args.expected_route is not None and args.expected_route not in routes):
        raise ValueError("routing requires a supported skill and an allowed route")

    def pairs(values, allowed):
        result = {}
        for item in values or []:
            key, sep, value = item.partition("=")
            if not sep or key not in allowed or value not in allowed[key] or key in result:
                raise ValueError("invalid or duplicate routing field")
            result[key] = value
        return result

    return {
        "entry": args.entry or "unknown",
        "route": args.route,
        "expected_route": args.expected_route,
        "route_match": None if args.expected_route is None else args.route == args.expected_route,
        "decisions": pairs(args.decision, DECISIONS[args.skill]),
        "steps": pairs(args.step, {key: STEP_STATES for key in STEPS[args.skill]}),
    }


def report_events(path: Path, skill: str | None, start: datetime | None = None,
                  end: datetime | None = None) -> dict:
    counts, routes, mismatches, steps = Counter(), Counter(), Counter(), Counter()
    entries, decisions = Counter(), Counter()
    unknown_expectations = invalid_lines = invalid_timestamps = 0
    if path.exists():
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError("not an event")
                except (ValueError, TypeError):
                    invalid_lines += 1
                    continue
                name = event.get("skill")
                if skill and name != skill:
                    continue
                # Output only known metadata, never arbitrary legacy fields.
                if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", name):
                    invalid_lines += 1
                    continue
                if start is not None or end is not None:
                    try:
                        timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                        if timestamp.tzinfo is None:
                            raise ValueError("timestamp needs timezone")
                    except (KeyError, ValueError, TypeError, AttributeError):
                        invalid_timestamps += 1
                        continue
                    if (start is not None and timestamp < start) or (end is not None and timestamp >= end):
                        continue
                outcome = event.get("outcome")
                if outcome not in OUTCOMES:
                    invalid_lines += 1
                    continue
                counts[f"{name}:{outcome}"] += 1
                route = event.get("route")
                if route not in ROUTES.get(name, ()):
                    route = "unobserved"
                routes[f"{name}:{route}"] += 1
                entry = event.get("entry")
                if entry in ENTRIES:
                    entries[f"{name}:{entry}"] += 1
                observed_decisions = event.get("decisions", {})
                if isinstance(observed_decisions, dict):
                    for key, value in observed_decisions.items():
                        if key in DECISIONS.get(name, {}) and value in DECISIONS[name][key]:
                            decisions[f"{name}:{key}:{value}"] += 1
                expected = event.get("expected_route")
                if expected in ROUTES.get(name, ()) and route != "unobserved":
                    if expected != route:
                        mismatches[f"{name}:{expected}->{route}"] += 1
                else:
                    unknown_expectations += 1
                observed_steps = event.get("steps", {})
                if isinstance(observed_steps, dict):
                    for step, state in observed_steps.items():
                        if step in STEPS.get(name, ()) and state in STEP_STATES:
                            steps[f"{name}:{step}:{state}"] += 1
    return {"outcomes": dict(counts), "routes": dict(routes), "mismatches": dict(mismatches),
            "entries": dict(entries), "decisions": dict(decisions), "steps": dict(steps), "unknown_expectations": unknown_expectations, "invalid_lines": invalid_lines, "invalid_timestamps": invalid_timestamps}


def build_event(args: argparse.Namespace) -> dict:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", args.skill):
        raise ValueError("skill must be a manifest-style name")
    if args.duration_ms is not None and args.duration_ms < 0:
        raise ValueError("duration-ms must be non-negative")
    routing = routing_fields(args)
    return {
        "schema_version": 2 if routing else 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "skill": args.skill,
        "runtime": args.runtime,
        "trigger": args.trigger,
        "outcome": args.outcome,
        "duration_ms": args.duration_ms,
        "artifacts": args.artifact or [],
        "gate": args.gate,
        **routing,
    }


def append_event(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        stream.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", type=Path, default=Path(os.environ.get("SKILL_TELEMETRY_PATH", DEFAULT_PATH)))
    parser.add_argument("--skill")
    parser.add_argument("--runtime", choices=RUNTIMES)
    parser.add_argument("--trigger", choices=TRIGGERS)
    parser.add_argument("--outcome", choices=OUTCOMES)
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--artifact", action="append")
    parser.add_argument("--gate")
    parser.add_argument("--entry", choices=ENTRIES)
    parser.add_argument("--route")
    parser.add_argument("--expected-route")
    parser.add_argument("--decision", action="append", metavar="KEY=VALUE")
    parser.add_argument("--step", action="append", metavar="NAME=STATE")
    parser.add_argument("--report", action="store_true", help="read-only aggregate, optionally filtered by --skill")
    args = parser.parse_args()
    if args.report:
        print(json.dumps(report_events(args.path, args.skill), ensure_ascii=False, indent=2))
        return 0
    if not all((args.skill, args.runtime, args.trigger, args.outcome)):
        parser.error("recording requires --skill, --runtime, --trigger, --outcome")
    try:
        event = build_event(args)
    except ValueError as exc:
        parser.error(str(exc))
    append_event(args.path, event)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
