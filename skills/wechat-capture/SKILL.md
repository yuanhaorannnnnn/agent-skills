---
name: wechat-capture
description: Capture public WeChat Official Account articles or albums with text and images into a caller-selected local directory. Use for batch local archiving or downstream use outside Wiki; Wiki ingestion remains owned by acquisition.
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
