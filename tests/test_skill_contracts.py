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

    def test_delivery_skills_reference_shared_contract(self) -> None:
        contract = "clean-delivery-contract.md"
        paths = [
            SKILLS_DIR / "conops" / "SKILL.md",
            SKILLS_DIR / "breach" / "SKILL.md",
            SKILLS_DIR / "execute" / "SKILL.md",
            SKILLS_DIR / "sanitize" / "SKILL.md",
            SKILLS_DIR / "tasking" / "SKILL.md",
            SKILLS_DIR / "SITREP" / "SKILL.md",
            SKILLS_DIR / "repair" / "SKILL.md",
            SKILLS_DIR / "neutralize" / "SKILL.md",
            SKILLS_DIR / "herdr-carla-tune" / "SKILL.md",
            SKILLS_DIR / "cover" / "SKILL.md",
            SKILLS_DIR / "acquisition" / "SKILL.md",
            SKILLS_DIR / "codify" / "SKILL.md",
            SKILLS_DIR / "go-nogo" / "SKILL.md",
            SKILLS_DIR / "tadsim-dynamics-bench" / "SKILL.md",
            SKILLS_DIR / "traceback" / "SKILL.md",
        ]
        missing = [str(path.relative_to(REPO_ROOT)) for path in paths
                   if contract not in path.read_text()]
        self.assertEqual(missing, [])

    def test_passdown_remains_context_only(self) -> None:
        text = (SKILLS_DIR / "passdown" / "SKILL.md").read_text()
        self.assertNotIn("clean-delivery-contract.md", text)
        self.assertNotIn("accepted_spec", text)

    def test_delivery_owners_are_explicit(self) -> None:
        execute = (SKILLS_DIR / "execute" / "SKILL.md").read_text()
        conops = (SKILLS_DIR / "conops" / "SKILL.md").read_text()
        self.assertIn("负责把已确认内容固化为", execute)
        self.assertIn("由 `conops` 固化已确认的最终 brief", conops)

    def test_audit_exceptions_are_declared(self) -> None:
        self.assertIn("audit", (SKILLS_DIR / "after-action" / "SKILL.md").read_text())
        breach = (SKILLS_DIR / "breach" / "SKILL.md").read_text()
        self.assertIn("Discussion Digest 属于", breach)
        self.assertIn("X", breach)

    def test_accepted_spec_artifact_mode_is_validated(self) -> None:
        module = load_module("accepted_spec_contract", REPO_ROOT / "scripts" / "accepted_spec.py")
        spec = {
            "schema_version": 1,
            "task_id": "contract-test",
            "spec_version": 1,
            "state": "accepted",
            "artifact_mode": "not-a-mode",
            "scope": ["src/**"],
            "constraints": ["keep defaults"],
            "acceptance": ["gate validates mode"],
            "non_goals": ["new framework"],
            "approved_dependencies": [],
            "artifacts": [],
        }
        spec["spec_hash"] = module.compute_spec_hash(spec)
        errors = module.validate_spec(spec)
        self.assertTrue(any("artifact_mode" in error for error in errors))


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
        cls.conops = load_module(
            "conops_quality_gate", SKILLS_DIR / "conops" / "scripts" / "quality_gate.py"
        )
        cls.report = load_module(
            "sanitize_report_gate", SKILLS_DIR / "sanitize" / "scripts" / "report_gate.py"
        )
        cls.cover = load_module(
            "cover_synthesis_gate", SKILLS_DIR / "cover" / "scripts" / "synthesis_gate.py"
        )
        cls.sitrep = load_module(
            "sitrep_report_gate", SKILLS_DIR / "SITREP" / "scripts" / "report_gate.py"
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

    def test_tasking_delivery_contract_requires_accepted_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            goal = root / "goal.md"
            goal.write_text(
                "## Goal\nP0\n## Tasks\n- [ ] test\n"
                "- artifact_mode: delivery\n",
                encoding="utf-8",
            )
            state = root / "state.json"
            state.write_text(json.dumps({"goal_path": str(goal)}))
            ok, message = self.tasking.check_delivery_contract(state, root)
            self.assertFalse(ok)
            self.assertIn("accepted_spec_path required", message)

    def test_sanitize_requires_progress_commit_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            task = Path(tmp) / "task.md"
            task.write_text("## Progress\n- committed: abc123\n")
            self.assertTrue(self.sanitize.check_canon_updated(task)[0])
            task.write_text("## Progress\n- implementation pending\n")
            self.assertFalse(self.sanitize.check_canon_updated(task)[0])

    def test_sanitize_consumes_scope_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            gate = root / "scope-gate.json"
            gate.write_text(json.dumps({"verdict": "pass"}))
            self.assertTrue(self.sanitize.check_scope_gate(gate)[0])
            gate.write_text(json.dumps({"verdict": "blocked"}))
            self.assertFalse(self.sanitize.check_scope_gate(gate)[0])

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

    def test_delivery_renderers_require_accepted_spec(self) -> None:
        self.assertFalse(self.conops.check_delivery_contract(mode="delivery")[0])
        self.assertFalse(self.report.check_artifact_contract(mode="delivery")[0])
        self.assertFalse(self.cover.check_artifact_contract(mode="delivery")[0])

    def test_sitrep_delivery_requires_confirmed_checklist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report = root / "report.md"
            report.write_text("# report")
            checklist = root / "checklist.json"
            checklist.write_text(json.dumps({"confirmed": False}))
            ok, message = self.sitrep.check_artifact_mode(
                "delivery", report, checklist
            )
            self.assertFalse(ok)
            self.assertIn("confirmed checklist", message)


if __name__ == "__main__":
    unittest.main()
