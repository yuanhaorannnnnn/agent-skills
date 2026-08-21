from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "skills" / "execute" / "scripts" / "execution_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("execution_gate", GATE)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ExecutionGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = load_module()

    def make_spec(self, root: Path, mode=None):
        spec = {
            "schema_version": 1,
            "task_id": "gate-test",
            "spec_version": 1,
            "state": "accepted",
            "scope": ["src/**"],
            "constraints": ["keep defaults"],
            "acceptance": ["gate validates hash"],
            "non_goals": ["new framework"],
            "approved_dependencies": [],
            "artifacts": [],
        }
        if mode is not None:
            spec["artifact_mode"] = mode
        spec["spec_hash"] = cls_hash(spec)
        path = root / "accepted_spec.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        return path

    def test_goal_metadata_requires_valid_accepted_spec(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_path = self.make_spec(root)
            goal = root / "goal.md"
            goal.write_text(
                "## Goal\nP1\n## Tasks\n- [ ] test\n"
                f"- accepted_spec_path: {spec_path}\n",
                encoding="utf-8",
            )
            task = root / "task.md"
            task.write_text("## Goal\nP1\n", encoding="utf-8")
            ok, message = self.gate.check_accepted_spec(
                self.gate.accepted_spec_path_from_goal(goal),
                required=True,
            )
            self.assertTrue(ok, message)

    def test_stale_accepted_spec_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_path = self.make_spec(root)
            spec = json.loads(spec_path.read_text())
            spec["acceptance"] = ["changed after approval"]
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            ok, message = self.gate.check_accepted_spec(spec_path, required=True)
            self.assertFalse(ok)
            self.assertIn("stale or mismatched", message)

    def test_cli_treats_accepted_spec_as_a_hard_check(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_path = self.make_spec(root)
            spec = json.loads(spec_path.read_text())
            spec["acceptance"] = ["changed after approval"]
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            goal = root / "goal.md"
            goal.write_text(
                "## Goal\nP1\n## Tasks\n- [ ] test\n"
                f"- accepted_spec_path: {spec_path}\n",
                encoding="utf-8",
            )
            task = root / "task.md"
            task.write_text("## Goal\nP1\n", encoding="utf-8")
            result = subprocess.run(
                [
                    "python3",
                    str(GATE),
                    "--goal",
                    str(goal),
                    "--task",
                    str(task),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("5.accepted-spec", result.stdout)

    def test_delivery_requires_declared_mode(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_path = self.make_spec(root)
            ok, message = self.gate.check_accepted_spec(
                spec_path,
                required=True,
                required_mode="delivery",
            )
            self.assertFalse(ok)
            self.assertIn("artifact_mode: required", message)

    def test_delivery_rejects_mode_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spec_path = self.make_spec(root, "audit")
            ok, message = self.gate.check_accepted_spec(
                spec_path,
                required=True,
                required_mode="delivery",
            )
            self.assertFalse(ok)
            self.assertIn("expected 'delivery'", message)

    def test_delivery_goal_without_spec_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            goal = root / "goal.md"
            goal.write_text(
                "## Goal\nP0\n## Tasks\n- [ ] test\n"
                "- artifact_mode: delivery\n",
                encoding="utf-8",
            )
            task = root / "task.md"
            task.write_text("## Goal\nP0\n", encoding="utf-8")
            result = subprocess.run(
                ["python3", str(GATE), "--goal", str(goal), "--task", str(task), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("accepted_spec: required", result.stdout)


def cls_hash(spec):
    helper = importlib.util.spec_from_file_location(
        "accepted_spec", REPO_ROOT / "scripts" / "accepted_spec.py"
    )
    module = importlib.util.module_from_spec(helper)
    assert helper.loader is not None
    helper.loader.exec_module(module)
    return module.compute_spec_hash(spec)


if __name__ == "__main__":
    unittest.main()
