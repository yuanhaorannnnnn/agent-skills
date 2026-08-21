from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRACEBACK_DIR = REPO_ROOT / "skills" / "traceback"
GATE = TRACEBACK_DIR / "scripts" / "traceback_gate.py"
RENDER = TRACEBACK_DIR / "scripts" / "render_alignment.py"
ENGAGE_GATE = (
    REPO_ROOT / "skills" / "tasking" / "scripts" / "engage_gate.py"
)


class TracebackGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self._run(["git", "init", "-q"], cwd=self.repo)
        self._run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.repo,
        )
        self._run(
            ["git", "config", "user.name", "Test"],
            cwd=self.repo,
        )
        (self.repo / "src.py").write_text(
            "def run():\n    return 1\n",
            encoding="utf-8",
        )
        (self.repo / "test_src.py").write_text(
            "from src import run\n\ndef test_run():\n"
            "    assert run() == 1\n",
            encoding="utf-8",
        )
        (self.repo / "design.md").write_text(
            "# Design\nThe run function returns one.\n",
            encoding="utf-8",
        )
        self.canon = self.root / "canon-task.md"
        self.canon.write_text("# Task\n", encoding="utf-8")
        self._run(["git", "add", "."], cwd=self.repo)
        self._run(["git", "commit", "-qm", "baseline"], cwd=self.repo)
        self.plan = self.repo / ".planning" / "task-1"
        self.plan.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def _run(self, command, cwd=None, check=True):
        return subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
        )

    def _fingerprint(self):
        result = self._run(
            [
                "python3",
                str(GATE),
                "--repo",
                str(self.repo),
                "--fingerprint",
            ]
        )
        return json.loads(result.stdout)

    def _alignment(self):
        fingerprint = self._fingerprint()
        design = self.repo / "design.md"
        return {
            "schema_version": 1,
            "mode": "alignment",
            "task": {
                "id": "task-1",
                "canon_task_path": str(self.canon),
            },
            "checked_at": "2026-07-22T12:00:00+08:00",
            "checked_commit": fingerprint["checked_commit"],
            "workspace_fingerprint": fingerprint["workspace_fingerprint"],
            "inputs": [
                {
                    "kind": "design",
                    "path": "design.md",
                    "sha256": hashlib.sha256(
                        design.read_bytes()
                    ).hexdigest(),
                }
            ],
            "requirements": [
                {
                    "id": "REQ-001",
                    "source_ref": "design.md §1",
                    "requirement": "run returns one",
                    "severity": "P1",
                    "implementation": {
                        "status": "implemented",
                        "confidence": "direct",
                        "evidence": [
                            {"path": "src.py", "symbol": "run", "line": 1}
                        ],
                    },
                    "tests": {
                        "status": "covered",
                        "confidence": "direct",
                        "evidence": [
                            {
                                "path": "test_src.py",
                                "symbol": "test_run",
                                "line": 3,
                            }
                        ],
                        "run_ids": ["RUN-001"],
                    },
                }
            ],
            "validation_runs": [
                {
                    "id": "RUN-001",
                    "command": "python3 -m unittest",
                    "result": "passed",
                }
            ],
            "boundary_drift": [],
            "canon": {"recorded": False, "update_card_path": ""},
        }

    def _write_and_render(self, data):
        (self.plan / "alignment.json").write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
        self._run(
            [
                "python3",
                str(RENDER),
                "--input",
                str(self.plan / "alignment.json"),
                "--output",
                str(self.plan / "alignment.md"),
            ]
        )

    def _gate(self, scope_gate=None):
        command = [
            "python3",
            str(GATE),
            "--dir",
            str(self.plan),
            "--repo",
            str(self.repo),
            "--json",
        ]
        if scope_gate:
            command.extend(["--scope-gate", str(scope_gate)])
        return self._run(
            command,
            check=False,
        )

    def test_valid_alignment_passes(self):
        self._write_and_render(self._alignment())
        result = self._gate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["verdict"], "pass")

    def test_scope_gate_block_is_consumed(self):
        self._write_and_render(self._alignment())
        scope_gate = self.root / "scope-gate.json"
        scope_gate.write_text(
            json.dumps(
                {
                    "verdict": "blocked",
                    "checked_commit": self._fingerprint()["checked_commit"],
                    "errors": ["changed files outside accepted scope"],
                }
            ),
            encoding="utf-8",
        )
        result = self._gate(scope_gate)
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertIn(
            "scope-gate: verdict is not pass",
            payload["errors"],
        )

    def test_placeholder_markdown_without_alignment_blocks(self):
        for name in (
            "document-dev-checklist.md",
            "dev-test-coverage-checklist.md",
            "align-summary.md",
        ):
            (self.plan / name).write_text(
                "# Placeholder\n" + "x" * 80,
                encoding="utf-8",
            )
        result = self._gate()
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["verdict"], "blocked")
        self.assertIn("alignment.json: missing", payload["errors"])

    def test_p1_missing_implementation_blocks(self):
        data = self._alignment()
        data["requirements"][0]["implementation"] = {
            "status": "missing",
            "confidence": "none",
            "evidence": [],
        }
        data["requirements"][0]["tests"] = {
            "status": "not-applicable",
            "reason": "No implementation",
            "confidence": "none",
            "evidence": [],
            "run_ids": [],
        }
        data["canon"]["recorded"] = True
        self._write_and_render(data)
        result = self._gate()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["verdict"], "blocked")

    def test_three_p2_missing_tests_block(self):
        data = self._alignment()
        base = data["requirements"][0]
        requirements = []
        for index in range(3):
            item = json.loads(json.dumps(base))
            item["id"] = f"REQ-{index + 1:03d}"
            item["severity"] = "P2"
            item["tests"] = {
                "status": "missing",
                "confidence": "none",
                "evidence": [],
                "run_ids": [],
            }
            requirements.append(item)
        data["requirements"] = requirements
        data["validation_runs"] = []
        data["canon"]["recorded"] = True
        self._write_and_render(data)
        result = self._gate()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(len(json.loads(result.stdout)["findings"]), 3)

    def test_workspace_change_blocks_stale_alignment(self):
        self._write_and_render(self._alignment())
        (self.repo / "src.py").write_text(
            "def run():\n    return 2\n",
            encoding="utf-8",
        )
        result = self._gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "workspace_fingerprint: stale or missing",
            json.loads(result.stdout)["errors"],
        )

    def test_stale_markdown_blocks(self):
        self._write_and_render(self._alignment())
        data = json.loads(
            (self.plan / "alignment.json").read_text(encoding="utf-8")
        )
        data["requirements"][0]["requirement"] = "changed view"
        (self.plan / "alignment.json").write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )
        result = self._gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "alignment.md: stale or not generated from alignment.json",
            json.loads(result.stdout)["errors"],
        )

    def test_manual_markdown_edit_blocks(self):
        self._write_and_render(self._alignment())
        with (self.plan / "alignment.md").open("a", encoding="utf-8") as handle:
            handle.write("\nmanual edit\n")
        result = self._gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "alignment.md: stale or not generated from alignment.json",
            json.loads(result.stdout)["errors"],
        )

    def test_duplicate_requirement_id_blocks(self):
        data = self._alignment()
        data["requirements"].append(
            json.loads(json.dumps(data["requirements"][0]))
        )
        self._write_and_render(data)
        result = self._gate()
        self.assertEqual(result.returncode, 1)
        self.assertTrue(
            any(
                "duplicate REQ-001" in error
                for error in json.loads(result.stdout)["errors"]
            )
        )

    def test_failed_validation_run_blocks(self):
        data = self._alignment()
        data["validation_runs"][0]["result"] = "failed"
        data["canon"]["recorded"] = True
        self._write_and_render(data)
        result = self._gate()
        self.assertEqual(result.returncode, 1)
        payload = json.loads(result.stdout)
        self.assertTrue(
            any(
                item["category"] == "validation"
                for item in payload["findings"]
            )
        )

    def test_accepted_boundary_drift_requires_canon(self):
        data = self._alignment()
        data["boundary_drift"] = [
            {
                "id": "DRIFT-001",
                "description": "Undocumented public method",
                "severity": "P2",
                "status": "accepted",
                "reason": "Approved expansion",
                "evidence": [
                    {"path": "src.py", "symbol": "run", "line": 1}
                ],
            }
        ]
        self._write_and_render(data)
        result = self._gate()
        self.assertEqual(result.returncode, 1)
        self.assertIn(
            "canon.recorded: required for gaps, drift, or waivers",
            json.loads(result.stdout)["errors"],
        )

    def test_recorded_skip_passes_as_skipped(self):
        fingerprint = self._fingerprint()
        data = {
            "schema_version": 1,
            "mode": "skipped",
            "task": {
                "id": "task-1",
                "canon_task_path": str(self.canon),
            },
            "checked_at": "2026-07-22T12:00:00+08:00",
            "checked_commit": fingerprint["checked_commit"],
            "workspace_fingerprint": fingerprint["workspace_fingerprint"],
            "inputs": [],
            "requirements": [],
            "validation_runs": [],
            "boundary_drift": [],
            "canon": {
                "recorded": True,
                "skip_reason": "No approved source artifact",
                "update_card_path": "",
            },
        }
        self._write_and_render(data)
        result = self._gate()
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(json.loads(result.stdout)["verdict"], "skipped")

    def test_tasking_consumes_current_traceback_gate(self):
        self._write_and_render(self._alignment())
        spec = importlib.util.spec_from_file_location(
            "engage_gate",
            ENGAGE_GATE,
        )
        module = importlib.util.module_from_spec(spec)
        assert spec.loader
        spec.loader.exec_module(module)
        ok, message = module.check_traceback(self.repo, "task-1")
        self.assertTrue(ok, message)
        self.assertIn("pass", message)


if __name__ == "__main__":
    unittest.main()
