"""Exercise the public gate, including honest limits and invalid provenance."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


GATE = Path(__file__).resolve().parents[1] / "skills/cover/scripts/synthesis_gate.py"


class CoverGateTests(unittest.TestCase):
    def run_gate(self, evidence, design=None):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "DESIGN.md").write_text(design or (
                "# Example\ncolors:\n  ink: '#111111'\ntypography:\n"
                "  body: 'sans-serif'\n" + "A concrete project design. " * 6
            ))
            (root / "evidence.json").write_text(json.dumps(evidence))
            result = subprocess.run(
                [sys.executable, str(GATE), "--design", str(root / "DESIGN.md"),
                 "--evidence", str(root / "evidence.json"), "--json"],
                capture_output=True, text=True,
            )
            return result.returncode, json.loads(result.stdout)

    def test_legacy_and_film_references_remain_valid(self):
        for refs in (["a/DESIGN.md", "b/DESIGN.md"],
                     ["https://example.org/film", "project/DESIGN.md"]):
            code, result = self.run_gate({"references_studied": refs, "wholesale_copy": False})
            self.assertEqual(code, 0)
            self.assertEqual(result["check_kind"], "structure_lint")
            self.assertEqual(result["artistic_review"], "required")

    def test_copy_and_absent_or_nonboolean_attestation_block(self):
        for value in (True, None, "false", 0):
            code, result = self.run_gate({"references_studied": ["a", "b"], "wholesale_copy": value})
            self.assertEqual(code, 1)
            self.assertEqual(result["verdict"], "blocked")

    def test_invalid_or_duplicate_sources_do_not_count(self):
        for refs in ("ab", [], ["a"], ["a", "a"], ["a", " a "], ["a", ""], ["a", {}], None):
            with self.subTest(refs=refs):
                code, result = self.run_gate({"references_studied": refs, "wholesale_copy": False})
                self.assertEqual(code, 1)
                self.assertEqual(result["verdict"], "blocked")

    def test_extra_references_are_warning_not_failure(self):
        code, result = self.run_gate({"references_studied": list("abcde"), "wholesale_copy": False})
        self.assertEqual(code, 0)
        self.assertTrue(any("max_refs" in f for f in result["failed"]))

    def test_missing_design_tokens_block(self):
        code, _ = self.run_gate({"references_studied": ["a", "b"], "wholesale_copy": False}, "# Empty")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
