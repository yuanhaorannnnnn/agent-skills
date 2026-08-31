#!/usr/bin/env python3
"""Discover and de-duplicate public article URLs from a WeChat album.

This is a discovery-only route. It never fetches individual articles or creates
queries; callers choose which discovered article URLs enter the normal article
pipeline.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit


DEFAULT_MAX_SCROLLS = 24


def validate_album_url(url: str) -> str:
    parsed = urlsplit(url)
    query = parse_qs(parsed.query)
    if parsed.scheme != "https" or parsed.hostname != "mp.weixin.qq.com":
        raise ValueError("only public https://mp.weixin.qq.com album URLs are supported")
    if parsed.path != "/mp/appmsgalbum":
        raise ValueError("expected a /mp/appmsgalbum URL")
    if not query.get("album_id") or not query.get("__biz"):
        raise ValueError("album URL must include album_id and __biz")
    return url


def canonical_album_url(url: str) -> str:
    parsed = urlsplit(validate_album_url(url))
    query = parse_qs(parsed.query)
    return urlunsplit(
        (
            "https",
            "mp.weixin.qq.com",
            "/mp/appmsgalbum",
            urlencode(
                {
                    "__biz": query["__biz"][0],
                    "action": "getalbum",
                    "album_id": query["album_id"][0],
                }
            ),
            "",
        )
    )


def normalize_article_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.hostname != "mp.weixin.qq.com" or parsed.path != "/s":
        raise ValueError(f"album item is not a WeChat article URL: {url}")
    if not parse_qs(parsed.query).get("mid"):
        raise ValueError(f"article URL has no mid: {url}")
    return urlunsplit(("https", "mp.weixin.qq.com", "/s", parsed.query, ""))


def article_identity(url: str) -> str:
    parsed = urlsplit(normalize_article_url(url))
    query = parse_qs(parsed.query)
    mid = query.get("mid", [""])[0]
    idx = query.get("idx", [""])[0]
    biz = query.get("__biz", [""])[0]
    return f"{biz}:{mid}:{idx}" if biz and mid else normalize_article_url(url)


def parse_item(raw: dict[str, str]) -> dict[str, object]:
    url = normalize_article_url(raw["url"])
    lines = [line.strip() for line in raw.get("text", "").splitlines() if line.strip()]
    first_line = lines[0] if lines else ""
    number_match = re.match(r"^(\d+)\.\s*(.*)$", first_line)
    article_number = int(number_match.group(1)) if number_match else None
    title = number_match.group(2).strip() if number_match else first_line
    if not title:
        raise ValueError(f"album item has no title: {url}")
    return {
        "article_number": article_number,
        "title": title,
        "listed_time": lines[1] if len(lines) > 1 else None,
        "url": url,
        "identity": article_identity(url),
    }


def declared_item_count(body: str) -> int | None:
    match = re.search(r"\b(\d+)\s+items\b", body, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def compile_manifest(source_url: str, browser_data: dict[str, object]) -> dict[str, object]:
    seen: set[str] = set()
    items: list[dict[str, object]] = []
    duplicates = 0
    for raw in browser_data["items"]:
        item = parse_item(raw)
        identity = str(item.pop("identity"))
        if identity in seen:
            duplicates += 1
            continue
        seen.add(identity)
        items.append(item)

    canonical_url = canonical_album_url(source_url)
    declared = declared_item_count(str(browser_data.get("body", "")))
    return {
        "source_url": source_url,
        "canonical_album_url": canonical_url,
        "platform": "wechat",
        "album_id": parse_qs(urlsplit(canonical_url).query)["album_id"][0],
        "title": str(browser_data["title"]),
        "declared_items": declared,
        "discovered_items": len(items),
        "duplicates_removed": duplicates,
        "complete": declared is None or declared == len(items),
        "items": items,
    }


def select_items(
    items: list[dict[str, object]], limit: int | None, order: str
) -> list[dict[str, object]]:
    """Select the requested portion after discovery has established completeness."""
    if order not in {"latest", "oldest"}:
        raise ValueError("order must be latest or oldest")
    numbered = all(item["article_number"] is not None for item in items)
    if numbered:
        ordered = sorted(
            items,
            key=lambda item: int(item["article_number"]),
            reverse=order == "latest",
        )
    elif order == "latest":
        ordered = list(items)
    else:
        ordered = list(reversed(items))
    return ordered if limit is None else ordered[:limit]


def apply_selection(
    manifest: dict[str, object], limit: int | None, order: str
) -> dict[str, object]:
    selected = select_items(list(manifest["items"]), limit, order)
    result = dict(manifest)
    result["items"] = selected
    result["selection"] = {
        "order": order,
        "limit": limit,
        "selected_items": len(selected),
    }
    return result


def installed_cli_python(command: str) -> str:
    executable = shutil.which(command)
    if executable is None:
        raise RuntimeError(
            f"{command!r} is not installed; install it once with "
            "`uv tool install wechat-article-to-markdown`"
        )
    first_line = Path(executable).read_text(encoding="utf-8").splitlines()[0]
    if not first_line.startswith("#!"):
        raise RuntimeError(f"cannot determine the Python runtime for {command!r}")
    python_path = first_line[2:].strip()
    if not Path(python_path).is_file():
        raise RuntimeError(f"installed runtime no longer exists: {python_path}")
    return python_path


def fetch_album_dom(url: str, command: str, max_scrolls: int) -> dict[str, object]:
    python_path = installed_cli_python(command)
    launcher = """
