#!/usr/bin/env python3
import json, os, sys, subprocess
from pathlib import Path

BUG_ROOT = Path("/media/yhr/2T/yunxiao/bugs")

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw).stdout.strip()

def check_git_branch(expected):
    actual = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    ok = actual == expected
    return ok, f"branch: expected={expected} actual={actual}" + (" OK" if ok else " FAIL")

def check_file(p, label):
    ok = p.exists() and p.stat().st_size > 0
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")

def check_state_json(p):
    if not p.exists():
        return False, "state.json: missing FAIL"
    try:
        d = json.loads(p.read_text())
        # Gate must verify Intake completed — only accept intake phase
        ok = d.get("phase") == "intake" and bool(d.get("title"))
        return ok, f"state.json: phase={d.get('phase','EMPTY')}" + (" OK" if ok else " FAIL (expected phase=intake)")
    except Exception as e:
        return False, f"state.json: error {e} FAIL"

def check_fix_plan_json(p):
    if not p.exists():
        return False, "fix_plan.json: missing FAIL"
    try:
        d = json.loads(p.read_text())
        rc = d.get("root_cause", {})
        fp = d.get("fix_plan", {})
        has_hypothesis = bool(rc.get("hypothesis"))
        has_files = bool(fp.get("modified_files"))
        
        # Schema gate rules: speculative → blocked, blocking uncertainty → blocked
        confidence = rc.get("confidence", "")
        if confidence == "speculative":
            return False, f"fix_plan.json: confidence=speculative FAIL (must confirm root cause)"
        
        uncertainties = d.get("uncertainties", [])
        blocking = [u for u in uncertainties if u.get("impact") == "blocking"]
        if blocking:
            return False, f"fix_plan.json: {len(blocking)} blocking uncertainty(s) FAIL (resolve before Fix)"
        
        ok = has_hypothesis and has_files
        return ok, f"fix_plan.json: root_cause={'OK' if has_hypothesis else 'EMPTY'} files={'OK' if has_files else 'EMPTY'} confidence={confidence}" + (" OK" if ok else " FAIL")
    except Exception as e:
        return False, f"fix_plan.json: error {e} FAIL"

def check_worktree_clean():
    """Verify git worktree is clean — no unstaged or staged changes."""
    unstaged = subprocess.run(["git", "diff", "--quiet"], capture_output=True).returncode != 0
    staged = subprocess.run(["git", "diff", "--cached", "--quiet"], capture_output=True).returncode != 0
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

    bug_dir = BUG_ROOT / args.bug_id
    repo = Path(args.repo)
    prop = repo / ".proposal" / "repair" / args.bug_id

    sp = bug_dir / "state.json"
    try:
        state = json.loads(sp.read_text()) if sp.exists() else {}
    except Exception:
        state = {}

    branch = state.get("fix_branch") or state.get("base_branch") or run(["git", "rev-parse", "--abbrev-ref", "HEAD"])

    checks = []
    checks.append(("0.worktree", check_worktree_clean()))
    checks.append(("1.context-loaded", check_state_json(sp)))
    checks.append(("2.branch", check_git_branch(branch)))
    checks.append(("3.analyzed", check_fix_plan_json(prop / "fix_plan.json")))
    checks.append(("4.fix_plan.md", check_file(prop / "fix_plan.md", "fix_plan.md")))
    checks.append(("5.breach", check_file(prop / "index.html", "Breach HTML")))
    checks.append(("6.yunxiao-status", (False, "yunxiao-status: SKIPPED — needs MCP auth")))
    checks.append(("7.owner", (False, "owner-check: SKIPPED — needs MCP auth")))
    checks.append(("8.state.json", check_state_json(sp)))
    checks.append(("9.canon", check_canon(Path(f"/media/yhr/2T/Canon/tasks/{args.bug_id}.md"), args.bug_id)))

    # Fix: "3" must be in hard — fix_plan.json is Fix's primary source
    hard = {"0","2","3","4","5","8","9"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    warns = [c for c in checks if c[0].split(".")[0] not in hard and c[0].split(".")[0] not in ("6","7") and not c[1][0]]

    if fails:
        verdict = "blocked"
    elif warns:
        verdict = "warn"
    else:
        verdict = "pass"

    if args.json:
        out = {"verdict": verdict, "bug_id": args.bug_id, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}
        print(json.dumps(out, indent=2, ensure_ascii=False))
    else:
        print(f"Intake Gate: {verdict.upper()}")
        for n, (ok, msg) in checks:
            print(f"  [{n}] {msg}")

    gate_path = prop / "intake_gate.json"
    gate_path.parent.mkdir(parents=True, exist_ok=True)
    gate = {"verdict": verdict, "bug_id": args.bug_id, "checks": {n: {"ok": ok, "msg": msg} for n, (ok, msg) in checks}}
    gate_path.write_text(json.dumps(gate, indent=2, ensure_ascii=False))
    print(f"\nintake_gate.json -> {gate_path}", file=sys.stderr)
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
