#!/usr/bin/env python3
"""Fetch a public WeChat Official Account article and convert it to Markdown."""

from __future__ import annotations

import argparse
import html
import datetime
import json
import re
import sys
import textwrap
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


MOBILE_WECHAT_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 "
    "MicroMessenger/8.0.49 NetType/WIFI Language/zh_CN"
)


class ExtractionError(RuntimeError):
    pass


@dataclass
class Article:
    url: str
    title: str
    account: str
    author: str
    published: str
    markdown: str


def extract_first_wechat_url(value: str) -> str:
    match = re.search(r"https?://mp\.weixin\.qq\.com/[^\s\"'<>）)]+", value)
    if not match:
        raise ExtractionError("No mp.weixin.qq.com URL found in input.")
    url = html.unescape(match.group(0)).rstrip(".,;")
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "mp.weixin.qq.com":
        raise ExtractionError("URL is not an mp.weixin.qq.com article URL.")
    return url


def fetch_html(url: str, timeout: int) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": MOBILE_WECHAT_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.7",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="replace")
    except urllib.error.URLError as exc:
        raise ExtractionError(f"Failed to fetch URL: {exc}") from exc


def text_between(pattern: str, source: str) -> str:
    match = re.search(pattern, source, flags=re.I | re.S)
    if not match:
        return ""
    return clean_text(match.group(1))


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def meta_content(source: str, *names: str) -> str:
    for name in names:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']*)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']*)["\']',
            rf'<meta[^>]+content=["\']([^"\']*)["\'][^>]+(?:property|name)=["\']{re.escape(name)}["\']',
        ]
        for pattern in patterns:
            value = text_between(pattern, source)
            if value:
                return value
    return ""


def js_string(source: str, name: str) -> str:
    value = text_between(rf"var\s+{re.escape(name)}\s*=\s*['\"](.*?)['\"]\s*;", source)
    return value.replace(r"\/", "/")


def detect_blocked(source: str) -> None:
    markers = [
        "环境异常",
        "访问频率过高",
        "请在微信客户端打开",
        "该内容已被发布者删除",
        "此内容因违规无法查看",
        "当前内容可能存在未经审核的第三方商业营销信息",
        "验证码",
    ]
    lowered = source.lower()
    verification_markers = [
        "captcha",
        "verifycode",
        "verify_code",
        "security check",
        "access-control",
    ]
    if any(marker in lowered for marker in verification_markers):
        raise ExtractionError("WeChat returned a verification or access-control page.")
    for marker in markers:
        if marker in source:
            raise ExtractionError(f"WeChat article is unavailable: {marker}")


def normalize_image_url(value: str) -> str:
    value = html.unescape(value or "").strip()
    if value.startswith("//"):
        return "https:" + value
    return value


def infer_image_extension(url: str, content_type: str = "") -> str:
    match = re.search(r"(?:wx_fmt|tp)=([A-Za-z0-9]+)", url)
    if match:
        ext = match.group(1).lower()
    elif content_type.startswith("image/"):
        ext = content_type.split("/", 1)[1].split(";", 1)[0].lower()
    else:
        path_ext = Path(urllib.parse.urlparse(url).path).suffix.lower().lstrip(".")
        ext = path_ext or "png"
    aliases = {"jpeg": "jpg", "pjpeg": "jpg", "svg+xml": "svg"}
    ext = aliases.get(ext, ext)
    return ext if re.fullmatch(r"[a-z0-9]{2,5}", ext) else "png"


def collect_markdown_image_urls(markdown: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r"!\[[^\]]*\]\(([^)]+)\)", markdown):
        url = normalize_image_url(match.group(1).strip())
        if url and url not in seen and urllib.parse.urlparse(url).scheme in {"http", "https"}:
            seen.add(url)
            urls.append(url)
    return urls


