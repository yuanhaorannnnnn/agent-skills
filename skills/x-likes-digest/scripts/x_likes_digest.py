#!/usr/bin/env python3
"""X likes weekly digest: baseline, incremental fetch, HTML build, state update."""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

APP = "x-bookmark-ingest"
XURL = ["npx", "-y", "@xdevplatform/xurl", "--app", APP]
TZ = timezone(timedelta(hours=8))

STATE_DIR = Path.home() / ".codex" / "automations" / "x-likes"
STATE_PATH = STATE_DIR / "state.json"
ISSUES_DIR = STATE_DIR / "issues"
MEMORY_PATH = STATE_DIR / "memory.md"

MAX_ITEMS_PER_MAIL = 60
MAX_HTML_BYTES = 95_000
SAFETY_PAGE_CAP = 20
BASELINE_PAGE_CAP = 80

POST_FIELDS = (
    "tweet.fields=created_at,author_id,text,entities,note_tweet,attachments,"
    "lang,public_metrics,possibly_sensitive,referenced_tweets"
)
EXPANSIONS = "expansions=author_id,attachments.media_keys,referenced_tweets.id"
MEDIA_FIELDS = (
    "media.fields=type,url,preview_image_url,alt_text,width,height,"
    "duration_ms,variants,public_metrics"
)
USER_FIELDS = "user.fields=username,name,description,public_metrics,verified"

SENSITIVE_PAT = re.compile(
    r"(porn|pornhub|nsfw|nude|裸|色情|成人|女菩萨|91\b|SNOS-|IPZZ-|"
    r"亚洲马桶|烂裤裆|后宫文)",
    re.I,
)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def run_xurl(path: str) -> dict:
    proc = subprocess.run(
        XURL + [path], capture_output=True, text=True, timeout=180
    )
    if proc.returncode != 0:
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict) and payload.get("status") == 402:
            raise RuntimeError(
                "X API credits depleted (402): "
                f"{payload.get('detail') or 'Payment Required'}. "
                "Top up the X Developer account, then rerun baseline."
            )
        raise RuntimeError(
            f"xurl failed ({proc.returncode}): {proc.stderr.strip()[:500]}"
        )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"xurl returned non-JSON: {proc.stdout[:500]}"
        ) from exc


def get_me() -> dict:
    data = run_xurl("/2/users/me")
    user = data.get("data") or {}
    if not user.get("id"):
        raise RuntimeError("cannot resolve X user id")
    return user


def liked_url(uid: str, token: str | None = None, max_results: int = 100) -> str:
    path = (
        f"/2/users/{uid}/liked_tweets?max_results={max_results}"
        f"&{POST_FIELDS}&{EXPANSIONS}&{MEDIA_FIELDS}&{USER_FIELDS}"
    )
    if token:
        path += f"&pagination_token={token}"
    return path


def fetch_page(uid: str, token: str | None = None, max_results: int = 100) -> dict:
    return run_xurl(liked_url(uid, token, max_results))


def merge_includes(target: dict, payload: dict) -> None:
    includes = payload.get("includes") or {}
    for key in ("users", "media", "tweets"):
        values = includes.get(key) or []
        if isinstance(values, dict):
            values = list(values.values())
        for item in values:
            ident = item.get("id") or item.get("media_key")
            if ident:
                target[key][ident] = item


def empty_includes() -> dict:
    return {"users": {}, "media": {}, "tweets": {}}


def fetch_all(
    uid: str, page_cap: int = BASELINE_PAGE_CAP, limit: int = 0
) -> tuple[list, dict]:
    posts: list = []
    includes = empty_includes()
    token = None
    pages = 0
    while pages < page_cap:
        payload = fetch_page(uid, token)
        posts.extend(payload.get("data") or [])
        merge_includes(includes, payload)
        pages += 1
        if limit and len(posts) >= limit:
            posts = posts[:limit]
            break
        token = (payload.get("meta") or {}).get("next_token")
        if not token:
            break
        time.sleep(0.25)
    return posts, includes


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {"baseline_at": None, "last_success_at": None, "seen": {}, "sent": []}
    return json.loads(STATE_PATH.read_text())


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8"
    )


