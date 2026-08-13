#!/usr/bin/env python3
"""Engage gate checker — pass/blocked/warn. No human gate (all machine)."""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REQ_ROOT = Path("/media/yhr/2T/yunxiao/requirements")


def check_state_phase(sp):
    if not sp.exists():
        return False, "state.json: missing FAIL"
    try:
        data = json.loads(sp.read_text())
        ok = data.get("phase") in ("dev", "review")
        return ok, (
            f"state.json: phase={data.get('phase', 'EMPTY')}"
            + (" OK" if ok else " FAIL")
        )
    except Exception as exc:
        return False, f"state.json: error {exc} FAIL"


def check_goal_md(sp, repo):
    if not sp.exists():
        return False, "goal.md: state.json missing FAIL"
    try:
        data = json.loads(sp.read_text())
        path = data.get("goal_path", "")
        ok = bool(path) and Path(path).exists()
        return ok, (
            f"goal.md: {'found' if ok else 'missing'}"
            + (" OK" if ok else " FAIL")
        )
    except Exception as exc:
        return False, f"goal.md: error {exc} FAIL"


def check_review_gate(sp):
    if not sp.exists():
        return False, "review: state.json missing FAIL"
    try:
        data = json.loads(sp.read_text())
        verdict = data.get("review_gate", "")
        if verdict == "passed":
            return True, "review: passed OK"
        if verdict == "skipped":
            return True, "review: skipped (exempted) OK"
        if verdict == "blocked":
            return False, "review: blocked FAIL"
        return False, f"review: unknown '{verdict}' FAIL"
    except Exception as exc:
        return False, f"review: error {exc} FAIL"


def check_traceback(repo, demand_id):
    repo = Path(repo).resolve()
    gate_script = (
        Path(__file__).resolve().parents[2]
        / "traceback"
        / "scripts"
        / "traceback_gate.py"
    )
    alignment_dir = repo / ".planning" / demand_id
    if not gate_script.is_file():
        return False, "traceback: gate script missing FAIL"
    result = subprocess.run(
        [
            sys.executable,
            str(gate_script),
            "--dir",
            str(alignment_dir),
            "--repo",
            str(repo),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        detail = (
            result.stderr.strip()
            or result.stdout.strip()
            or "invalid gate output"
        )
        return False, f"traceback: {detail} FAIL"
    verdict = payload.get("verdict")
    ok = result.returncode == 0 and verdict in {"pass", "skipped"}
    details = payload.get("errors") or payload.get("warnings") or []
    suffix = f" ({'; '.join(details[:2])})" if details else ""
    return ok, (
        f"traceback: {verdict or 'unknown'}{suffix}"
        + (" OK" if ok else " FAIL")
    )


def check_yunxiao_status(sp):
    return False, "yunxiao-status: SKIPPED — MCP auth required"


def check_canon(demand_id):
    ok = Path(f"/media/yhr/2T/Canon/tasks/{demand_id}.md").exists()
    return ok, (
        f"Canon task: {'found' if ok else 'missing'}"
        + (" OK" if ok else " FAIL")
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("demand_id")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    sp = REQ_ROOT / args.demand_id / "state.json"
    repo = Path(args.repo).resolve()

    checks = [
        ("1.state", check_state_phase(sp)),
        ("2.goal_md", check_goal_md(sp, repo)),
        ("3.review", check_review_gate(sp)),
        ("4.traceback", check_traceback(repo, args.demand_id)),
        ("5.yunxiao", check_yunxiao_status(sp)),
        ("6.canon", check_canon(args.demand_id)),
    ]

    hard = {"1", "2", "3", "4", "6"}
    fails = [
        check
        for check in checks
        if check[0].split(".")[0] in hard and not check[1][0]
    ]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(
            json.dumps(
                {
                    "verdict": verdict,
                    "demand_id": args.demand_id,
                    "failed": [
                        f"{name} {message}"
                        for name, (ok, message) in checks
                        if not ok
                    ],
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        print(f"Engage Gate: {verdict.upper()}")
        for name, (ok, message) in checks:
            print(f"  [{name}] {message}")

    proposal = repo / ".proposal" / args.demand_id
    gate_path = proposal / "engage_gate.json"
    gate = {
        "verdict": verdict,
        "demand_id": args.demand_id,
        "checks": {
            name: {"ok": ok, "msg": message}
            for name, (ok, message) in checks
        },
    }
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate_path.write_text(
        json.dumps(gate, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nengage_gate.json -> {gate_path}", file=sys.stderr)
    return 0 if verdict != "blocked" else 1


if __name__ == "__main__":
    sys.exit(main())
