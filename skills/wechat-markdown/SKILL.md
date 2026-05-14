---
name: wechat-markdown
description: |
  微信公众号文章转 Markdown。输入 `mp.weixin.qq.com` URL、分享链接文本、
  或公众号名称，输出带元数据的干净 Markdown 文件。触发词："转成 Markdown"、
  "保存这篇公众号"、"把这篇微信文章提取出来"、"wechat to markdown"、
  "convert this WeChat article"。搭配 `wechat-discover` 可以先发现 URL
  再批量转换。
---

# WeChat MP To Markdown

## Overview

Convert public WeChat Official Account articles to clean Markdown with metadata. Prefer direct `mp.weixin.qq.com` article URLs; use account names or local WeChat sources only to discover candidate URLs before extraction.

## Workflow

1. Identify the input type.
   - Direct article URL: any `mp.weixin.qq.com/s/...` or `mp.weixin.qq.com/mp/appmsgalbum?...` URL.
   - Copied share text: extract the first `mp.weixin.qq.com` URL from the text.
   - Account name: search local WeChat data or ask the user for a concrete article URL if local search is unavailable.
   - Non-WeChat web page: use a general web extraction workflow instead of this skill.

2. Resolve URLs.
   - For one URL, run `scripts/wechat_article_to_markdown.py "<URL>"`.
   - For several URLs, run the script once per URL and keep each article as a separate Markdown document.
   - For account names, first try `wechat-cli search "<account or keyword>" --type link --limit 50` only if `wechat-cli` is installed and initialized. Extract `mp.weixin.qq.com` links from the structured JSON/text output, then process those URLs.

3. Convert and inspect output.
   - Success: return or save the generated Markdown exactly as requested.
   - Verification/captcha/login/paid content: stop after one failed fetch and explain that the public HTML was not available.
   - Empty content: retry only if the URL was malformed or truncated; otherwise ask for the original share link.

4. Persist results when requested.
   - If the user asks to save, write `.md` files using the article title slug or the provided destination.
   - Preserve YAML frontmatter emitted by the script unless the user requests a different format.

## Script Usage

```bash
python3 "$SKILL_DIR/scripts/wechat_article_to_markdown.py" "https://mp.weixin.qq.com/s/..."
python3 "$SKILL_DIR/scripts/wechat_article_to_markdown.py" "https://mp.weixin.qq.com/s/..." --output article.md
python3 "$SKILL_DIR/scripts/wechat_article_to_markdown.py" "copied share text with a URL" --json
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
