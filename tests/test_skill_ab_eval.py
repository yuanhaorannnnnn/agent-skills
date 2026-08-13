from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "scripts" / "run_skill_ab_eval.py"


class SkillAbEvalTests(unittest.TestCase):
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
