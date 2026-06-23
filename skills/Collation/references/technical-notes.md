# Technical Notes

## Source Assessment

- `rrrrrredy/wechat-reader`: closest prior art. It documents direct `mp.weixin.qq.com` fetching with a mobile WeChat User-Agent, article metadata extraction, and Markdown conversion. Treat it as the baseline concept, but keep this skill runtime-agnostic and avoid hardcoded proxy assumptions.
- `huohuoer/wechat-cli`: useful for discovering links from local WeChat data, chat history, favorites, or account-related messages. It is not a public-account article parser and may require local WeChat access, initialization, permissions, or platform-specific setup.
- `kepano/defuddle`: useful general page readability extractor that can return Markdown and metadata. It is best as a fallback for generic web pages or saved HTML, not as the primary WeChat path.

## Extraction Strategy

1. Fetch the public HTML with a mobile WeChat User-Agent.
2. Detect unavailable pages early by scanning for verification, login, deletion, or access-limited markers.
3. Extract metadata from WeChat selectors and inline JavaScript variables:
   - Title: `#activity-name`, `og:title`, `<title>`.
   - Account/author: `#js_name`, `author`, `og:article:author`.
   - Publish time: `publish_time`, `ct`, or meta dates where present.
   - Body: `#js_content`, then `article`, then readability-like fallback.
4. Convert WeChat `code-snippet` DOM blocks to fenced Markdown code blocks before generic HTML conversion.
5. Convert the selected content to Markdown.
6. Optionally download reachable images to a local `images/` directory and rewrite Markdown image links.
7. Emit YAML frontmatter plus body Markdown by default.

## Failure Policy

Stop on access-control failures. The skill is for converting public articles, not for evading WeChat restrictions. If public HTML is unavailable, ask the user for another link or for copied article text.

## Account Name Inputs

Account names are not stable article identifiers. Use them only to discover URLs:

```bash
wechat-cli search "<account-or-keyword>" --type link --limit 50
wechat-cli favorites --type article
wechat-cli history "<chat-name>" --type link --limit 100
```

Then extract `mp.weixin.qq.com` URLs from the output and run the normal conversion script.


## Optional Image Localization

`wechat_article_to_markdown.py --download-images` scans Markdown image links, downloads reachable HTTP(S) images with a WeChat mobile User-Agent and `Referer: https://mp.weixin.qq.com/`, writes sequential `img_NNN.<ext>` files, and rewrites links to the local images directory. Failed image downloads are warnings, not extraction failures.

## Code Snippet Preservation

When BeautifulSoup is available, WeChat `.code-snippet` / `.code-snippet__fix` blocks are converted to fenced Markdown code blocks before `markdownify` runs. The converter removes line-number/copy UI elements and preserves `pre[data-lang]` as the fence language.
