from __future__ import annotations

import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO_ROOT / "skills"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SkillContractTests(unittest.TestCase):
    def test_enabled_skills_do_not_hardcode_claude_install_root(self) -> None:
        manifest = yaml.safe_load((REPO_ROOT / "manifest.yaml").read_text())
        enabled = [entry["name"] for entry in manifest["skills"] if entry["enabled"]]
        offenders = []
        for name in enabled:
            for path in (SKILLS_DIR / name).rglob("*.md"):
                if "~/.claude/skills" in path.read_text():
                    offenders.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual(offenders, [])

    def test_acquisition_self_script_references_exist(self) -> None:
        skill_dir = SKILLS_DIR / "acquisition"
        text = (skill_dir / "SKILL.md").read_text()
        self.assertNotIn("~/.agents/skills/content-ingest", text)
        scripts = set(re.findall(r"<skill-dir>/scripts/([a-z0-9_]+\.py)", text))
        self.assertGreaterEqual(len(scripts), 3)
        self.assertEqual(
            [name for name in sorted(scripts) if not (skill_dir / "scripts" / name).is_file()],
            [],
        )

    def test_repair_declares_raw_read_only_and_state_scoped_write(self) -> None:
        text = (SKILLS_DIR / "repair" / "SKILL.md").read_text()
        self.assertIn("raw 输入只读", text)
        self.assertIn("state.json", text)
        self.assertIn("scoped write", text)

    def test_herdr_tune_resolves_live_ids(self) -> None:
        text = (SKILLS_DIR / "herdr-carla-tune" / "SKILL.md").read_text()
        self.assertIsNone(re.search(r"w\d+:p[A-Za-z0-9]+", text))
        self.assertIn("herdr workspace list", text)
        self.assertIn("herdr pane list", text)
        for variable in ("BUILD_PANE", "SERVER_PANE", "CLIENT_PANE"):
            self.assertIn(variable, text)

    def test_breach_declares_writing_discipline_dependency(self) -> None:
        manifest = yaml.safe_load((REPO_ROOT / "manifest.yaml").read_text())
        breach = next(entry for entry in manifest["skills"] if entry["name"] == "breach")
        self.assertIn("engineering-doc-writing", breach["calls"])
        text = (SKILLS_DIR / "breach" / "SKILL.md").read_text()
        self.assertIn("invoke `engineering-doc-writing`", text)
        self.assertIn("HTML structure, visual tokens, rendering, and provenance", text)


class WorkflowGateHelperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repair = load_module(
            "repair_intake_gate", SKILLS_DIR / "repair" / "scripts" / "intake_gate.py"
        )
        cls.tasking = load_module(
            "tasking_engage_gate", SKILLS_DIR / "tasking" / "scripts" / "engage_gate.py"
        )
        cls.sanitize = load_module(
            "sanitize_wrapup_gate", SKILLS_DIR / "sanitize" / "scripts" / "wrapup_gate.py"
        )
        cls.herdr_preflight = load_module(
            "herdr_preflight_gate",
            SKILLS_DIR / "herdr-carla-tune" / "scripts" / "preflight_gate.py",
        )
        cls.herdr_round = load_module(
            "herdr_round_gate",
            SKILLS_DIR / "herdr-carla-tune" / "scripts" / "round_gate.py",
        )

    def test_repair_accepts_confirmed_intake_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "state.json"
            state.write_text(json.dumps({"phase": "intake", "title": "bug"}))
            ok, _ = self.repair.check_state_json(state)
            self.assertTrue(ok)

            plan = root / "fix_plan.json"
            plan.write_text(
                json.dumps(
                    {
                        "root_cause": {"hypothesis": "confirmed", "confidence": "verified"},
                        "fix_plan": {"modified_files": ["src/a.py"]},
                        "uncertainties": [],
                    }
                )
            )
            ok, _ = self.repair.check_fix_plan_json(plan)
            self.assertTrue(ok)

    def test_tasking_engage_helpers_require_goal_and_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal = root / "goal.md"
            goal.write_text("# Goal")
            state = root / "state.json"
            state.write_text(
                json.dumps(
                    {"phase": "dev", "goal_path": str(goal), "review_gate": "passed"}
                )
            )
            self.assertTrue(self.tasking.check_state_phase(state)[0])
            self.assertTrue(self.tasking.check_goal_md(state, root)[0])
            self.assertTrue(self.tasking.check_review_gate(state)[0])

    def test_sanitize_requires_progress_commit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.md"
            task.write_text("## Progress\n- committed: abc123\n")
            self.assertTrue(self.sanitize.check_canon_updated(task)[0])
            task.write_text("## Progress\n- implementation pending\n")
            self.assertFalse(self.sanitize.check_canon_updated(task)[0])

    def test_herdr_tune_gates_accept_injected_state_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = root / "loop.yaml"
            self.assertTrue(self.herdr_preflight.check_state(state)[0])
            self.assertFalse(self.herdr_preflight.check_clean(root / "missing", "target")[0])
            self.assertFalse(self.herdr_round.check_worktree_clean(root / "missing")[0])
            state.write_text(
                yaml.safe_dump(
                    {
                        "loop_id": "test-loop",
                        "config": {"max_rounds": 3},
                        "current": {"round": 1},
                        "termination": {"reason": "", "no_improvement_streak": 0},
                        "hypotheses": [{"id": "h1", "status": "pending"}],
                    }
                )
            )
            self.assertTrue(self.herdr_round.check_state_file(state)[0])
            self.assertTrue(self.herdr_round.check_not_terminated(state)[0])
            self.assertTrue(self.herdr_round.check_hypotheses_remaining(state)[0])
            self.assertTrue(self.herdr_round.check_round_limits(state)[0])


class ExecuteGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.execute = load_module(
            "execute_gate", SKILLS_DIR / "execute" / "scripts" / "execution_gate.py"
        )

    @staticmethod
    def write_task(
        path: Path,
        *,
        routing_mode: str = "auto",
        resolved_route: str = "direct",
        depth: int = 0,
        extra: str = "",
    ) -> None:
        routing = (
            "## Routing\n"
            f"- routing_mode: {routing_mode}\n"
            f"- resolved_route: {resolved_route}\n"
            "- reason: bounded task\n"
            "- router_owner: main Execute router\n"
            f"- delegation_depth: {depth}\n"
            "- downstream_auto_delegate: forbidden\n"
            "- models: current\n"
            "- scope: scoped files\n"
            "- status: active\n"
            "- evidence: contract\n\n"
        )
        path.write_text(
            "# Task\n\n## Goal\nDo work.\n\n## Current State\nActive.\n\n"
            "## Next Step\nImplement.\n\n## Tasks\n- [ ] Work\n\n"
            f"## Progress\nStarted.\n\n{routing}{extra}",
            encoding="utf-8",
        )

    def test_auto_route_records_direct_without_goal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.md"
            self.write_task(task)
            self.assertEqual(self.execute.main(["--mode", "none", "--task", str(task)]), 0)

    def test_direct_and_delegate_routes_require_matching_records(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.md"
            self.write_task(task, routing_mode="direct")
            self.assertEqual(
                self.execute.main(["--mode", "none", "--direct", "--task", str(task)]), 0
            )
            self.write_task(
                task,
                routing_mode="delegate",
                resolved_route="delegate",
                depth=1,
                extra=(
                    "## Delegation\n"
                    "- executor: luna\n"
                    "- scope: scoped files\n"
                    "- status: returned\n"
                    "- evidence: tests\n"
                ),
            )
            self.assertEqual(
                self.execute.main(["--mode", "none", "--delegate", "--task", str(task)]), 0
            )

    def test_plan_delegate_requires_goal_plan_and_delegation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = root / "task.md"
            goal = root / "goal.md"
            self.write_task(
                task,
                routing_mode="delegate",
                resolved_route="delegate",
                depth=1,
                extra=(
                    "## Plan\nPlan it.\n\n## Delegation\n"
                    "- executor: terra\n"
                    "- scope: scoped files\n"
                    "- status: returned\n"
                    "- evidence: tests\n"
                ),
            )
            goal.write_text("# Goal\n\n## Goal\nShip it.\n\n## Tasks\n- [ ] Implement\n", encoding="utf-8")
            self.assertEqual(
                self.execute.main(
                    ["--mode", "plan", "--delegate", "--task", str(task), "--goal", str(goal)]
                ),
                0,
            )

    def test_rejects_conflicting_or_recursive_delegate_flags(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.md"
            self.write_task(task)
            with self.assertRaises(SystemExit):
                self.execute.main(
                    ["--mode", "none", "--direct", "--delegate", "--task", str(task)]
                )
            with self.assertRaises(SystemExit):
                self.execute.main(
                    [
                        "--mode", "none", "--delegate", "--delegation-depth", "1",
                        "--task", str(task),
                    ]
                )

    def test_downstream_auto_cannot_resolve_to_delegate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.md"
            self.write_task(task, resolved_route="delegate", depth=2)
            self.assertEqual(
                self.execute.main(
                    ["--mode", "none", "--route", "auto", "--delegation-depth", "1", "--task", str(task)]
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
