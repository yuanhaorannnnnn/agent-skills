#!/usr/bin/env python3
"""Sanitize gate — verify commit, push, and Canon update completed.

Usage:
  python3 wrapup_gate.py --task <canon-task-path> --repo <path> [--json]
"""

import json, os, sys, subprocess
from pathlib import Path

def run(cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd).stdout.strip()

def check_commit_exists(repo):
    log = run(["git", "log", "--oneline", "-1"], cwd=repo)
    ok = len(log) > 0
    return ok, f"commit: {'exists' if ok else 'NONE'}" + (" OK" if ok else " FAIL")

def check_push_status(repo):
    """Check if local branch is ahead/behind remote."""
    branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo)
    ahead = run(["git", "rev-list", "--count", f"origin/{branch}..HEAD"], cwd=repo)
    ok = ahead == "0"
    return ok, f"push: {'synced' if ok else f'{ahead} commit(s) ahead — not pushed'}" + (" OK" if ok else " FAIL")

def check_canon_updated(p):
    if not Path(p).exists():
        return False, "Canon task: missing FAIL"
    text = Path(p).read_text()
    ok = "## Progress" in text and "committed" in text.lower()
    return ok, f"Canon task: {'updated' if ok else '§ Progress missing or no commit ref'}" + (" OK" if ok else " FAIL")

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    checks = [
        ("1.commit", check_commit_exists(args.repo)),
        ("2.push", check_push_status(args.repo)),
        ("3.canon", check_canon_updated(args.task)),
    ]

    hard = {"1","2","3"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Sanitize Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
