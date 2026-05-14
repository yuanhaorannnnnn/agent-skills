---
name: wechat-discover
description: |
  发现微信公众号文章 URL。输入公众号名称、关键词或日期范围，输出
  `mp.weixin.qq.com` 文章链接列表。依赖 Tavily API。触发词：
  "搜索 XX 公众号的文章"、"找 XX 相关的微信文章"、"发现公众号 URL"、
  "wechat discover"、"find WeChat articles"。搭配 `wechat-markdown`
  批量转换为 Markdown。
---

# WeChat MP URL Discovery

## Overview

Find candidate WeChat Official Account article URLs and write them to `urls.txt` or `urls.json`. This skill does discovery only; use `wechat-markdown` afterward to convert the URLs into Markdown.

## Workflow

1. Choose the input.
   - Latest articles from one account: use `--account "公众号名" --latest`.
   - Topic search: use `--query "关键词"` only when the user explicitly asks for a topic.
   - Date filtering: add `--since YYYY-MM-DD` and/or `--until YYYY-MM-DD`.

2. Run the Tavily search script.

```bash
TAVILY_API_KEY=... python3 "$SKILL_DIR/scripts/wechat_discover_urls.py" \
  --account "智能车参考" \
  --latest \
  --limit 20 \
  --candidate-limit 60 \
  --output urls.txt \
  --json-output urls.json \
  --report discovery_report.md
```

3. Inspect the report.
   - Keep rows with `verified: True` and the expected account name.
   - Treat unverified titles/accounts from search snippets as hints, not ground truth.
   - Do not add title/topic terms like `Waymo` unless the user explicitly asks for that topic.

4. Convert articles.

```bash
while IFS= read -r url; do
  python3 "$SKILL_DIR/../wechat-markdown/scripts/wechat_article_to_markdown.py" "$url" --output "articles/$(basename "$url").md"
done < urls.txt
```

## API Key Handling

- Read the Tavily key from `TAVILY_API_KEY` or pass it with `--api-key` only for one-off runs.
- Do not write API keys into skill files, reports, URL lists, shell scripts, or Markdown outputs.
- If a key was pasted into chat or logs, recommend rotating it after the workflow is working.

## Search Strategy

For account-latest requests, the script generates account-only bounded queries such as:

```text
site:mp.weixin.qq.com/s "<account>" "公众号"
"<account> | 公众号" "mp.weixin.qq.com/s"
"<account>" "公众号" "mp.weixin.qq.com/s"
```

Then `--latest` fetches candidate articles, verifies the actual WeChat account metadata, filters mismatches, and sorts by article publish date descending. Topic terms belong only in `--query` when the user explicitly asks for a topical search.

## Limits

- Discovery depends on search-engine indexing. It cannot guarantee complete article history for a公众号.
- It does not bypass WeChat login, captcha, follower-only content, deleted articles, or paywalls.
- Search APIs can return duplicates, stale links, or syndicated copies; verify by running `wechat-markdown` on the generated URLs.

Read `references/tavily-notes.md` before changing the Tavily request shape or adding browser automation fallback.
