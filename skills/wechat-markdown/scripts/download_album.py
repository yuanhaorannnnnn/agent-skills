#!/usr/bin/env python3
"""Download article list from a WeChat Official Account album (合集).

Usage:
  python download_album.py "https://mp.weixin.qq.com/mp/appmsgalbum?..."
  python download_album.py "<album-url>" --json

Parses a WeChat album page, paginates through all articles, and outputs:
- Default: human-readable article list with index, title, url, publish time
- --json: JSON array of article objects suitable for batch processing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from urllib.parse import urlparse, parse_qs
from urllib.request import Request, urlopen


API_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "X-Requested-With": "XMLHttpRequest",
}


def parse_album_url(raw: str) -> dict | None:
    """Extract __biz, album_id, scene from a WeChat album URL."""
    url = raw.strip().strip('"').strip("'")
    if not url.startswith("http"):
        url = "https://" + url.lstrip("/")
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        biz = params.get("__biz", [None])[0]
        album_id = params.get("album_id", [None])[0]
        scene = params.get("scene", ["126"])[0]
        if biz and album_id:
            return {"biz": biz, "album_id": album_id, "scene": scene}
    except Exception:
        pass
    return None


def fetch_album_page(biz: str, album_id: str, count: int = 20,
                     cursor: dict | None = None) -> dict:
    """Fetch one page of the album article list. Returns parsed response dict."""
    api = (
        f"https://mp.weixin.qq.com/mp/appmsgalbum?"
        f"action=getalbum&__biz={biz}&album_id={album_id}"
        f"&count={count}&f=json"
    )
    if cursor:
        api += f"&begin_msgid={cursor['msgid']}&begin_itemidx={cursor['itemidx']}"

    req = Request(api, headers=API_HEADERS)
    with urlopen(req) as resp:
        raw = resp.read().decode("utf-8", errors="ignore")

    # Handle WeChat's non-standard JSON (sometimes includes Unicode escapes)
    # Also handle the case where the response might have a BOM or extra chars
    raw = raw.lstrip("﻿").strip()
    data = json.loads(raw)

    base_resp = data.get("base_resp", {})
    if base_resp.get("ret", 0) != 0:
        raise RuntimeError(f"API returned error: ret={base_resp.get('ret')}")

    getalbum = data.get("getalbum_resp", {})
    base_info = getalbum.get("base_info", {})
    article_list = getalbum.get("article_list", [])

    # Normalize article_list — it may be array, dict, or nested
    articles = []
    if isinstance(article_list, list):
        articles = article_list
    elif isinstance(article_list, dict):
        articles = [v for v in article_list.values()
                     if isinstance(v, dict) and "title" in v]

    return {
        "album_title": base_info.get("title", album_id),
        "articles": articles,
        "continue_flag": getalbum.get("continue_flag", "") == "1",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="List all articles in a WeChat Official Account album"
    )
    parser.add_argument("url", help="WeChat album URL (mp.weixin.qq.com/mp/appmsgalbum)")
    parser.add_argument("--json", action="store_true",
                        help="Output JSON array of articles (suitable for batch download)")
    parser.add_argument("--batch-size", type=int, default=20,
                        help="Articles per API call (max 20)")
    args = parser.parse_args()

    parsed = parse_album_url(args.url)
    if not parsed:
        print("Error: could not parse album URL — need __biz and album_id params",
              file=sys.stderr)
        return 1

    biz = parsed["biz"]
    album_id = parsed["album_id"]
    batch = min(args.batch_size, 20)

    all_articles = []
    cursor = None
    album_title = album_id

    while True:
        page = fetch_album_page(biz, album_id, batch, cursor)
        articles = page["articles"]
        if not articles:
            break
        if page["album_title"] and album_title == album_id:
            album_title = page["album_title"]
        all_articles.extend(articles)

        last = articles[-1]
        cursor = {"msgid": last.get("msgid", ""), "itemidx": last.get("itemidx", "")}
        if not page["continue_flag"]:
            break
        time.sleep(1 + time.time() % 2)  # rate-limit between pages

    # Normalize each article to a clean dict
    result = []
    for a in all_articles:
        url = a.get("url", "").replace("http://", "https://")
        title = a.get("title", "")
        create_time = a.get("create_time", "")
        pub_time = "-"
        if create_time:
            try:
                ts = int(create_time)
                pub_time = time.strftime("%Y-%m-%d", time.gmtime(ts))
            except (ValueError, OSError):
                pub_time = str(create_time)
        result.append({
            "index": len(result) + 1,
            "title": title,
            "url": url,
            "create_time": create_time,
            "publish_time": pub_time,
        })

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"专辑: {album_title}")
        print(f"文章数: {len(result)}")
        print(f"{'─'*70}")
        for a in result:
            print(f"[{a['index']:3d}] {a['title']}")
            print(f"      {a['url']}")
            print(f"      发布于: {a['publish_time']}")
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