def download_images(markdown: str, images_dir: Path, timeout: int) -> tuple[str, dict[str, str]]:
    image_urls = collect_markdown_image_urls(markdown)
    if not image_urls:
        return markdown, {}

    images_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    for index, url in enumerate(image_urls, 1):
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": MOBILE_WECHAT_UA,
                "Referer": "https://mp.weixin.qq.com/",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                content = response.read()
                ext = infer_image_extension(url, response.headers.get("Content-Type", ""))
        except Exception as exc:
            print(f"warning: failed to download image {url}: {exc}", file=sys.stderr)
            continue
        filename = f"img_{index:03d}.{ext}"
        target = images_dir / filename
        target.write_bytes(content)
        mapping[url] = f"{images_dir.name}/{filename}"

    for remote_url, local_path in mapping.items():
        escaped = re.escape(remote_url)
        markdown = re.sub(
            r"!\[([^\]]*)\]\(" + escaped + r"\)",
            lambda m: f"![{m.group(1)}]({local_path})",
            markdown,
        )
    return markdown, mapping


def preprocess_wechat_body(soup, body) -> None:
    # WeChat lazy-loads images via data-src; markdownify only sees src.
    for img in body.find_all("img"):
        data_src = img.get("data-src") or img.get("data-original") or img.get("data-backsrc")
        if data_src:
            img["src"] = normalize_image_url(data_src)

    snippets = body.select(".code-snippet__fix, .code-snippet")
    for snippet in snippets:
        if snippet.find_parent("pre"):
            continue
        for noise in snippet.select(".code-snippet__line-index, .code-snippet__copy, .code-snippet__button"):
            noise.decompose()
        pre = snippet.select_one("pre[data-lang]") or snippet.find("pre")
        lang = clean_text(pre.get("data-lang", "")) if pre else ""
        code_lines = []
        for code_tag in snippet.find_all("code"):
            value = code_tag.get_text("", strip=False)
            if value and not re.match(r"^[ce]?ounter\(line", value.strip()):
                code_lines.append(value.rstrip())
        if not code_lines:
            value = snippet.get_text("\n", strip=False).strip()
            if value:
                code_lines.append(value)
        if not code_lines:
            continue
        code = "\n".join(code_lines).strip("\n")
        fence = f"\n\n```{lang}\n{code}\n```\n\n"
        snippet.replace_with(soup.new_string(fence))


def extract_with_bs4(source: str) -> tuple[str, str, str, str, str] | None:
    try:
        from bs4 import BeautifulSoup
    except Exception:
        return None
    soup = BeautifulSoup(source, "html.parser")

    def node_text(selector: str) -> str:
        node = soup.select_one(selector)
        return clean_text(node.get_text(" ")) if node else ""

    def meta(*names: str) -> str:
        for name in names:
            node = soup.find("meta", attrs={"property": name}) or soup.find("meta", attrs={"name": name})
            if node and node.get("content"):
                return clean_text(node["content"])
        return ""

    body = soup.select_one("#js_content") or soup.select_one("article") or soup.select_one(".rich_media_content")
    if not body:
        return None
    preprocess_wechat_body(soup, body)
    title = node_text("#activity-name") or meta("og:title", "twitter:title") or clean_text(soup.title.get_text(" ") if soup.title else "")
    account = node_text("#js_name") or node_text(".profile_nickname") or meta("og:article:author", "author")
    return title, account, meta("author"), "", str(body)


def extract_html_block(source: str) -> tuple[str, str, str, str, str]:
    bs4_result = extract_with_bs4(source)
    if bs4_result:
        return bs4_result
    patterns = [
        r'<div[^>]+id=["\']js_content["\'][^>]*>(.*?)</div>\s*</div>\s*</div>',
        r'<div[^>]+id=["\']js_content["\'][^>]*>(.*?)</div>',
        r"<article[^>]*>(.*?)</article>",
        r'<div[^>]+class=["\'][^"\']*rich_media_content[^"\']*["\'][^>]*>(.*?)</div>',
    ]
    for pattern in patterns:
        match = re.search(pattern, source, flags=re.I | re.S)
        if match:
            return "", "", "", "", match.group(1)
    raise ExtractionError("Could not find the article body in the fetched HTML.")


def html_to_markdown(fragment: str) -> str:
    try:
        from markdownify import markdownify as md
        markdown = md(fragment, heading_style="ATX", strip=["script", "style"])
    except Exception:
        markdown = fallback_markdown(fragment)
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)
    return markdown.strip()


