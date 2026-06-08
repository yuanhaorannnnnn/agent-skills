#!/usr/bin/env python3
"""Unit tests for skill-architect scripts."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

# Add scripts/ to path for imports
import sys

scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))

from render_ascii import render_workflow, render_architecture, render
from scan_skills import parse_frontmatter


def test_parse_frontmatter_simple():
    """Test parsing a simple frontmatter block."""
    content = """---
name: test-skill
description: |
  This is a multiline
  description.
version: "1.0.0"
---

# Test Skill

Some content.
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(content)
        f.flush()
        path = Path(f.name)

    try:
        data = parse_frontmatter(path)
        assert data["name"] == "test-skill"
        assert "multiline" in data["description"]
        assert data["version"] == "1.0.0"
    finally:
        path.unlink()


def test_render_workflow_single_node():
    """Test workflow render with a single node."""
    topology = {
        "nodes": [{"id": "secure", "name": "Secure"}],
        "edges": [],
    }
    result = render_workflow(topology)
    assert "Secure" in result
    assert "┌" in result  # box-drawing char


def test_render_workflow_chain():
    """Test workflow render with a linear chain."""
    topology = {
        "nodes": [
            {"id": "secure", "name": "secure"},
            {"id": "reactivate", "name": "reactivate"},
        ],
        "edges": [{"from": "secure", "to": "reactivate", "label": "triggers"}],
    }
    result = render_workflow(topology)
    assert "secure" in result
    assert "reactivate" in result
    assert "──▶" in result


def test_render_architecture_layers():
    """Test architecture render with groups."""
    topology = {
        "nodes": [
            {"id": "StandUp", "name": "StandUp"},
            {"id": "secure", "name": "secure"},
        ],
        "edges": [{"from": "StandUp", "to": "secure", "label": "creates"}],
        "groups": [
            {"name": "Infra", "members": ["StandUp"]},
            {"name": "Persist", "members": ["secure"]},
        ],
    }
    result = render_architecture(topology)
    assert "[Infra]" in result
    assert "[Persist]" in result
    assert "StandUp" in result
    assert "secure" in result


def test_render_architecture_no_groups():
    """Test architecture render without explicit groups."""
    topology = {
        "nodes": [{"id": "a", "name": "skill-a"}],
        "edges": [],
        "groups": [],
    }
    result = render_architecture(topology)
    assert "[Skills]" in result
    assert "skill-a" in result


def test_render_unknown_mold():
    """Test render with unknown mold type."""
    topology = {"nodes": [], "edges": []}
    result = render(topology, "unknown")
    assert "Unknown mold" in result


def test_workflow_with_branching():
    """Test workflow with a branching edge."""
    topology = {
        "nodes": [
            {"id": "dev", "name": "Sanitize"},
            {"id": "secure", "name": "secure"},
            {"id": "git", "name": "git-push"},
        ],
        "edges": [
            {"from": "dev", "to": "secure", "label": "includes"},
            {"from": "dev", "to": "git", "label": "triggers"},
        ],
    }
    result = render_workflow(topology)
    assert "Sanitize" in result
    assert "──▶" in result


if __name__ == "__main__":
    # Run all tests
    tests = [
        test_parse_frontmatter_simple,
        test_render_workflow_single_node,
        test_render_workflow_chain,
        test_render_architecture_layers,
        test_render_architecture_no_groups,
        test_render_unknown_mold,
        test_workflow_with_branching,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {test.__name__}: {e}")
            failed += 1

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(0 if failed == 0 else 1)
