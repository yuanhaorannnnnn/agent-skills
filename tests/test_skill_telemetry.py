from __future__ import annotations

import json
import os
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "skill_telemetry.py"


class SkillTelemetryTests(unittest.TestCase):
    def test_emit_writes_minimal_private_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            result = subprocess.run(
                [
                    "python3",
                    str(SCRIPT),
                    "--path",
                    str(output),
                    "--skill",
                    "passdown",
                    "--runtime",
                    "codex",
                    "--trigger",
                    "explicit",
                    "--outcome",
                    "pass",
                    "--duration-ms",
                    "42",
                    "--artifact",
                    "/tmp/report.md",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            event = json.loads(output.read_text().strip())
            self.assertEqual(event["schema_version"], 1)
            self.assertEqual(event["skill"], "passdown")
            self.assertEqual(event["outcome"], "pass")
            self.assertEqual(event["artifacts"], ["/tmp/report.md"])
            self.assertNotIn("prompt", event)
            self.assertNotIn("response", event)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)

    def test_emit_rejects_invalid_name_and_negative_duration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            for extra in (
                ["--skill", "bad skill", "--duration-ms", "1"],
                ["--skill", "passdown", "--duration-ms", "-1"],
            ):
                result = subprocess.run(
                    [
                        "python3",
                        str(SCRIPT),
                        "--path",
                        str(output),
                        "--runtime",
                        "codex",
                        "--trigger",
                        "explicit",
                        "--outcome",
                        "pass",
                        *extra,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
