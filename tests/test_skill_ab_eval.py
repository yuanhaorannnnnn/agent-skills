from __future__ import annotations

import json
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_skill_ab_eval.py"


spec = importlib.util.spec_from_file_location("skill_ab_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class SkillAbEvalTests(unittest.TestCase):
    def test_fixture_boundary_and_artifact_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                runner.fixture_path(root, "../escape")
            (root / "result.txt").write_text("ok")
            checks = runner.check_artifacts(root, [
                {"path": "result.txt", "equals": "ok"},
                {"path": "missing.txt", "absent": True},
                {"path": "result.txt", "equals": "wrong"},
            ])
            self.assertEqual([c["passed"] for c in checks], [True, True, False])
            (root / "binary").write_bytes(b"\xff")
            bad = runner.check_artifacts(root, [{"path": "binary"}, {"path": "../escape"}])
            self.assertTrue(all(not c["passed"] for c in bad))

    def test_missing_executable_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            auth = root / "auth.json"
            auth.write_text("{}")
            result = runner.run_arm(root / "absent", auth, REPO_ROOT / "skills/execute",
                                    "test", "gpt-6.1-sol", "baseline")
            self.assertEqual(result["returncode"], 127)
            self.assertEqual(result["error"], "codex_launch_failed")

    def test_long_prompt_uses_stdin(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / "codex"
            fake.write_text("#!/usr/bin/env python3\nimport sys\nfrom pathlib import Path\n"
                            "Path(sys.argv[sys.argv.index('-o')+1]).write_text(str(len(sys.stdin.read())))\n")
            fake.chmod(0o755)
            auth = root / "auth.json"
            auth.write_text("{}")
            result = runner.run_arm(fake, auth, REPO_ROOT / "skills/execute",
                                    "x" * 150000, "gpt-6.1-sol", "baseline")
            self.assertEqual(result["returncode"], 0)
            self.assertEqual(result["response"], "150000")

    def test_timeout_is_recorded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake = root / "codex"
            fake.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(5)\n")
            fake.chmod(0o755)
            auth = root / "auth.json"
            auth.write_text("{}")
            result = runner.run_arm(fake, auth, REPO_ROOT / "skills" / "execute", "test", "gpt-6.1-sol", "baseline", timeout=1)
            self.assertEqual(result["returncode"], 124)
            self.assertEqual(result["error"], "timeout")
            self.assertIsNone(result["behavior_pass"])

    def test_runner_isolates_arms_and_writes_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_codex = root / "codex"
            fake_codex.write_text(
                "#!/bin/sh\n"
                "out=''\n"
                "while [ \"$#\" -gt 0 ]; do\n"
                "  if [ \"$1\" = '-o' ]; then out=$2; shift 2; else shift; fi\n"
                "done\n"
                "printf 'response' > \"$out\"\n"
            )
            fake_codex.chmod(0o755)
            auth = root / "auth.json"
            auth.write_text("{}")
            output = root / "result.json"
            result = subprocess.run(
                [
                    "python3",
                    str(RUNNER),
                    "--skill-dir",
                    str(REPO_ROOT / "skills" / "go-nogo"),
                    "--evals",
                    str(REPO_ROOT / "skills" / "go-nogo" / "evals" / "evals.json"),
                    "--output",
                    str(output),
                    "--codex",
                    str(fake_codex),
                    "--auth-file",
                    str(auth),
                    "--case-id",
                    "2",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text())
            self.assertEqual(report["skill"], "go-nogo")
            self.assertEqual(len(report["cases"]), 1)
            self.assertEqual(report["cases"][0]["id"], 2)
            self.assertEqual(report["cases"][0]["baseline"]["response"], "response")
            self.assertEqual(report["cases"][0]["skill"]["response"], "response")


if __name__ == "__main__":
    unittest.main()
