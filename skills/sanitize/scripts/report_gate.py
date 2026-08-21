#!/usr/bin/env python3
"""Sanitize report gate — verify a formal report is built from evidence.

Usage:
  python3 report_gate.py <report.md> [--json]
"""

import json, sys
from pathlib import Path

SHARED_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"
if str(SHARED_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SHARED_SCRIPTS))
from accepted_spec import artifact_mode, load_spec  # noqa: E402

REQUIRED_SECTIONS = [
    "Abstract", "Related Work", "Method", "Implementation", "Evaluation", "Conclusion",
]

def check_file(p):
    ok = Path(p).exists() and Path(p).stat().st_size > 200
    return ok, f"file: {'found' if ok else 'missing or too small'}" + (" OK" if ok else " FAIL")

def check_sections(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    missing = []
    for sec in REQUIRED_SECTIONS:
        if sec not in text:
            missing.append(sec)
    ok = len(missing) == 0
    return ok, f"sections: {'all 6' if ok else f'missing: {missing}'}" + (" OK" if ok else " FAIL")

def check_evidence_cited(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    has_canon = "/media/yhr/2T/Canon/tasks/" in text
    has_planning = ".planning/" in text or ".agent-state/" in text
    has_commit = "commit" in text.lower()
    ok = has_canon or has_planning or has_commit
    evidence = []
    if has_canon: evidence.append("Canon task")
    if has_planning: evidence.append("planning/conversation")
    if has_commit: evidence.append("commit ref")
    return ok, f"evidence: {'+'.join(evidence) if evidence else 'NONE cited'}" + (" OK" if ok else " FAIL")


def check_artifact_contract(spec_path=None, mode=None, required=False):
    if required and not mode:
        mode = "delivery"
    if not mode and not required:
        return True, "artifact contract: not requested"
    if mode not in ("delivery", "audit", "knowledge"):
        return False, f"artifact contract: invalid mode {mode!r} FAIL"
    if not spec_path:
        if mode == "delivery" or required:
            return False, "artifact contract: accepted_spec required for delivery FAIL"
        return True, f"artifact contract: {mode} without accepted_spec OK"
    spec, errors = load_spec(spec_path, require_artifact_mode=mode == "delivery")
    if errors:
        return False, "artifact contract: " + "; ".join(errors) + " FAIL"
    declared = artifact_mode(spec)
    if declared != mode:
        return False, f"artifact contract: spec mode={declared!r}, expected {mode!r} FAIL"
    return True, f"artifact contract: {mode} accepted ({spec['spec_hash']}) OK"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("report", nargs="?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--accepted-spec", help="Accepted specification path")
    ap.add_argument("--artifact-mode", choices=("delivery", "audit", "knowledge"))
    ap.add_argument("--require-accepted-spec", action="store_true")
    args = ap.parse_args()

    if not args.report:
        print("usage: source_gate.py <report.md>", file=sys.stderr)
        sys.exit(2)

    checks = [
        ("1.file", check_file(args.report)),
        ("2.sections", check_sections(args.report)),
        ("3.evidence", check_evidence_cited(args.report)),
        (
            "4.artifact-contract",
            check_artifact_contract(
                args.accepted_spec,
                args.artifact_mode,
                args.require_accepted_spec,
            ),
        ),
    ]

    hard = {"1","2","3","4"}
    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"Sanitize Report Gate: {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
