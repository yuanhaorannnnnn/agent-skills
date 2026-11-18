---
name: wechat-capture
description: Capture public WeChat Official Account articles or albums with text and images, and discover an account's other public articles from public surfaces, into a caller-selected local directory. Use for batch local archiving or downstream use outside Wiki; Wiki ingestion remains owned by acquisition.
---

# WeChat capture

Capture public articles, or a bounded selection of a public album, without generating Wiki queries. Confirm the output directory and batch size from the request or calling workflow; do not assume a Wiki or website destination. Do not publish or upload the result unless separately authorized.

```bash
python3 <skill-dir>/scripts/capture.py 'ARTICLE_URL' --output OUTPUT_DIR
python3 <skill-dir>/scripts/capture.py 'ALBUM_URL' --output OUTPUT_DIR --limit N --order latest
```

The existing `wechat-article-to-markdown` and Camoufox installation is required. A capture has `article.md`, `images/` when present, and `manifest.json` recording source, metadata, image counts and missing references. Existing destinations are never overwritten. Album discovery must establish the declared count before selecting articles. Report each error or partial image capture, and retain successful results; do not claim a complete batch when any article failed.

`image_status: checked` means extractor-reported image counts and Markdown references were checked for nonempty files; it does not establish image decoding or that the extractor detected all original content. Body and embedded media completeness remain unverified. Inspect actual output and compare with the source when the task requires faithful reproduction. Video, audio, dynamic widgets and original page styling are not guaranteed. Respect source access restrictions; do not use accounts or cookies to bypass them.

For Wiki ingestion use acquisition's identity, source and query contracts; do not put captures in Wiki or on a homepage merely because a capture succeeded. Existing acquisition fallback remains available and unchanged.

## Account discovery

When the request is to find an account's other articles, read `references/account-discovery.md` before collecting URLs. Discovery is a separate, best-effort step that uses public surfaces: custom homepage pages, album pages, Sogou WeChat search, and web search. It is not the account's complete history.

Keep the source of every discovered item, dedupe by normalized title or `mid`, and report per-source counts, captured items, and blocked items. Say "discovered", not "all". Do not inspect browser history, cookies, or a logged-in session unless the caller explicitly authorizes it; do not bypass verification pages.

## Proxy parsing before capture

If the installed Python runtime raises `httpx.InvalidURL: Invalid port: ':1]'` before making a request, check for an exact `[::1]` entry in `NO_PROXY` or `no_proxy`. For this compatibility case, normalize that entry to `::1` in the capture subprocess environment only; preserve all other entries and proxy settings. This retains the IPv6 loopback proxy exemption instead of deleting it. Do not change the system environment or use this correction to retry a page explicitly denied by a tool or site policy.

Validate client initialization without a network request first. This correction does not resolve Camoufox/native-process crashes, incomplete album discovery, or verification pages; keep those failures separate and retain their evidence.
