from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GATE = REPO_ROOT / "skills" / "Neutralize" / "scripts" / "verify_fix_gate.py"


class NeutralizeGateTests(unittest.TestCase):
    def run_gate(self, evidence: dict) -> subprocess.CompletedProcess:
        with tempfile.TemporaryDirectory() as tmp:
            evidence_path = Path(tmp) / "evidence.json"
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")
            return subprocess.run(
                ["python3", str(GATE), "--evidence", str(evidence_path), "--json"],
                capture_output=True,
                text=True,
                check=False,
            )

    def test_complete_feedback_loop_passes(self) -> None:
        result = self.run_gate(
            {
                "failure_observation": "targeted test failed before the fix",
                "reproduction_command": "pytest tests/test_target.py",
                "rerun_command": "pytest tests/test_target.py",
                "rerun_exit_code": 0,
                "adjacent_searches": ["rg same_pattern src"],
                "adjacent_findings": [],
                "public_interface_changed": False,
                "boundary_assessment": "public interface stayed stable inside parser module",
                "remaining_risk": "broader integration suite was not available",
            }
        )
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_missing_pre_change_evidence_blocks(self) -> None:
        result = self.run_gate(
            {
                "rerun_command": "pytest tests/test_target.py",
                "rerun_exit_code": 0,
                "adjacent_searches": ["rg same_pattern src"],
                "adjacent_findings": [],
                "public_interface_changed": False,
                "boundary_assessment": "public interface stayed stable inside parser module",
                "remaining_risk": "broader integration suite was not available",
            }
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("2.observable-target", result.stdout)


if __name__ == "__main__":
    unittest.main()