import asyncio
import json
import sys
from camoufox.async_api import AsyncCamoufox

async def main():
    url = sys.argv[1]
    max_scrolls = int(sys.argv[2])
    async with AsyncCamoufox(headless=True) as browser:
        page = await browser.new_page()
        await page.goto(url, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        stable = 0
        for _ in range(max_scrolls):
            before = await page.locator("li[data-link]").count()
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(0.75)
            after = await page.locator("li[data-link]").count()
            stable = stable + 1 if after == before else 0
            if stable >= 2:
                break
        items = await page.locator("li[data-link]").evaluate_all(
            "els => els.map(el => ({url: el.getAttribute('data-link'), text: (el.innerText || '').trim()}))"
        )
        return {"title": await page.title(), "body": await page.locator("body").inner_text(), "items": items}

print(json.dumps(asyncio.run(main()), ensure_ascii=False))
"""
    completed = subprocess.run(
        [python_path, "-c", launcher, url, str(max_scrolls)],
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()[-1:]
        suffix = detail[0] if detail else f"exit code {completed.returncode}"
        raise RuntimeError(f"WeChat album discovery failed: {suffix}")
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("WeChat album discovery returned invalid JSON") from error
    if not result.get("items"):
        raise RuntimeError("WeChat album page exposed no article data-link entries")
    return result


def manifest_path(wiki_root: Path, canonical_url: str) -> Path:
    album_id = parse_qs(urlsplit(canonical_url).query)["album_id"][0]
    digest = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:10]
    name = f"{dt.date.today():%Y%m%d}-wechat-album-{album_id}-{digest}.json"
    return wiki_root / "raw" / "collections" / name


def save_manifest(manifest: dict[str, object], wiki_root: Path) -> Path:
    path = manifest_path(wiki_root, str(manifest["canonical_album_url"]))
    if path.exists():
        raise FileExistsError(f"refusing to overwrite an existing album manifest: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Public https://mp.weixin.qq.com/mp/appmsgalbum URL")
    parser.add_argument(
        "--save-manifest",
        action="store_true",
        help="Write the discovered URL list to raw/collections; otherwise print JSON only.",
    )
    parser.add_argument("--wiki-root", type=Path, help="Required with --save-manifest")
    parser.add_argument(
        "--limit",
        type=int,
        help="Return at most N article URLs after full discovery; default is all.",
    )
    parser.add_argument(
        "--order",
        choices=("latest", "oldest"),
        default="latest",
        help="Selection order; default is latest.",
    )
    parser.add_argument("--max-scrolls", type=int, default=DEFAULT_MAX_SCROLLS)
    parser.add_argument("--command", default="wechat-article-to-markdown")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        validate_album_url(args.url)
        if args.max_scrolls < 1 or (args.limit is not None and args.limit < 1):
            raise ValueError("--max-scrolls and --limit must be positive")
        if args.save_manifest != bool(args.wiki_root):
            raise ValueError("--save-manifest and --wiki-root must be provided together")
        manifest = apply_selection(
            compile_manifest(
                args.url,
                fetch_album_dom(args.url, args.command, args.max_scrolls),
            ),
            args.limit,
            args.order,
        )
        if args.save_manifest:
            manifest["manifest_path"] = str(save_manifest(manifest, args.wiki_root.resolve()))
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
