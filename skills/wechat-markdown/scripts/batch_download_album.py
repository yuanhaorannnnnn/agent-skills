#!/usr/bin/env python3
"""Continuously download all articles from a WeChat album, resuming on rerun."""

import json, os, subprocess, sys, time
from datetime import date

ALBUM_JSON = "/tmp/album.json"
PROCESSED = "/media/yhr/2T/files/wiki/raw/PROCESSED.md"
OUTPUT_DIR = sys.argv[1] if len(sys.argv) > 1 else "./album-output"
BATCH_SIZE = 5
BATCH_PAUSE = 3  # seconds between batches
ARTICLE_PAUSE = 1  # seconds between articles

SCRIPT = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "wechat_article_to_markdown.py"
)

# Load articles
articles = json.load(open(ALBUM_JSON))
total = len(articles)

# Load already-processed URLs from PROCESSED.md
seen_urls = set()
if os.path.exists(PROCESSED):
    for line in open(PROCESSED):
        for part in line.split("|"):
            if "mp.weixin.qq.com" in part:
                seen_urls.add(part.strip())

# Count remaining
remaining = [a for a in articles if a["url"] not in seen_urls]
print(f"Album: {len(articles)} total, {len(remaining)} remaining")

os.makedirs(OUTPUT_DIR, exist_ok=True)
today = date.today().isoformat()
downloaded = 0

for a in articles:
    if a["url"] in seen_urls:
        print(f"[{a['index']}/{total}] SKIP: {a['title']}")
        continue

    slug = f"{a['index']:03d}-{a['title'][:40].replace('/','-')}"
    outpath = os.path.join(OUTPUT_DIR, f"{slug}.md")

    print(f"[{a['index']}/{total}] DOWNLOAD: {a['title']}")
    result = subprocess.run(
        ["python3", SCRIPT, a["url"], "--output", outpath],
        capture_output=True, text=True,
    )

    if result.returncode == 0:
        downloaded += 1
        with open(PROCESSED, "a") as pf:
            pf.write(f"| {today} | wechat-album | {a['url']} | {slug}.md |\n")
        seen_urls.add(a["url"])
        print(f"  OK -> {slug}.md ({downloaded} in batch)")
        time.sleep(ARTICLE_PAUSE)
    else:
        print(f"  FAILED: {result.stderr[:200]}")

    if downloaded >= BATCH_SIZE:
        downloaded = 0
        remaining_now = [a2 for a2 in articles if a2["url"] not in seen_urls]
        print(f"Batch done. {len(remaining_now)} remaining. Pausing {BATCH_PAUSE}s...")
        print("─" * 50)
        sys.stdout.flush()
        time.sleep(BATCH_PAUSE)

if downloaded == 0:
    print("All articles already downloaded.")
else:
    print(f"Done: {downloaded} new in final batch.")
