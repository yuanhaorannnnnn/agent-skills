---
name: Collation
description: |
  微信公众号文章转 Markdown。输入 `mp.weixin.qq.com` URL、分享链接文本、
  或公众号名称，输出带元数据的干净 Markdown 文件。支持合集（album）批量下载。
  触发词："转成 Markdown"、"保存这篇公众号"、"把这篇微信文章提取出来"、
  "wechat to markdown"、"convert this WeChat article"、
  "下载这个合集"、"批量下载公众号文章"。搭配 `wechat-discover` 可以先发现 URL
  再批量转换。
---

# WeChat MP To Markdown

## Overview

Convert public WeChat Official Account articles to clean Markdown with metadata. Prefer direct `mp.weixin.qq.com` article URLs; use account names or local WeChat sources only to discover candidate URLs before extraction. Album (合集) URLs are supported for batch download of all articles.

## Workflow

1. Identify the input type.
   - Single article URL: `mp.weixin.qq.com/s/...`
   - Album URL: `mp.weixin.qq.com/mp/appmsgalbum?...` (合集 — batch download all articles)
   - Copied share text: extract the first `mp.weixin.qq.com` URL from the text.
   - Account name: search local WeChat data or ask the user for a concrete article URL if local search is unavailable.
   - Non-WeChat web page: use a general web extraction workflow instead of this skill.

2. Resolve URLs.
   - **Album URL**: run `scripts/download_album.py "<URL>"` to get the article list, then run `scripts/wechat_article_to_markdown.py` for each article. Use `--json` for machine-readable article list.
   - **Single article**: run `scripts/wechat_article_to_markdown.py "<URL>"`.
   - **Several article URLs**: run the script once per URL, keep each as a separate `.md`.
   - **Account names**: first try `wechat-cli search` only if available. Extract URLs, then process.

3. Album batch download flow:
   ```bash
   # Step 1: Get the article list
   python3 scripts/download_album.py "https://mp.weixin.qq.com/mp/appmsgalbum?..." --json > /tmp/album.json

   # Step 2: Download each article, skipping already-downloaded ones
   python3 -c "
   import json, os, sys, subprocess
   from datetime import date

   output_dir = './album-output'
   os.makedirs(output_dir, exist_ok=True)
   processed = '/media/yhr/2T/files/wiki/raw/PROCESSED.md'

   # Load already-processed source URLs
   seen_urls = set()
   if os.path.exists(processed):
       for line in open(processed):
           for part in line.split('|'):
               if 'mp.weixin.qq.com' in part:
                   seen_urls.add(part.strip())

   articles = json.load(open('/tmp/album.json'))
   today = date.today().isoformat()
   new_count = 0

   with open(processed, 'a') as pf:
       for a in articles:
           if a['url'] in seen_urls:
               print(f'[{a[\"index\"]}/{len(articles)}] SKIP: {a[\"title\"]}')
               continue

           slug = f\"{a['index']:03d}-{a['title'][:40].replace('/','-')}\"
           outpath = os.path.join(output_dir, f'{slug}.md')
           print(f'[{a[\"index\"]}/{len(articles)}] DOWNLOAD: {a[\"title\"]}')
           result = subprocess.run([
               'python3', 'scripts/wechat_article_to_markdown.py',
               a['url'], '--output', outpath
           ])
           if result.returncode == 0:
               new_count += 1
               pf.write(f'| {today} | wechat-album | {a[\"url\"]} | {slug}.md |\n')
               seen_urls.add(a['url'])

           if new_count >= 5:
               print('Reached 5 new downloads — stop. Rerun to continue.')
               break

   print(f'Done: {new_count} new, {len(articles)} total')
   "
   ```
   - Dedup against `/media/yhr/2T/files/wiki/raw/PROCESSED.md` — articles with matching URL are skipped.
   - New downloads are automatically appended to PROCESSED.md.
   - Safety cap (5 per batch) avoids rate-limiting. Rerun to continue.

4. Convert and inspect output.
   - Success: return or save the generated Markdown exactly as requested.
   - Verification/captcha/login/paid content: stop after one failed fetch and explain.
   - Empty content: retry only if the URL was malformed; otherwise ask for the original share link.
   - Album pagination: the script handles pagination automatically with 1-3s rate-limit between pages.

5. Persist results when requested.
   - If the user asks to save, write `.md` files using the article title slug or the provided destination.
   - Preserve YAML frontmatter emitted by the script unless the user requests a different format.
   - For albums, save all articles in a subdirectory named after the album title.

## Script Usage

```bash
# Single article
python3 "$SKILL_DIR/scripts/wechat_article_to_markdown.py" "https://mp.weixin.qq.com/s/..."
python3 "$SKILL_DIR/scripts/wechat_article_to_markdown.py" "https://mp.weixin.qq.com/s/..." --output article.md

# Album batch
python3 "$SKILL_DIR/scripts/download_album.py" "https://mp.weixin.qq.com/mp/appmsgalbum?..."
python3 "$SKILL_DIR/scripts/download_album.py" "https://mp.weixin.qq.com/mp/appmsgalbum?..." --json
```

When `$SKILL_DIR` is unavailable, use `~/.agents/skills/wechat-markdown` or the runtime-appropriate skill path.

## Tool Selection

- Use `scripts/wechat_article_to_markdown.py` as the default extractor for public article URLs.
- Use `wechat-cli` only as an optional local URL discovery layer for account names, chat history, or favorites. Do not require it for direct URLs.
- Use `defuddle` or another general readability extractor only after saving fetched HTML for a non-WeChat or malformed page; it is not the default path for WeChat because WeChat-specific metadata selectors are more reliable.

Read `references/technical-notes.md` before changing the extraction approach, adding dependencies, or debugging repeated failures.

## Limits

- Do not bypass WeChat access controls, paywalls, login walls, follower-only content, or captcha.
- Do not loop through proxy/User-Agent combinations. One normal fetch attempt is enough unless the user provides a new URL.
- Images may be kept as remote URLs in Markdown, but WeChat CDN hotlinking can prevent later rendering. Do not promise that image downloads will work.
