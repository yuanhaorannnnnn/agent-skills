# WeChat account article discovery

Use this when the request is "find the account's other articles", not "capture
this URL". Discovery is a separate, bounded step. It is not a full-history API:
WeChat's account history endpoints require a logged-in session, so public
surfaces only yield a subset.

## Establish the account identity

The reliable input is one article URL from the account. Load it in Camoufox and
read the page variables:

```text
var biz = "MzI0MDg4NzAwMA=="
var mid = "2247527713"
var idx = "1"
var sn  = "..."
var user_name = "gh_f1e180216de1"
```

An account name alone is not reliably resolvable to `__biz`. Sogou's account
search (`type=1`) often returns no profile; that is not proof of absence.
Record `__biz`, nickname, and the article URL that supplied them.

Do not inspect browser history, cookies, or a logged-in WeChat session unless
the caller explicitly authorizes it. Ask for the album or article URL instead.

## Public surfaces

Use these in order and keep the source of every item. None of them is complete.

### 1. Custom homepage pages

```text
https://mp.weixin.qq.com/mp/homepage?__biz=<BIZ>&hid=<N>
```

Probe `N = 1..12`. A valid page contains a title like `法国当季精选` and a data
block:

```python
m = re.search(r'var data=(\{"appmsg_list".*?\});', html, re.S)
items = json.loads(m.group(1))["appmsg_list"]
```

Fields include `title`, `link`, `sendtime`, `digest`, `itemidx`. Normalize
`http` to `https`, unescape `&amp;`, and treat the page as a curated list that
may be stale. A page returning an error or a small page without `appmsg_list`
is absent.

### 2. Album pages

```text
https://mp.weixin.qq.com/mp/appmsgalbum?__biz=<BIZ>&action=getalbum&album_id=<ID>
```

Only use an album URL supplied by the caller or linked from a discovered page.
Do not derive it from local browser data without permission. Some video albums
do not expose a declared item count; discovery then cannot establish
completeness. Do not claim a complete album in that case.

### 3. Sogou WeChat search

```text
https://weixin.sogou.com/weixin?type=2&query=<KEYWORD>
```

Use the account nickname and distinctive words from article bodies (for example
the author's pen name) as queries. Parse result blocks:

- account: `span.all-time-y2`
- date: `timeConvert('<unix>')`
- link: `h3 a[href]`, a relative `/link?url=...&token=...`

Filter by exact account name and dedupe by normalized title. Search results are
sparse and pagination often returns nothing after page 1.

The `/link` URL is a JS redirect and `curl` normally lands on an anti-spider
page. Resolve it in a real browser context, for example Camoufox, with the Sogou
search page as referer. A successful resolve ends at:

```text
https://mp.weixin.qq.com/s?src=11&timestamp=...&ver=...&signature=...&poc_token=...
```

Feed that URL to `capture.py` immediately; the signature and token are
short-lived. If the resolve lands on `wappoc_appmsgcaptcha` or the page shows
`环境异常`, stop that item. Do not solve the captcha or reuse an authenticated
session.

### 4. Web search

Exact-title queries can surface canonical article URLs:

```text
https://mp.weixin.qq.com/s?__biz=...&mid=...&idx=...&sn=...
```

This is useful for recent or notable posts but is not an account index.

## Dedupe and manifest

Normalize titles before dedupe: HTML-unescape, strip tags, punctuation, and
whitespace. Dedupe by `mid` when available.

Write a discovery manifest (JSON or Markdown) with one row per article:

```json
{
  "source": "homepage:hid=1",
  "title": "...",
  "url": "https://mp.weixin.qq.com/s?...",
  "date": "2023-10-31",
  "status": "captured | blocked | skipped"
}
```

Report per-source counts and the unique total. Say "discovered", not "all".
Make clear that the result is a union of public surfaces, not the account's
complete history.

## Capture and stop rules

- Capture only after the caller confirms the output directory and batch size,
  or the calling workflow supplies them.
- Capture signed Sogou URLs immediately; they expire.
- A verification page is a stop condition for that item, not a retry loop.
  Report the item as blocked and keep the rest.
- Native Camoufox crashes are intermittent. Retry an item a few times at most,
  then report it; do not silently drop it.
- Never inject cookies or accounts, solve captchas, or use a logged-in session
  to bypass access restrictions.

## Special cases

- Video posts may have `#js_content` but no `#activity-name`; the standard
  extractor can fail. A metadata-only record is acceptable only if it is
  labeled `video-only`; do not present it as a full text capture.
- Old homepage links without `chksm` are more likely to hit a verification
  page. That is an access condition, not proof that the item is a video.
- Image-heavy articles can crash the extractor. Report the failure and retain
  successful items.

## Reporting template

```text
Discovered N unique articles from S sources:
- homepage:hid=1/2/4/6 — A (B before dedupe)
- sogou:<query> — C
- web:<query> — D
- album:<id> — E
Captured M; blocked K (reasons).
This is a public-surface union, not the account's complete history.
```
