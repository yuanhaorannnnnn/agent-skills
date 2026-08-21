from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "skills" / "traceback" / "scripts" / "scope_gate.py"
HELPER = REPO_ROOT / "scripts" / "accepted_spec.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ScopeGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gate = load_module(GATE, "scope_gate")
        cls.helper = load_module(HELPER, "accepted_spec_for_scope")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.run_cmd(["git", "init", "-q"])
        self.run_cmd(["git", "config", "user.email", "test@example.com"])
        self.run_cmd(["git", "config", "user.name", "test"])
        (self.repo / "src.py").write_text("value = 1\n", encoding="utf-8")
        self.run_cmd(["git", "add", "."])
        self.run_cmd(["git", "commit", "-qm", "baseline"])

    def tearDown(self):
        self.temp.cleanup()

    def run_cmd(self, command):
        return subprocess.run(
            command,
            cwd=self.repo,
            capture_output=True,
            text=True,
            check=True,
        )

    def write_spec(self, scope, approved=None):
        spec = {
            "schema_version": 1,
            "task_id": "scope-test",
            "spec_version": 1,
            "state": "accepted",
            "scope": scope,
            "constraints": ["keep defaults"],
            "acceptance": ["scope is checked"],
            "non_goals": ["new framework"],
            "approved_dependencies": approved or [],
            "artifacts": [],
        }
        spec["spec_hash"] = self.helper.compute_spec_hash(spec)
        path = self.root / "accepted_spec.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        return path

    def test_in_scope_change_passes(self):
        (self.repo / "src.py").write_text("value = 2\n", encoding="utf-8")
        spec = self.write_spec(["src.py"])
        result = self.gate.evaluate(self.repo, spec)
        self.assertEqual(result["verdict"], "pass")
        self.assertEqual(result["unmapped_hunks"], [])

    def test_out_of_scope_change_blocks(self):
        (self.repo / "other.py").write_text("value = 2\n", encoding="utf-8")
        spec = self.write_spec(["src.py"])
        result = self.gate.evaluate(self.repo, spec)
        self.assertEqual(result["verdict"], "blocked")
        self.assertEqual(result["unmapped_hunks"][0]["path"], "other.py")

    def test_stale_spec_blocks(self):
        spec = self.write_spec(["src.py"])
        data = json.loads(spec.read_text())
        data["acceptance"] = ["changed after approval"]
        spec.write_text(json.dumps(data), encoding="utf-8")
        result = self.gate.evaluate(self.repo, spec)
        self.assertEqual(result["verdict"], "blocked")
        self.assertIn("stale or mismatched", result["errors"][0])

    def test_unapproved_requirement_change_blocks(self):
        (self.repo / "requirements.txt").write_text("requests==2.0\n", encoding="utf-8")
        spec = self.write_spec(["**"])
        result = self.gate.evaluate(self.repo, spec)
        self.assertEqual(result["verdict"], "blocked")
        self.assertTrue(result["new_dependencies"])


if __name__ == "__main__":
    unittest.main()
