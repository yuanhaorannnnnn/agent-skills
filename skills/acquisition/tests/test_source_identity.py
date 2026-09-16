import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "source_identity.py"
SPEC = importlib.util.spec_from_file_location("source_identity", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(MODULE)


class SourceIdentityTests(unittest.TestCase):
    def test_canonical_url_removes_viewer_noise(self):
        self.assertEqual(
            MODULE.canonical_url("https://www.x.com/example/status/1?s=20&utm_source=test#part"),
            "https://x.com/example/status/1",
        )

    def test_detects_same_source_across_clipping_and_raw(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "raw" / "clippings").mkdir(parents=True)
            existing = root / "raw" / "clippings" / "saved.md"
            existing.write_text("---\nsource_url: https://example.com/post?utm_source=x\n---\nBody\n")
            incoming = root / "incoming.md"
            incoming.write_text("---\nsource: https://example.com/post#reader\n---\nBody\n")
            result = MODULE.inspect(root, "", incoming)
            self.assertTrue(result["duplicate"])
            self.assertEqual(result["matches"][0]["match"], "canonical_url+content_hash")


if __name__ == "__main__":
    unittest.main()
