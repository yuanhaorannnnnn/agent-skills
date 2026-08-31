import datetime as dt
import importlib.util
from pathlib import Path
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "ingest_wechat_article.py"
SPEC = importlib.util.spec_from_file_location("ingest_wechat_article", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class WeChatFallbackTests(unittest.TestCase):
    def test_only_accepts_public_wechat_article_urls(self):
        url = "https://mp.weixin.qq.com/s/example?foo=bar"
        self.assertEqual(MODULE.validate_wechat_url(url), url)
        with self.assertRaises(ValueError):
            MODULE.validate_wechat_url("http://mp.weixin.qq.com/s/example")
        with self.assertRaises(ValueError):
            MODULE.validate_wechat_url("https://example.com/s/example")

    def test_raw_name_is_url_stable(self):
        self.assertEqual(
            MODULE.canonical_stem("https://mp.weixin.qq.com/s/example", dt.date(2026, 8, 31)),
            "20260831-wechat-e9514928359e",
        )

    def test_cli_headers_are_not_repeated_in_canonical_body(self):
        article = "\n".join(
            [
                "# 测试文章",
                "",
                "> 公众号: 测试作者",
                "> 发布时间: 2026-08-31 10:00:00",
                "> 原文链接: https://mp.weixin.qq.com/s/example",
                "",
                "---",
                "",
                "正文" * 120,
            ]
        )
        title, author, published, body = MODULE.parse_cli_markdown(
            article, "https://mp.weixin.qq.com/s/example"
        )
        self.assertEqual((title, author, published), ("测试文章", "测试作者", "2026-08-31 10:00:00"))
        self.assertFalse(body.startswith("> 公众号:"))
        self.assertTrue(body.startswith("正文"))

    def test_local_images_are_rebased_beneath_the_raw_article(self):
        body = "![图](images/img_001.png)\n![远图](https://example.com/a.png)"
        self.assertEqual(
            MODULE.rewrite_image_paths(body, "20260831-wechat-abc"),
            "![图](images/20260831-wechat-abc/img_001.png)\n![远图](https://example.com/a.png)",
        )


if __name__ == "__main__":
    unittest.main()