def fallback_markdown(fragment: str) -> str:
    fragment = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", fragment)
    fragment = re.sub(r"(?i)</\s*p\s*>", "\n\n", fragment)
    fragment = re.sub(r"(?i)</\s*(section|div|h[1-6]|li)\s*>", "\n", fragment)
    fragment = re.sub(
        r'(?is)<img[^>]+(?:data-src|src)=["\']([^"\']+)["\'][^>]*>',
        lambda match: f"\n![]({html.unescape(match.group(1))})\n",
        fragment,
    )
    text = re.sub(r"(?is)<(script|style).*?</\1>", "", fragment)
    text = re.sub(r"<[^>]+>", "", text)
    lines = [clean_text(line) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def normalize_published(value: str) -> str:
    if re.fullmatch(r"\d{10}", value or ""):
        return datetime.datetime.fromtimestamp(int(value), datetime.UTC).date().isoformat()
    return value


def parse_article(url: str, source: str) -> Article:
    detect_blocked(source)
    bs_title, bs_account, bs_author, bs_published, body_html = extract_html_block(source)
    title = (
        bs_title
        or text_between(r'<h1[^>]+id=["\']activity-name["\'][^>]*>(.*?)</h1>', source)
        or meta_content(source, "og:title", "twitter:title")
        or text_between(r"<title[^>]*>(.*?)</title>", source)
        or "Untitled WeChat Article"
    )
    account = (
        bs_account
        or text_between(r'<a[^>]+id=["\']js_name["\'][^>]*>(.*?)</a>', source)
        or text_between(r'<strong[^>]+class=["\'][^"\']*profile_nickname[^"\']*["\'][^>]*>(.*?)</strong>', source)
        or meta_content(source, "og:article:author", "author")
    )
    author = js_string(source, "author") or bs_author or meta_content(source, "author")
    published = normalize_published(js_string(source, "publish_time") or js_string(source, "ct") or bs_published)
    body = html_to_markdown(body_html)
    if not body:
        raise ExtractionError("Article body was empty after Markdown conversion.")
    return Article(url=url, title=title, account=account, author=author, published=published, markdown=body)


def yaml_escape(value: str) -> str:
    return json.dumps(value or "", ensure_ascii=False)


def render_markdown(article: Article) -> str:
    frontmatter = [
        "---",
        f"title: {yaml_escape(article.title)}",
        f"source: {yaml_escape(article.url)}",
        f"account: {yaml_escape(article.account)}",
        f"author: {yaml_escape(article.author)}",
        f"published: {yaml_escape(article.published)}",
        "---",
        "",
    ]
    return "\n".join(frontmatter) + f"# {article.title}\n\n{article.markdown}\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="mp.weixin.qq.com URL or copied share text containing one")
    parser.add_argument("--output", "-o", help="Write Markdown to this file")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of Markdown")
    parser.add_argument("--timeout", type=int, default=20, help="Fetch timeout in seconds")
    parser.add_argument("--download-images", action="store_true", help="Download article images and rewrite Markdown links to local files")
    parser.add_argument("--images-dir", help="Directory for downloaded images; defaults to <output-dir>/images or ./images")
    parser.add_argument("--image-timeout", type=int, default=20, help="Image download timeout in seconds")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        url = extract_first_wechat_url(args.input)
        article = parse_article(url, fetch_html(url, args.timeout))
        image_map = {}
        if args.download_images:
            if args.images_dir:
                images_dir = Path(args.images_dir)
            elif args.output:
                images_dir = Path(args.output).resolve().parent / "images"
            else:
                images_dir = Path.cwd() / "images"
            article.markdown, image_map = download_images(article.markdown, images_dir, args.image_timeout)

        if args.json:
            payload = article.__dict__.copy()
            if args.download_images:
                payload["images"] = image_map
            output = json.dumps(payload, ensure_ascii=False, indent=2)
        else:
            output = render_markdown(article)
        if args.output:
            Path(args.output).write_text(output, encoding="utf-8")
        else:
            print(output)
        return 0
    except ExtractionError as exc:
        message = textwrap.fill(str(exc), width=88)
        print(f"error: {message}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
