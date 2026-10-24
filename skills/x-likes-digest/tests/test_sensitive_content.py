import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    "digest", Path(__file__).resolve().parents[1] / "scripts/x_likes_digest.py"
)
digest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(digest)


class SensitiveContentTests(unittest.TestCase):
    def test_known_adult_posts_are_detected(self):
        samples = (
            "JAV Verse现已补足无码和中文字幕",
            "推荐一下极品女优；我决定每天看她 打一次✈️",
            "fullwidth ＮＳＦＷ and ｐｏｒｎ",
            "nude note tweet",
        )
        self.assertTrue(all(digest.has_sensitive_signal(sample) for sample in samples[:3]))
        self.assertTrue(
            digest.is_sensitive(
                {"text": "ordinary short text", "note_tweet": {"text": samples[3]}},
            )
        )

    def test_media_alt_text_is_part_of_sensitive_classification(self):
        self.assertTrue(
            digest.is_sensitive(
                {"text": "ordinary photo caption"},
                [{"type": "photo", "alt_text": "adult nude image"}],
            )
        )

    def test_sensitive_post_html_hides_text_media_and_author(self):
        raw_text = "推荐一下极品女优；我决定每天看她 打一次✈️"
        post = {
            "id": "123",
            "author_id": "author-1",
            "text": raw_text,
            "attachments": {"media_keys": ["media-1"]},
        }
        includes = {
            "users": {"author-1": {"username": "adult_account"}},
            "media": {
                "media-1": {
                    "type": "photo",
                    "url": "https://pbs.twimg.com/media/sensitive.jpg",
                }
            },
        }
        document = digest.build_html([post], includes, "issue", 1, 1, "2026.10.23")
        self.assertIn(digest.SENSITIVE_MARKER, document)
        self.assertIn("https://x.com/adult_account/status/123", document)
        self.assertNotIn(raw_text, document)
        self.assertNotIn("@adult_account", document)
        self.assertNotIn("sensitive.jpg", document)
        digest.validate_html_safety(document)

    def test_pending_html_gate_rejects_unmasked_adult_content(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            part = root / "part-1.html"
            manifest = root / "pending.json"
            part.write_text("<html><body>JAV Verse：无码影片</body></html>", encoding="utf-8")
            manifest.write_text(
                json.dumps({"parts": [{"html_path": str(part)}]}), encoding="utf-8"
            )
            with self.assertRaisesRegex(ValueError, "sensitive-content gate"):
                digest.validate_pending(manifest)

    def test_html_gate_catches_terms_split_by_markup(self):
        with self.assertRaisesRegex(ValueError, "sensitive-content gate"):
            digest.validate_html_safety("<p>JAV</p><p>Verse<span>无码</span></p>")


if __name__ == "__main__":
    unittest.main()
