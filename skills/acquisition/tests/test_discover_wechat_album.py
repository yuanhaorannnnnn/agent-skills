import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "discover_wechat_album.py"
SPEC = importlib.util.spec_from_file_location("discover_wechat_album", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


ALBUM_URL = (
    "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=biz-value&action=getalbum"
    "&album_id=123456&scene=178#wechat_redirect"
)
ARTICLE_URL = "http://mp.weixin.qq.com/s?__biz=biz-value&mid=99&idx=1&sn=abc#rd"


class WeChatAlbumDiscoveryTests(unittest.TestCase):
    def test_album_url_is_canonicalized_without_viewer_noise(self):
        self.assertEqual(
            MODULE.canonical_album_url(ALBUM_URL),
            "https://mp.weixin.qq.com/mp/appmsgalbum?__biz=biz-value&action=getalbum&album_id=123456",
        )
        with self.assertRaises(ValueError):
            MODULE.validate_album_url(ARTICLE_URL)

    def test_article_urls_are_normalized_and_identified_by_article_identity(self):
        normalized = "https://mp.weixin.qq.com/s?__biz=biz-value&mid=99&idx=1&sn=abc"
        self.assertEqual(MODULE.normalize_article_url(ARTICLE_URL), normalized)
        self.assertEqual(MODULE.article_identity(ARTICLE_URL), "biz-value:99:1")

    def test_manifest_deduplicates_items_and_reports_completeness(self):
        browser_data = {
            "title": "测试专辑",
            "body": "测试专辑\n2 items",
            "items": [
                {"url": ARTICLE_URL, "text": "2. 最新文章\n1 week ago"},
                {"url": ARTICLE_URL, "text": "2. 最新文章\n1 week ago"},
                {
                    "url": "https://mp.weixin.qq.com/s?__biz=biz-value&mid=98&idx=1&sn=def",
                    "text": "1. 更早文章\n2026-08-01",
                },
            ],
        }
        manifest = MODULE.compile_manifest(ALBUM_URL, browser_data)
        self.assertEqual(manifest["declared_items"], 2)
        self.assertEqual(manifest["discovered_items"], 2)
        self.assertEqual(manifest["duplicates_removed"], 1)
        self.assertTrue(manifest["complete"])
        self.assertEqual(manifest["items"][0]["title"], "最新文章")


if __name__ == "__main__":
    unittest.main()
