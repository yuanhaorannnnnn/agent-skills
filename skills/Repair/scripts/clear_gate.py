#!/usr/bin/env python3
"""Clear gate checker — verifies merge + build + close are complete.

Usage:
  python3 clear_gate.py <bug-id> [--repo <path>] [--json]
"""

import json, os, sys, subprocess, urllib.request
from pathlib import Path

BUG_ROOT = Path("/media/yhr/2T/yunxiao/bugs")


def check_state_cleared(sp):
    if not sp.exists():
        return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        phase = d.get("phase", "")
        status = d.get("status", "")
        ok = phase == "done" and status == "关闭"
        return ok, f"state: phase={phase or 'EMPTY'} status={status or 'EMPTY'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"state: error {e} FAIL"


def check_merge_commit(sp):
    if not sp.exists():
        return False, "merge: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        sha = d.get("merge_commit_sha", "")
        ok = bool(sha)
        return ok, f"merge: commit={'present' if ok else 'MISSING'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"merge: error {e} FAIL"


def check_build_artifact(sp):
    if not sp.exists():
        return False, "build: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        art = d.get("clear_build_artifact", "")
        ok = bool(art)
        return ok, f"build: artifact={'present' if ok else 'MISSING'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"build: error {e} FAIL"


def check_deliverable_urls(sp):
    if not sp.exists():
        return False, "deliverable: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        urls = d.get("deliverable_urls", [])
        if not urls:
            return False, "deliverable: no deliverable_urls FAIL"
        unreachable = []
        for url in urls:
            try:
                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status >= 400:
                        unreachable.append(f"{url} (HTTP {resp.status})")
            except Exception as e:
                unreachable.append(f"{url} ({e})")
        if unreachable:
            return False, f"deliverable: {len(unreachable)}/{len(urls)} unreachable: {unreachable[0]} FAIL"
        return True, f"deliverable: {len(urls)} url(s) reachable OK"
    except Exception as e:
        return False, f"deliverable: error {e} FAIL"


def check_worktree_clean(repo):
    """Verify git worktree is clean — no unstaged or staged changes."""
    cwd = str(repo)
    unstaged = subprocess.run(["git", "-C", cwd, "diff", "--quiet"], capture_output=True).returncode != 0
    staged = subprocess.run(["git", "-C", cwd, "diff", "--cached", "--quiet"], capture_output=True).returncode != 0
    ok = not unstaged and not staged
    parts = []
    if unstaged:
        parts.append("unstaged changes")
    if staged:
        parts.append("staged changes")
    msg = f"worktree: {'clean' if ok else ', '.join(parts)}" + (" OK" if ok else " FAIL")
    return ok, msg

def check_canon(task_path, bug_id):
    ok = task_path.exists()
    return ok, f"Canon task: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("bug_id")
    ap.add_argument("--repo", default=os.getcwd())
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    sp = BUG_ROOT / args.bug_id / "state.json"
    canon_task = Path(f"/media/yhr/2T/Canon/tasks/{args.bug_id}.md")
    repo = Path(args.repo)

    checks = []
    checks.append(("0.worktree", check_worktree_clean(repo)))
    checks.append(("1.state", check_state_cleared(sp)))
    checks.append(("2.merge", check_merge_commit(sp)))
    checks.append(("3.build", check_build_artifact(sp)))
    checks.append(("4.deliverable", check_deliverable_urls(sp)))
    checks.append(("5.canon", check_canon(canon_task, args.bug_id)))

    hard = {"0", "1", "2", "3", "4", "5"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]

    verdict = "blocked" if fails else "pass"

    if args.json:
        out = {"verdict": verdict, "bug_id": args.bug_id,
               "failed": [f"{n} {m}" for n, m in checks if not m[0]]}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"Clear Gate: {verdict.upper()}")
        for n, (ok, msg) in checks:
            print(f"  [{n}] {msg}")

    prop = repo / ".proposal" / "repair" / args.bug_id
    gate_path = prop / "clear_gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate = {"verdict": verdict, "bug_id": args.bug_id,
            "checks": {n: {"ok": ok, "msg": msg} for n, (ok, msg) in checks}}
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False))
    print(f"\nclear_gate.json -> {gate_path}", file=sys.stderr)
    sys.exit(0 if verdict != "blocked" else 1)


if __name__ == "__main__":
    main()
