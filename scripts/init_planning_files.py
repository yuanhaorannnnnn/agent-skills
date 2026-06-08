#!/usr/bin/env python3
"""DEPRECATED — planning workspace initialization.

This script was part of the old plan-workspace (Staging) skill which has been
absorbed by Execute --plan. Canon task pages (§ Plan / § Findings / § Progress)
replace the old .planning/conversations/<id>/ workspace.

Kept for backward reference only. Do not use in new workflows.
"""
from __future__ import annotations

import argparse
from pathlib import Path


def main() -> int:
    print(
        "DEPRECATED: init_planning_files.py is no longer used.\n"
        "Use Execute --plan to create planning structure in Canon task pages.\n"
        "See /home/yhr/.agents/repos/agent-skills/skills/Execute/references/plan-template.md"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
