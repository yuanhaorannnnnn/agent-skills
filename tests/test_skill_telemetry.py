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

    def emit(self, output, *extra):
        return subprocess.run(
            ["python3", str(SCRIPT), "--path", str(output), "--skill", "breach",
             "--runtime", "codex", "--trigger", "implicit", "--outcome", "pass", *extra],
            capture_output=True, text=True, check=False)

    def test_routing_compares_only_explicit_expectations_and_records_steps(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            result = self.emit(output, "--route", "general-page", "--entry", "natural-language",
                               "--expected-route", "discussion-digest", "--decision", "prose=faithful",
                               "--step", "paperwork=skipped", "--step", "render=pending")
            self.assertEqual(result.returncode, 0, result.stderr)
            result = self.emit(output, "--route", "general-page")
            self.assertEqual(result.returncode, 0, result.stderr)
            first, second = map(json.loads, output.read_text().splitlines())
            self.assertEqual(first["schema_version"], 2)
            self.assertFalse(first["route_match"])
            self.assertEqual(first["outcome"], "pass")
            self.assertEqual(first["steps"], {"paperwork": "skipped", "render": "pending"})
            self.assertIsNone(second["route_match"])
            self.assertIsNone(second["expected_route"])

    def test_closed_vocabulary_rejects_content_and_duplicates_without_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            for extra in (
                ("--route", "user supplied prose"),
                ("--route", "general-page", "--expected-route", "secret"),
                ("--route", "general-page", "--decision", "reason=secret"),
                ("--route", "general-page", "--decision", "prose=secret"),
                ("--route", "general-page", "--decision", "prose=author", "--decision", "prose=faithful"),
                ("--route", "general-page", "--step", "render=selected"),
                ("--route", "general-page", "--step", "secret=pass"),
                ("--route", "general-page", "--step", "render=pass", "--step", "render=pending"),
                ("--entry", "natural-language"),
                ("--skill", "passdown", "--route", "general-page"),
            ):
                result = self.emit(output, *extra)
                self.assertNotEqual(result.returncode, 0, extra)
                self.assertFalse(output.exists(), extra)

    def test_report_handles_legacy_missing_partial_and_filters_private_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            command = ["python3", str(SCRIPT), "--path", str(output), "--report", "--skill", "breach"]
            empty = subprocess.run(command, capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(empty.stdout)["routes"], {})
            self.assertFalse(output.exists())
            self.assertEqual(self.emit(output).returncode, 0)
            self.assertEqual(self.emit(output, "--route", "general-page", "--expected-route", "discussion-digest",
                                       "--step", "render=pending").returncode, 0)
            with output.open("a") as stream:
                stream.write(json.dumps({"skill": "sanitize", "outcome": "pass", "prompt": "SECRET"}) + "\n")
                stream.write(json.dumps({"skill": "breach", "outcome": "pass", "route": "SECRET",
                                         "expected_route": "SECRET", "decisions": {"prose": "SECRET"}}) + "\n")
                stream.write('{"partial":')
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            report = json.loads(result.stdout)
            self.assertEqual(report["routes"], {"breach:unobserved": 2, "breach:general-page": 1})
            self.assertEqual(report["mismatches"], {"breach:discussion-digest->general-page": 1})
            self.assertEqual(report["unknown_expectations"], 2)
            self.assertEqual(report["invalid_lines"], 1)
            self.assertEqual(report["steps"], {"breach:render:pending": 1})
            self.assertNotIn("SECRET", result.stdout)

    def test_each_supported_skill_can_record_an_actual_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "events.jsonl"
            for skill, route, decision, step in (
                ("breach", "discussion-digest", "style=digest-template", "render=pass"),
                ("acquisition", "chart-handoff", "delivery=handoff", "handoff=pass"),
                ("execute", "direct", "persistence=local", "validation=pass"),
                ("sanitize", "report", "publish=none", "report-gate=pass"),
            ):
                result = self.emit(output, "--skill", skill, "--route", route,
                                   "--expected-route", route, "--decision", decision, "--step", step)
                self.assertEqual(result.returncode, 0, result.stderr)
            events = list(map(json.loads, output.read_text().splitlines()))
            self.assertEqual(len(events), 4)
            self.assertTrue(all(event["route_match"] for event in events))


if __name__ == "__main__":
    unittest.main()
