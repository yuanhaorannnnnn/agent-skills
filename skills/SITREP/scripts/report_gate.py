#!/usr/bin/env python3
"""SITREP gate — verify checklist or final report against structured evidence.

Usage:
  python3 report_gate.py --mode checklist <checklist-md-or-json> [--json]
  python3 report_gate.py --mode report <report.md> --checklist <checklist-json> [--json]
"""

import json, sys, os
from datetime import datetime, timezone
from pathlib import Path


def _find_checklist_json(md_path: str) -> dict | None:
    """Find and parse the checklist JSON for a given checklist markdown path."""
    meta_dir = Path.home() / ".agents" / "work-reports" / ".checklist"
    path = Path(md_path)
    if path.suffix == ".json" and path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    basename = path.stem
    for candidate in [meta_dir / f"{basename}.json", path.with_suffix(".json")]:
        if candidate.exists():
            try:
                return json.loads(candidate.read_text(encoding="utf-8"))
            except Exception:
                pass
    return None


def _count_task_items(text: str) -> int:
    """Count recognizable task items in markdown text."""
    import re
    count = 0
    for line in text.split("\n"):
        if re.match(r"^(?:[-*]\s+)?\[(?:x| |\-)\]\s+", line.strip()):
            count += 1
        elif re.match(r"^[123]\s+\S", line.strip()):
            count += 1
        elif re.match(r"^(?:✅|⬜|➖)\s+\S", line.strip()):
            count += 1
        elif re.match(r"^#{3,}\s+\d+(?:\.\d+)+\.\s+\S", line.strip()):
            count += 1
    return count


def check_file(p, label):
    ok = Path(p).exists() and Path(p).stat().st_size > 100
    return ok, f"{label}: {'found' if ok else 'missing'}" + (" OK" if ok else " FAIL")


def check_not_empty(p, label):
    count = _count_task_items(Path(p).read_text() if Path(p).exists() else "")
    ok = count > 0
    return ok, f"{label}: {count} task items" + (" OK" if ok else " FAIL (no task items)")


def check_from_canon(p):
    text = Path(p).read_text() if Path(p).exists() else ""
    has_canon = "/media/yhr/2T/Canon/tasks/" in text or "Canon" in text
    return has_canon, f"Canon source: {'present' if has_canon else 'NONE'}" + (" OK" if has_canon else " WARN")


def check_based_on_checklist(report_path: str, checklist_path: str):
    """Structured validation: report must be based on checklist, not fresh scan.

    Uses checklist JSON as the authoritative artifact:
    - Checklist must be confirmed (user approved on DingTalk).
    - Report mtime must be >= checklist JSON mtime.
    - Report must contain task items from the checklist (not an empty fresh scan).
    """
    rp = Path(report_path)
    cp = Path(checklist_path)

    if not rp.exists() or not cp.exists():
        return False, "based-on-checklist: missing files FAIL"

    # Load checklist JSON
    cdata = _find_checklist_json(checklist_path)
    if not cdata:
        return False, "based-on-checklist: no checklist JSON FAIL"

    # Must be confirmed (Sunday finalize wrote back)
    if not cdata.get("confirmed"):
        return False, "based-on-checklist: not confirmed FAIL"

    # Load the checklist JSON artifact and verify temporal integrity:
    # report must be generated after checklist was confirmed (JSON mtime).
    cjson_file = cp if cp.suffix == ".json" else None
    if not cjson_file or not cjson_file.exists():
        cjson_path = Path.home() / ".agents" / "work-reports" / ".checklist"
        cjson_file = None
        for f in cjson_path.glob("checklist-*.json"):
            try:
                d = json.loads(f.read_text())
                if d.get("nodeId") == cdata.get("nodeId"):
                    cjson_file = f
                    break
            except Exception:
                pass

    if not cjson_file:
        return False, "based-on-checklist: checklist JSON not found FAIL"

    json_mtime = datetime.fromtimestamp(cjson_file.stat().st_mtime)
    report_mtime = datetime.fromtimestamp(rp.stat().st_mtime)

    # Report must have been generated after checklist was confirmed
    if report_mtime < json_mtime:
        return False, f"based-on-checklist: report older than confirmed checklist FAIL"

    # Verify report has task items (not just boilerplate)
    report_items = _count_task_items(rp.read_text() if rp.exists() else "")
    if report_items == 0:
        return False, "based-on-checklist: report has no task items FAIL"

    checklist_items = len(cdata.get("tasks", []))
    # Verify report items roughly match checklist non-excluded tasks
    non_excluded = sum(1 for t in cdata.get("tasks", []) if t.get("status") != "excluded")
    if report_items < non_excluded * 0.5:
        return False, f"based-on-checklist: report({report_items}) << checklist({non_excluded}) FAIL"

    return True, f"based-on-checklist: confirmed, {checklist_items} checklist → {report_items} report items OK"

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["checklist", "report"])
    ap.add_argument("path", nargs="?", help="Path to checklist or report")
    ap.add_argument("--checklist", help="Path to checklist (report mode)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not args.path:
        print("usage: report_gate.py --mode <checklist|report> <path>", file=sys.stderr)
        sys.exit(2)

    if args.mode == "checklist":
        checks = [
            ("1.file", check_file(args.path, "checklist")),
            ("2.not-empty", check_not_empty(args.path, "checklist")),
            ("3.canon", check_from_canon(args.path)),
        ]
        hard = {"1","2"}
    else:
        if not args.checklist:
            print("--checklist required in report mode", file=sys.stderr)
            sys.exit(2)
        checks = [
            ("1.file", check_file(args.path, "report")),
            ("2.checklist-ref", check_file(args.checklist, "checklist")),
            ("3.based-on", check_based_on_checklist(args.path, args.checklist)),
            ("4.not-empty", check_not_empty(args.path, "report")),
        ]
        hard = {"1","2","3"}

    fails = [c for c in checks if c[0].split(".")[0] in hard and not c[1][0]]
    verdict = "blocked" if fails else "pass"

    if args.json:
        print(json.dumps({"verdict": verdict, "failed": [f"{n} {m}" for n,m in checks if not m[0]]}, indent=2, ensure_ascii=False))
    else:
        print(f"SITREP Gate ({args.mode}): {verdict.upper()}")
        for n, (ok, msg) in checks: print(f"  [{n}] {msg}")
    sys.exit(0 if verdict != "blocked" else 1)

if __name__ == "__main__":
    main()
