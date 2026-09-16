#!/usr/bin/env python3
"""Validate Execute persistence, routing records, and one-level delegation."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


def check_file(path: Path | None, label: str) -> tuple[bool, str]:
    ok = path is not None and path.exists() and path.stat().st_size > 50
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")


def read(path: Path | None) -> str:
    return path.read_text(encoding="utf-8", errors="replace") if path and path.exists() else ""


def section(text: str, name: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(name)}\s*$\n?(.*?)(?=^## |\Z)", text)
    return match.group(1) if match else ""


def fields(text: str) -> dict[str, str]:
    return {
        key: value.strip()
        for key, value in re.findall(r"(?m)^\s*-\s*([a-z_]+):\s*(.+?)\s*$", text)
    }


def check_task_structure(path: Path) -> tuple[bool, str]:
    required = ("## Goal", "## Current State", "## Next Step", "## Tasks", "## Progress")
    missing = [heading for heading in required if heading not in read(path)]
    ok = not missing
    detail = "complete" if ok else f"missing={','.join(missing)}"
    return ok, f"Canon task structure: {detail}" + (" OK" if ok else " FAIL")


def check_goal_structure(path: Path | None) -> tuple[bool, str]:
    text = read(path)
    has_goal = "## 目标" in text or "## Goal" in text
    has_tasks = "## 任务清单" in text or "## Tasks" in text or "- [ ]" in text
    ok = has_goal and has_tasks
    return ok, f"goal.md: goal={'OK' if has_goal else 'MISSING'} tasks={'OK' if has_tasks else 'MISSING'}" + (" OK" if ok else " FAIL")


def check_routing(path: Path, requested_route: str, current_depth: int) -> tuple[bool, str]:
    values = fields(section(read(path), "Routing"))
    required = (
        "routing_mode", "resolved_route", "reason", "router_owner", "delegation_depth",
        "downstream_auto_delegate", "models", "scope", "status", "evidence",
    )
    missing = [key for key in required if not values.get(key)]
    if missing:
        return False, f"Routing: missing={','.join(missing)} FAIL"
    mode = values["routing_mode"]
    resolved = values["resolved_route"]
    try:
        recorded_depth = int(values["delegation_depth"])
    except ValueError:
        return False, "Routing: delegation_depth must be an integer FAIL"
    expected_resolved = {"direct": "direct", "delegate": "delegate"}.get(requested_route, resolved)
    expected_depth = current_depth + (1 if expected_resolved == "delegate" else 0)
    ok = (
        mode == requested_route
        and resolved in {"direct", "delegate"}
        and expected_resolved == resolved
        and recorded_depth == expected_depth
        and recorded_depth <= 1
        and "main" in values["router_owner"].lower()
        and "execute" in values["router_owner"].lower()
        and values["downstream_auto_delegate"].lower() == "forbidden"
        and not (current_depth >= 1 and requested_route == "auto" and resolved == "delegate")
    )
    detail = f"mode={mode} resolved={resolved} depth={recorded_depth} owner={values['router_owner']}"
    return ok, f"Routing: {detail}" + (" OK" if ok else " FAIL")


def check_delegation(path: Path) -> tuple[bool, str]:
    values = fields(section(read(path), "Delegation"))
    required = ("executor", "scope", "status", "evidence")
    missing = [key for key in required if not values.get(key)]
    ok = not missing
    return ok, "Delegation: complete" + (" OK" if ok else f" missing={','.join(missing)} FAIL")


def resolve_route(parser: argparse.ArgumentParser, args: argparse.Namespace) -> tuple[str, str]:
    if args.direct and args.delegate:
        parser.error("--direct and --delegate are mutually exclusive")
    forced = "direct" if args.direct else "delegate" if args.delegate else None
    if args.route and forced and args.route != forced:
        parser.error("--route conflicts with explicit --direct/--delegate")
    route = forced or args.route or ("direct" if args.mode == "direct" else "auto")
    persistence = "none" if args.mode in {None, "direct", "none"} else args.mode
    if args.delegation_depth < 0 or args.delegation_depth > 1:
        parser.error("--delegation-depth must be 0 or 1")
    if args.delegation_depth >= 1 and route == "delegate":
        parser.error("delegation depth 1 cannot delegate again")
    return persistence, route


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("none", "direct", "goal", "plan"))
    parser.add_argument("--route", choices=("auto", "direct", "delegate"))
    parser.add_argument("--direct", action="store_true")
    parser.add_argument("--delegate", action="store_true")
    parser.add_argument("--delegation-depth", type=int, default=0)
    parser.add_argument("--goal", type=Path)
    parser.add_argument("--task", type=Path, required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    mode, route = resolve_route(parser, args)
    checks = [
        ("1.task-file", check_file(args.task, "Canon task page")),
        ("2.task-structure", check_task_structure(args.task)),
        ("3.routing", check_routing(args.task, route, args.delegation_depth)),
    ]
    if mode in {"goal", "plan"}:
        checks.extend([
            ("4.goal-file", check_file(args.goal, "goal.md")),
            ("5.goal-structure", check_goal_structure(args.goal)),
        ])
    if mode == "plan":
        checks.append(("6.plan", ("## Plan" in read(args.task), "Plan: present")))
    if route == "delegate" or (route == "auto" and "resolved_route: delegate" in section(read(args.task), "Routing")):
        checks.append(("7.delegation", check_delegation(args.task)))
    failed = [f"{name} {message}" for name, (ok, message) in checks if not ok]
    verdict = "blocked" if failed else "pass"
    result = {"verdict": verdict, "mode": mode, "route": route, "failed": failed}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"Execute Gate: {verdict.upper()} ({mode}+{route})")
        for name, (_, message) in checks:
            print(f"  [{name}] {message}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
