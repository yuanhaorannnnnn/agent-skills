#!/usr/bin/env python3
"""Closeout gate checker — verifies the defect was cleanly closed.

Usage:
  python3 closeout_gate.py <bug-id> [--repo <path>] [--json]
"""

import json, os, sys, subprocess, urllib.request
from pathlib import Path

BUG_ROOT = Path("/media/yhr/2T/yunxiao/bugs")

OUTCOME_STATUS_MAP = {
    "fixed": "集成测试中",
    "false-positive": "关闭",
    "requirement": "转需求",
    "cannot-reproduce": "开发挂起",
    "blocked": "开发挂起",
}

def check_state_outcome(sp):
    if not sp.exists():
        return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        outcome = d.get("outcome", "")
        status = d.get("status", "")
        if not outcome or not status:
            return False, f"state.json: outcome={outcome or 'EMPTY'} status={status or 'EMPTY'} FAIL"
        expected_status = OUTCOME_STATUS_MAP.get(outcome)
        if expected_status and status != expected_status:
            return False, f"state.json: outcome={outcome} → status={status} FAIL (expected {expected_status})"
        ok = bool(outcome) and bool(status)
        return ok, f"state.json: outcome={outcome} status={status}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"state.json: error {e} FAIL"

def check_phase(sp):
    if not sp.exists():
        return False, "state.json: missing FAIL"
    try:
        d = json.loads(sp.read_text())
        phase = d.get("phase", "")
        outcome = d.get("outcome", "")
        if outcome == "fixed" and phase != "integration":
            return False, f"phase: fixed outcome requires phase=integration, got {phase or 'EMPTY'} FAIL"
        ok = phase in ("integration", "regression", "requirement", "closed", "suspended", "fixed", "done")
        return ok, f"phase: {phase or 'EMPTY'}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"phase: error {e} FAIL"

def check_deliverable_urls(sp):
    """Verify deliverable URLs are reachable. Only required for fixed outcome."""
    if not sp.exists():
        return False, "deliverable: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        if d.get("outcome") != "fixed":
            return True, "deliverable: skipped (not fixed outcome) OK"
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


def check_comment_evidence(sp):
    """comment_ids or --comment evidence exists."""
    if not sp.exists():
        return False, "comment: state.json missing FAIL"
    try:
        d = json.loads(sp.read_text())
        has_comment_ids = bool(d.get("comment_ids"))
        return has_comment_ids, f"comment: comment_ids={'present' if has_comment_ids else 'EMPTY'}" + (" OK" if has_comment_ids else " FAIL (verify comment was actually posted)")
    except Exception as e:
        return False, f"comment: error {e} FAIL"

def check_owner_unchanged(sp, bug_id):
    """Compare current assignee with original. SKIPPED offline."""
    return False, "owner: SKIPPED — MCP auth required, verify manually"

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
    checks.append(("1.phase", check_phase(sp)))
    checks.append(("2.state-outcome", check_state_outcome(sp)))
    checks.append(("3.comment", check_comment_evidence(sp)))
    checks.append(("3b.deliverable", check_deliverable_urls(sp)))
    checks.append(("4.owner", check_owner_unchanged(sp, args.bug_id)))
    checks.append(("5.canon", check_canon(canon_task, args.bug_id)))

    hard = {"0", "1", "2", "3", "3b", "5"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]

    if fails:
        verdict = "blocked"
    else:
        verdict = "pass"

    if args.json:
        out = {"verdict": verdict, "bug_id": args.bug_id, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"Closeout Gate: {verdict.upper()}")
        for n, (ok, msg) in checks:
            print(f"  [{n}] {msg}")

    # Write to Intake's gate file (same location), or in absence, to proposal dir
    prop = repo / ".proposal" / "repair" / args.bug_id
    gate_path = prop / "closeout_gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate = {"verdict": verdict, "bug_id": args.bug_id, "checks": {n: {"ok": ok, "msg": msg} for n, (ok, msg) in checks}}
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False))
    print(f"\ncloseout_gate.json -> {gate_path}", file=sys.stderr)
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