def baseline(args) -> None:
    user = get_me()
    posts, _ = fetch_all(
        user["id"], page_cap=args.max_pages, limit=args.recent
    )
    if args.recent and args.recent > 0:
        posts = posts[: args.recent]
    stamp = now_iso()
    state = {
        "baseline_at": stamp,
        "baseline_count": len(posts),
        "baseline_mode": "recent",
        "baseline_recent": args.recent,
        "last_success_at": None,
        "seen": {str(p["id"]): stamp for p in posts},
        "sent": [],
    }
    save_state(state)
    print(
        json.dumps(
            {
                "mode": "baseline",
                "user": user.get("username"),
                "baseline_at": stamp,
                "baseline_mode": "recent",
                "baseline_recent": args.recent,
                "baseline_count": len(posts),
                "state_path": str(STATE_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def import_archive(args) -> None:
    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"archive file not found: {path}")
    text = path.read_text(encoding="utf-8", errors="ignore")
    ids = re.findall(r'tweetId"\s*:\s*"(\d+)"', text)
    if not ids:
        raise SystemExit(f"no tweetId entries found in {path}")
    ids = list(dict.fromkeys(ids))
    stamp = now_iso()
    state = load_state() if args.merge else {}
    state.update(
        {
            "baseline_at": stamp,
            "baseline_count": len(ids),
            "baseline_mode": "archive",
            "baseline_source": str(path),
            "last_success_at": state.get("last_success_at"),
            "seen": {**({} if not args.merge else state.get("seen", {})),
                     **{str(i): stamp for i in ids}},
            "sent": state.get("sent", []),
        }
    )
    save_state(state)
    print(
        json.dumps(
            {
                "mode": "import-archive",
                "source": str(path),
                "imported_ids": len(ids),
                "seen_count": len(state["seen"]),
                "state_path": str(STATE_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def set_start(args) -> None:
    boundary_id = str(args.tweet_id)
    ids: list[str] = []
    if args.manifest:
        manifest = json.loads(Path(args.manifest).read_text())
        for part in manifest.get("parts", []):
            ids.extend(str(post_id) for post_id in part.get("post_ids", []))
    else:
        user = get_me()
        token = None
        for _ in range(SAFETY_PAGE_CAP):
            payload = fetch_page(user["id"], token)
            for post in payload.get("data") or []:
                ids.append(str(post["id"]))
                if str(post["id"]) == boundary_id:
                    break
            if ids and ids[-1] == boundary_id:
                break
            token = (payload.get("meta") or {}).get("next_token")
            if not token:
                break
            time.sleep(0.25)
    if boundary_id not in ids:
        raise SystemExit(f"boundary tweet not found: {boundary_id}")
    boundary_index = ids.index(boundary_id)
    older_ids = ids[boundary_index + 1 :]
    if not older_ids:
        raise SystemExit(
            "boundary must have at least one older item to act as a stop marker"
        )
    stamp = now_iso()
    state = load_state()
    state.pop("baseline_recent", None)
    state.pop("baseline_source", None)
    state.update(
        {
            "baseline_at": stamp,
            "baseline_mode": "tweet-boundary",
            "baseline_boundary_id": boundary_id,
            "baseline_count": len(older_ids),
            "last_success_at": state.get("last_success_at"),
            "seen": {post_id: stamp for post_id in older_ids},
            "sent": state.get("sent", []),
        }
    )
    save_state(state)
    print(
        json.dumps(
            {
                "mode": "set-start",
                "boundary_id": boundary_id,
                "newer_count": boundary_index + 1,
                "older_seen_count": len(older_ids),
                "state_path": str(STATE_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def fetch_new(state: dict, user: dict) -> tuple[list, dict]:
    seen = state.get("seen") or {}
    posts: list = []
    includes = empty_includes()
    token = None
    pages = 0
    while pages < SAFETY_PAGE_CAP:
        payload = fetch_page(user["id"], token)
        page = payload.get("data") or []
        merge_includes(includes, payload)
        for post in page:
            if str(post.get("id")) in seen:
                return posts, includes
            posts.append(post)
        pages += 1
        token = (payload.get("meta") or {}).get("next_token")
        if not token:
            break
        time.sleep(0.25)
    return posts, includes


def normalize_source(raw: dict) -> tuple[list, dict]:
    posts = raw.get("data") or []
    includes = empty_includes()
    merge_includes(includes, raw)
    return posts, includes


def classify(post: dict, media: list) -> str:
    if any(m.get("type") in ("video", "animated_gif") for m in media):
        return "video"
    if any(m.get("type") == "photo" for m in media):
        return "photo"
    urls = [
        u.get("expanded_url", "")
        for u in post.get("entities", {}).get("urls", [])
    ]
    if any(u and "x.com" not in u and "twitter.com" not in u for u in urls):
        return "link"
    text = (post.get("note_tweet") or {}).get("text") or post.get("text", "")
    return "long" if len(text) > 280 else "text"


def is_sensitive(post: dict) -> bool:
    if post.get("possibly_sensitive"):
        return True
    text = (post.get("note_tweet") or {}).get("text") or post.get("text", "")
    return bool(SENSITIVE_PAT.search(text))


def clean_text(text: str, limit: int = 160) -> str:
    text = html.unescape(text or "")
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text).strip()
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return html.escape(text).replace("\n", "<br>")


def dur_label(ms: int | None) -> str:
    if not ms:
        return ""
    total = round(ms / 1000)
    return f"{total // 60}:{total % 60:02d}" if total >= 60 else f"{total}s"


def render_media(media: list, url: str, sensitive: bool) -> str:
    if sensitive:
        return ""
    photos = [m for m in media if m.get("type") == "photo" and m.get("url")]
    if not photos:
        return ""
    if len(photos) == 1:
        m = photos[0]
        max_w = 320 if (m.get("h") or 0) > (m.get("w") or 0) else 520
        return f'''
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;">
          <tr><td align="center"><a href="{url}" style="text-decoration:none;"><img src="{m["url"]}" alt="配图" width="{max_w}" style="display:block;width:100%;max-width:{max_w}px;height:auto;border-radius:12px;border:0;"></a></td></tr>
        </table>'''
    cells = []
    for i, m in enumerate(photos[:2]):
        pad = "padding:0 4px 0 0;" if i == 0 else "padding:0 0 0 4px;"
        cells.append(
            f'<td width="50%" style="{pad}"><a href="{url}"><img src="{m["url"]}" alt="" width="256" style="display:block;width:100%;height:auto;border-radius:10px;border:0;"></a></td>'
        )
    extra = (
        f'<div style="font-size:12px;color:#8a8a8a;margin-top:6px;">+{len(photos) - 2} 张，点原帖看全</div>'
        if len(photos) > 2
        else ""
    )
    return f'''
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:10px;"><tr><td>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>{"".join(cells)}</tr></table>
      {extra}
    </td></tr></table>'''


SECTIONS = [
    ("photo", "🖼", "图片", "#4dabf7"),
    ("video", "🎬", "视频", "#ff6b6b"),
    ("text", "📝", "文字 / 段子", "#845ef7"),
    ("long", "📄", "长文 / 文章", "#f59f00"),
    ("link", "🔗", "外链", "#51cf66"),
]


def build_html(
    posts: list,
    includes: dict,
    issue_id: str,
    part_no: int,
    part_total: int,
    date_label: str,
    total_count: int | None = None,
    total_counts: Counter | None = None,
    total_sensitive: int | None = None,
) -> str:
    users = includes.get("users") or {}
    media_by_key = includes.get("media") or {}
    buckets = {key: [] for key, _, _, _ in SECTIONS}
    sensitive_count = 0
    for post in posts:
        media = [
            media_by_key[k]
            for k in post.get("attachments", {}).get("media_keys", [])
            if k in media_by_key
        ]
        sensitive = is_sensitive(post)
        if sensitive:
            sensitive_count += 1
        buckets[classify(post, media)].append((post, media, sensitive))

    counts = Counter({k: len(v) for k, v in buckets.items()})
    if total_count is None:
        total_count = len(posts)
    if total_counts is None:
        total_counts = counts
    if total_sensitive is None:
        total_sensitive = sensitive_count
    number = 0
    body = ""
    for key, emoji, title, color in SECTIONS:
        rows = buckets[key]
        if not rows:
            continue
        body += f'''
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0 14px 0;">
          <tr><td width="4" style="background:{color};border-radius:2px;"></td>
          <td style="padding-left:10px;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:17px;font-weight:800;color:#141414;">{emoji} {title} · {len(rows)} 条</td></tr>
        </table>'''
        for post, media, sensitive in rows:
            number += 1
            user = users.get(post.get("author_id"), {})
            username = html.escape(str(user.get("username") or "unknown"))
            url = f"https://x.com/{username}/status/{post['id']}"
            if sensitive:
                text_html = '<span style="color:#c92a2a;">⚠️ 敏感内容，正文不复述，点开原帖查看。</span>'
            else:
                text = (post.get("note_tweet") or {}).get("text") or post.get(
                    "text", ""
                )
                text_html = clean_text(text)
            if key == "video" and not sensitive:
                vid = next(
                    (
                        m
                        for m in media
                        if m.get("type") in ("video", "animated_gif")
                    ),
                    {},
                )
                duration = dur_label(vid.get("duration_ms"))
                media_html = (
                    f'<div style="margin-top:8px;font-size:13px;color:#555;">'
                    f'▶ 视频{" · " + duration if duration else ""} · '
                    f'<a href="{url}" style="color:#1a73e8;text-decoration:none;">看原帖</a></div>'
                )
            else:
                media_html = render_media(media, url, sensitive)
            body += f'''
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;">
              <tr>
                <td width="34" valign="top" style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:14px;font-weight:800;color:{color};">{number:03d}</td>
                <td style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;">
                  <div style="font-size:12px;color:#8a8a8a;">@{username}</div>
                  <div style="font-size:15px;line-height:1.7;color:#222;border-left:3px solid #ececec;padding-left:12px;margin-top:8px;">{text_html}</div>
                  {media_html}
                  <div style="margin-top:8px;"><a href="{url}" style="font-size:12px;color:#1a73e8;text-decoration:none;">看原帖 →</a></div>
                </td>
              </tr>
            </table>'''

    part_label = f" ({part_no}/{part_total})" if part_total > 1 else ""
    scope_label = (
        f"本期新增 {total_count} 条 · 本页 {len(posts)} 条"
        if part_total > 1
        else f"本周新增 {total_count} 条"
    )
    return f'''<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>X 瞎看 · {date_label}</title></head>
<body style="margin:0;padding:0;background:#f2f2ef;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f2f2ef;">
<tr><td align="center" style="padding:24px 12px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background:#fff;border-radius:16px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,.06);">
  <tr><td style="background:#141414;padding:30px 26px 24px 26px;">
    <div style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:12px;letter-spacing:2px;color:#9a9a9a;text-transform:uppercase;">Weekly Likes Digest</div>
    <div style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:30px;line-height:1.2;font-weight:800;color:#fff;margin-top:8px;">X 瞎看 <span style="color:#ffd43b;">·</span> {date_label}{part_label}</div>
    <div style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:13px;line-height:1.6;color:#b9b9b9;margin-top:10px;">{scope_label} · 按实际内容分组 · 不加点评 · 视频只给链接</div>
  </td></tr>
  <tr><td style="border-bottom:1px solid #ececec;"><table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
    <td width="33.33%" align="center" style="padding:16px 8px;border-right:1px solid #ececec;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;"><div style="font-size:22px;font-weight:800;color:#141414;">{total_count}</div><div style="font-size:11px;color:#999;margin-top:2px;">本期新增</div></td>
    <td width="33.33%" align="center" style="padding:16px 8px;border-right:1px solid #ececec;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;"><div style="font-size:22px;font-weight:800;color:#141414;">{total_counts["photo"] + total_counts["video"]}</div><div style="font-size:11px;color:#999;margin-top:2px;">图片 / 视频</div></td>
    <td width="33.33%" align="center" style="padding:16px 8px;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;"><div style="font-size:22px;font-weight:800;color:#141414;">{total_sensitive}</div><div style="font-size:11px;color:#999;margin-top:2px;">敏感条目</div></td>
  </tr></table></td></tr>
  <tr><td style="padding:26px 26px 8px 26px;">{body}
    <div style="font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:13px;line-height:1.8;color:#8a8a8a;text-align:center;padding:6px 0 12px 0;">本期按实际内容分组：图片 {total_counts["photo"]} · 视频 {total_counts["video"]} · 文字 {total_counts["text"]} · 长文 {total_counts["long"]} · 外链 {total_counts["link"]}</div>
  </td></tr>
  <tr><td style="background:#fafafa;border-top:1px solid #ececec;padding:18px 26px;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Hiragino Sans GB','Microsoft YaHei',sans-serif;font-size:11px;line-height:1.7;color:#aaa;text-align:center;">按你的设置：不过滤条目 · 视频只给链接 · 敏感内容保留链接但不复述正文<br>每周五 20:30 发送 · 不进 Wiki · 不公开</td></tr>
</table></td></tr></table></body></html>'''


def summarize_posts(posts: list, includes: dict) -> tuple[Counter, int]:
    media_by_key = includes.get("media") or {}
    counts = Counter()
    sensitive_count = 0
    for post in posts:
        media = [
            media_by_key[k]
            for k in post.get("attachments", {}).get("media_keys", [])
            if k in media_by_key
        ]
        counts[classify(post, media)] += 1
        if is_sensitive(post):
            sensitive_count += 1
    return counts, sensitive_count


def split_parts(
    posts: list, includes: dict, issue_id: str, date_label: str
) -> list[tuple[list, str]]:
    """Split posts into parts that stay under the Gmail clipping threshold."""
    parts: list[tuple[list, str]] = []
    queue = [posts]
    while queue:
        chunk = queue.pop(0)
        doc = build_html(chunk, includes, issue_id, 1, 1, date_label)
        if len(doc.encode("utf-8")) <= MAX_HTML_BYTES or len(chunk) <= 1:
            parts.append((chunk, doc))
            continue
        mid = len(chunk) // 2
        queue.insert(0, chunk[mid:])
        queue.insert(0, chunk[:mid])
    return parts


def build(args) -> None:
    state = load_state()
    if args.source_json:
        raw = json.loads(Path(args.source_json).read_text())
        posts, includes = normalize_source(raw)
        if args.limit:
            posts = posts[: args.limit]
        issue_id = datetime.now(TZ).strftime("%Y%m%d-%H%M%S") + "-dryrun"
        date_label = datetime.now(TZ).strftime("%Y.%m.%d")
    else:
        if not state.get("baseline_at"):
            print(
                json.dumps(
                    {
                        "error": "baseline-missing",
                        "hint": "run baseline first; no email was sent",
                        "state_path": str(STATE_PATH),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return
        user = get_me()
        posts, includes = fetch_new(state, user)
        issue_id = datetime.now(TZ).strftime("%Y%m%d-%H%M%S")
        date_label = datetime.now(TZ).strftime("%Y.%m.%d")

    if not posts:
        print(
            json.dumps(
                {"discovered": 0, "sent": 0, "parts": 0, "message": "no new likes"},
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    parts = split_parts(posts, includes, issue_id, date_label)
    issue_dir = ISSUES_DIR / issue_id
    issue_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "issue_id": issue_id,
        "date_label": date_label,
        "subject_base": f"X 瞎看 · {date_label}",
        "created_at": now_iso(),
        "parts": [],
    }
    total = len(parts)
    total_counts, total_sensitive = summarize_posts(posts, includes)
    for index, (chunk, _) in enumerate(parts, 1):
        doc = build_html(
            chunk,
            includes,
            issue_id,
            index,
            total,
            date_label,
            total_count=len(posts),
            total_counts=total_counts,
            total_sensitive=total_sensitive,
        )
        path = issue_dir / f"part-{index}.html"
        path.write_text(doc, encoding="utf-8")
        manifest["parts"].append(
            {
                "index": index,
                "total": total,
                "html_path": str(path),
                "post_ids": [str(p["id"]) for p in chunk],
                "count": len(chunk),
                "bytes": len(doc.encode("utf-8")),
                "sent": False,
                "gmail_id": None,
            }
        )
    (issue_dir / "pending.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "discovered": len(posts),
                "parts": total,
                "issue_dir": str(issue_dir),
                "pending_json": str(issue_dir / "pending.json"),
                "subject_base": manifest["subject_base"],
                "part_bytes": [p["bytes"] for p in manifest["parts"]],
                "dry_run": bool(args.source_json),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def mark_sent(args) -> None:
    issue_dir = ISSUES_DIR / args.issue
    manifest_path = issue_dir / "pending.json"
    if not manifest_path.exists():
        raise SystemExit(f"pending.json not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text())
    state = load_state()
    stamp = now_iso()
    target = None
    for part in manifest["parts"]:
        if part["index"] == args.part:
            target = part
            break
    if target is None:
        raise SystemExit(f"part {args.part} not found in {manifest_path}")
    for post_id in target["post_ids"]:
        state.setdefault("seen", {})[str(post_id)] = stamp
    target["sent"] = True
    target["gmail_id"] = args.gmail_id
    target["sent_at"] = stamp
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    if all(p.get("sent") for p in manifest["parts"]):
        state["last_success_at"] = stamp
        state.setdefault("sent", []).append(
            {
                "issue_id": args.issue,
                "sent_at": stamp,
                "parts": len(manifest["parts"]),
                "gmail_ids": [p.get("gmail_id") for p in manifest["parts"]],
                "post_ids": [
                    pid for p in manifest["parts"] for pid in p["post_ids"]
                ],
            }
        )
    save_state(state)
    print(
        json.dumps(
            {
                "issue": args.issue,
                "part": args.part,
                "gmail_id": args.gmail_id,
                "all_parts_sent": all(p.get("sent") for p in manifest["parts"]),
                "seen_count": len(state.get("seen") or {}),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def status(_args) -> None:
    state = load_state()
    pending = []
    if ISSUES_DIR.exists():
        for path in sorted(ISSUES_DIR.glob("*/pending.json")):
            manifest = json.loads(path.read_text())
            if path.parent.name.endswith("-dryrun"):
                continue
            if not all(p.get("sent") for p in manifest.get("parts", [])):
                pending.append(str(path))
    print(
        json.dumps(
            {
                "state_path": str(STATE_PATH),
                "baseline_at": state.get("baseline_at"),
                "baseline_count": state.get("baseline_count"),
                "seen_count": len(state.get("seen") or {}),
                "last_success_at": state.get("last_success_at"),
                "sent_issues": len(state.get("sent") or []),
                "pending_manifests": pending,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def probe(_args) -> None:
    user = get_me()
    payload = fetch_page(user["id"], max_results=5)
    print(
        json.dumps(
            {
                "user": {
                    "id": user.get("id"),
                    "username": user.get("username"),
                    "name": user.get("name"),
                },
                "liked_sample_count": len(payload.get("data") or []),
                "has_next_token": bool(
                    (payload.get("meta") or {}).get("next_token")
                ),
                "like_read": True,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_probe = sub.add_parser("probe", help="read-only X API check")
    p_probe.set_defaults(func=probe)

    p_status = sub.add_parser("status", help="print state summary")
    p_status.set_defaults(func=status)

    p_baseline = sub.add_parser("baseline", help="record current likes as baseline")
    p_baseline.add_argument("--max-pages", type=int, default=BASELINE_PAGE_CAP)
    p_baseline.add_argument(
        "--recent",
        type=int,
        default=100,
        help="only the newest N likes become the baseline; 0 means all pages",
    )
    p_baseline.set_defaults(func=baseline)

    p_import = sub.add_parser(
        "import-archive", help="seed baseline from an X data archive like.js"
    )
    p_import.add_argument("--path", required=True)
    p_import.add_argument("--merge", action="store_true")
    p_import.set_defaults(func=import_archive)

    p_start = sub.add_parser(
        "set-start", help="set a tweet boundary as the start of the current issue"
    )
    p_start.add_argument("--tweet-id", required=True)
    p_start.add_argument("--manifest", help="offline pending.json containing ordered IDs")
    p_start.set_defaults(func=set_start)

    p_build = sub.add_parser("build", help="fetch new likes and build HTML parts")
    p_build.add_argument("--source-json", help="offline JSON for dry-run")
    p_build.add_argument("--limit", type=int, default=0)
    p_build.set_defaults(func=build)

    p_mark = sub.add_parser("mark-sent", help="record a sent part")
    p_mark.add_argument("--issue", required=True)
    p_mark.add_argument("--part", type=int, required=True)
    p_mark.add_argument("--gmail-id", required=True)
    p_mark.set_defaults(func=mark_sent)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # keep automation output parseable
        print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        sys.exit(1)
