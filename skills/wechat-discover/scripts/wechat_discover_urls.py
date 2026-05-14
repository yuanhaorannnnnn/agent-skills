#!/usr/bin/env python3
"""Discover WeChat Official Account article URLs with Tavily Search."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


TAVILY_ENDPOINT = "https://api.tavily.com/search"
WECHAT_URL_RE = re.compile(r"https?://mp\.weixin\.qq\.com/(?:s|mp/appmsgalbum)[^\s\"'<>）)]+")
WECHAT_TO_MARKDOWN_SCRIPT = Path("/home/yhr/.codex/skills/wechat-mp-to-markdown/scripts/wechat_article_to_markdown.py")


class DiscoveryError(RuntimeError):
    pass


@dataclass
class DiscoveredURL:
    url: str
    title: str
    snippet: str
    score: float | None
    source_query: str
    account: str = ""
    author: str = ""
    published: str = ""
    verified: bool = False
    source: str = "tavily"


def clean_url(url: str) -> str:
    url = url.replace("&amp;", "&").rstrip(".,;，。；)")
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "mp.weixin.qq.com":
        raise ValueError("not a WeChat URL")
    if parsed.path.startswith("/s/"):
        slug = parsed.path.removeprefix("/s/").strip("/")
        if not slug:
            raise ValueError("empty WeChat article slug")
        return urllib.parse.urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, "", parsed.query, ""))
    if parsed.path == "/mp/appmsgalbum":
        return urllib.parse.urlunparse((parsed.scheme or "https", parsed.netloc, parsed.path, "", parsed.query, ""))
    raise ValueError("not a supported WeChat article/list URL")


def extract_wechat_urls(*values: str) -> list[str]:
    urls: list[str] = []
    for value in values:
        for match in WECHAT_URL_RE.findall(value or ""):
            try:
                urls.append(clean_url(match))
            except ValueError:
                continue
    return urls


def build_queries(account: str, query: str) -> list[str]:
    queries: list[str] = []
    if account:
        queries.extend([
            f'site:mp.weixin.qq.com/s "{account}" "公众号"',
            f'"{account} | 公众号" "mp.weixin.qq.com/s"',
            f'"{account}" "公众号" "mp.weixin.qq.com/s"',
        ])
    if query:
        queries.extend([
            f'site:mp.weixin.qq.com/s {query}',
            f'"mp.weixin.qq.com/s" {query}',
        ])
    seen: set[str] = set()
    deduped: list[str] = []
    for item in queries:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    if not deduped:
        raise DiscoveryError("Provide --account, --query, or both.")
    return deduped


def validate_date(value: str) -> str:
    if not value:
        return ""
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise DiscoveryError(f"Invalid date {value!r}; expected YYYY-MM-DD.") from exc
    return value


def tavily_search(api_key: str, query: str, max_results: int, since: str, until: str) -> dict:
    body = {
        "query": query,
        "search_depth": "basic",
        "max_results": max(1, min(max_results, 20)),
        "include_domains": ["mp.weixin.qq.com"],
        "include_answer": False,
        "include_raw_content": False,
        "include_images": False,
        "include_usage": True,
    }
    if since:
        body["start_date"] = since
    if until:
        body["end_date"] = until
    data = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        TAVILY_ENDPOINT,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise DiscoveryError(f"Tavily HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise DiscoveryError(f"Tavily request failed: {exc}") from exc


def discover(api_key: str, account: str, query: str, limit: int, since: str, until: str, pause: float) -> tuple[list[DiscoveredURL], list[dict]]:
    found: dict[str, DiscoveredURL] = {}
    responses: list[dict] = []
    queries = build_queries(account, query)
    per_query = min(20, max(5, limit))
    for index, search_query in enumerate(queries):
        if len(found) >= limit:
            break
        response = tavily_search(api_key, search_query, per_query, since, until)
        responses.append({
            "query": search_query,
            "usage": response.get("usage", {}),
            "response_time": response.get("response_time"),
            "result_count": len(response.get("results", [])),
        })
        for result in response.get("results", []):
            candidates = extract_wechat_urls(result.get("url", ""), result.get("content", ""), result.get("raw_content", ""))
            for url in candidates:
                if url not in found:
                    found[url] = DiscoveredURL(
                        url=url,
                        title=result.get("title", "") or "",
                        snippet=result.get("content", "") or "",
                        score=result.get("score"),
                        source_query=search_query,
                    )
                if len(found) >= limit:
                    break
            if len(found) >= limit:
                break
        if index < len(queries) - 1 and pause > 0:
            time.sleep(pause)
    return list(found.values())[:limit], responses


def load_wechat_converter():
    if not WECHAT_TO_MARKDOWN_SCRIPT.exists():
        raise DiscoveryError(f"Missing converter script: {WECHAT_TO_MARKDOWN_SCRIPT}")
    spec = importlib.util.spec_from_file_location("wechat_article_to_markdown", WECHAT_TO_MARKDOWN_SCRIPT)
    if spec is None or spec.loader is None:
        raise DiscoveryError("Could not load wechat-mp-to-markdown converter.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def normalize_name(value: str) -> str:
    return re.sub(r"\s+", "", value or "")


def date_key(value: str) -> str:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value or ""):
        return value
    return ""


def verify_rows(rows: list[DiscoveredURL], account: str, keep_unverified: bool) -> list[DiscoveredURL]:
    converter = load_wechat_converter()
    verified: list[DiscoveredURL] = []
    expected_account = normalize_name(account)
    for row in rows:
        try:
            article = converter.parse_article(row.url, converter.fetch_html(row.url, 20))
        except Exception:
            if keep_unverified:
                verified.append(row)
            continue
        row.title = article.title or row.title
        row.account = article.account
        row.author = article.author
        row.published = article.published
        row.verified = True
        if expected_account and normalize_name(row.account) != expected_account:
            continue
        verified.append(row)
    return verified


def sort_latest(rows: list[DiscoveredURL]) -> list[DiscoveredURL]:
    return sorted(rows, key=lambda row: (date_key(row.published), row.score or 0), reverse=True)


def write_urls(path: str, rows: Iterable[DiscoveredURL]) -> None:
    Path(path).write_text("\n".join(row.url for row in rows) + "\n", encoding="utf-8")


def write_json(path: str, rows: list[DiscoveredURL], responses: list[dict]) -> None:
    payload = {
        "generated_at": dt.datetime.now(dt.UTC).isoformat(),
        "count": len(rows),
        "items": [asdict(row) for row in rows],
        "searches": responses,
    }
    Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_report(path: str, rows: list[DiscoveredURL], responses: list[dict]) -> None:
    lines = [
        "# WeChat URL Discovery Report",
        "",
        f"Generated: {dt.datetime.now(dt.UTC).isoformat()}",
        f"Count: {len(rows)}",
        "",
        "## Searches",
        "",
    ]
    for response in responses:
        lines.append(f"- `{response['query']}`: {response['result_count']} results, usage={response.get('usage', {})}")
    lines.extend(["", "## URLs", ""])
    for index, row in enumerate(rows, 1):
        title = row.title.replace("\n", " ").strip() or row.url
        lines.append(f"{index}. [{title}]({row.url})")
        if row.account:
            lines.append(f"   - account: {row.account}")
        if row.published:
            lines.append(f"   - published: {row.published}")
        if row.score is not None:
            lines.append(f"   - score: {row.score}")
        lines.append(f"   - verified: {row.verified}")
        lines.append(f"   - query: `{row.source_query}`")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--account", default="", help="WeChat Official Account display name")
    parser.add_argument("--query", default="", help="Topic or keyword query")
    parser.add_argument("--limit", type=int, default=50, help="Maximum URLs to output")
    parser.add_argument("--candidate-limit", type=int, default=60, help="Candidate URLs to collect before verification/sorting")
    parser.add_argument("--latest", action="store_true", help="Verify candidates, filter by account, and sort by article publish date descending")
    parser.add_argument("--verify", action="store_true", help="Fetch each candidate and attach verified article metadata")
    parser.add_argument("--keep-unverified", action="store_true", help="Keep candidates that cannot be fetched during verification")
    parser.add_argument("--since", default="", help="Return results after this date, YYYY-MM-DD")
    parser.add_argument("--until", default="", help="Return results before this date, YYYY-MM-DD")
    parser.add_argument("--output", default="urls.txt", help="Plain URL list output path")
    parser.add_argument("--json-output", default="", help="Optional structured JSON output path")
    parser.add_argument("--report", default="", help="Optional Markdown report output path")
    parser.add_argument("--api-key", default="", help="Tavily API key; prefer TAVILY_API_KEY")
    parser.add_argument("--pause", type=float, default=0.2, help="Seconds to pause between search queries")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        api_key = args.api_key or os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            raise DiscoveryError("Missing Tavily API key. Set TAVILY_API_KEY or pass --api-key.")
        if args.limit < 1:
            raise DiscoveryError("--limit must be at least 1.")
        since = validate_date(args.since)
        until = validate_date(args.until)
        account = args.account.strip()
        query = args.query.strip()
        candidate_limit = args.candidate_limit if (args.latest or args.verify) else args.limit
        rows, responses = discover(api_key, account, query, candidate_limit, since, until, args.pause)
        if args.latest or args.verify:
            rows = verify_rows(rows, account if args.latest else "", args.keep_unverified)
        if args.latest:
            rows = sort_latest(rows)
        rows = rows[:args.limit]
        write_urls(args.output, rows)
        if args.json_output:
            write_json(args.json_output, rows, responses)
        if args.report:
            write_report(args.report, rows, responses)
        print(f"wrote {len(rows)} URLs to {args.output}")
        return 0
    except DiscoveryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
