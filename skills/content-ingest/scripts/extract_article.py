#!/usr/bin/env python3
"""
extract_article.py: Fetch and extract clean article text + images from a URL.

Uses trafilatura (primary) with bs4 fallback for text.
Uses bs4 for image extraction from the article content area.
Outputs JSON with metadata + body text + image paths to stdout.
Optionally saves raw text and images to wiki raw/articles/.

Usage:
  python extract_article.py "https://example.com/blog/post"
  python extract_article.py "https://example.com/blog/post" --save-raw --wiki-root /path/to/wiki
"""

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin, urlparse

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Image URL patterns to skip (noise)
NOISE_IMG_PATTERNS = [
    r"/logo[s]?[-_.]",
    r"/icon[s]?[-_.]",
    r"/avatar[s]?[-_.]",
    r"/pixel[/.]",
    r"/tracking[/.]",
    r"/badge[/.]",
    r"/favicon[/.]",
    r"/social[-_.]",
    r"/share[-_.]",
    r"/emoji[/.]",
    r"\.svg(\?|$)",
    r"^data:",
]


def detect_platform(url: str) -> str:
    domain = urlparse(url).netloc.lower()
    if any(d in domain for d in ["x.com", "twitter.com", "nitter"]):
        return "x"
    if "substack.com" in domain:
        return "substack"
    if "medium.com" in domain:
        return "medium"
    if "github.com" in domain:
        return "github"
    if "arxiv.org" in domain:
        return "arxiv"
    return "blog"


def slugify(text: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[-\s]+", "-", slug).strip("-")
    return slug[:max_len]


def is_noise_image(img_url: str, alt_text: str = "") -> bool:
    """Check if an image is likely noise (logo, icon, tracking pixel, etc)."""
    url_lower = img_url.lower()
    for pat in NOISE_IMG_PATTERNS:
        if re.search(pat, url_lower):
            return True
    # Keep images with meaningful alt text even if URL looks generic
    if alt_text and len(alt_text) > 15:
        return False
    return False


def extract_images(html: str, base_url: str) -> list[dict]:
    """Extract meaningful images from article HTML.

    Returns list of {url, alt, filename} dicts.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []

    soup = BeautifulSoup(html, "html.parser")

    # Remove noise sections before looking for images
    for tag in soup.select(
        "nav, footer, header, script, style, "
        ".comments, .sidebar, .ad, .advertisement, "
        ".nav, .footer, .header, .menu, .share, "
        '[role="navigation"], [role="banner"], [role="contentinfo"]'
    ):
        tag.decompose()

    # Find content area
    content = soup.find("article") or soup.find("main") or soup.find("body")
    if not content:
        return []

    images = []
    seen_urls = set()

    for img in content.find_all("img"):
        src = img.get("src", "") or img.get("data-src", "") or img.get("data-lazy-src", "")
        if not src:
            continue

        # Resolve relative URLs
        full_url = urljoin(base_url, src)

        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        alt = img.get("alt", "").strip()

        if is_noise_image(full_url, alt):
            continue

        # Derive a safe filename from URL
        parsed = urlparse(full_url)
        ext = os.path.splitext(parsed.path)[1]
        if not ext or len(ext) > 5:
            ext = ".png"  # default
        safe_name = re.sub(r"[^\w\-.]", "-", os.path.basename(parsed.path))[:80]
        if not safe_name or safe_name == "-":
            safe_name = f"image{len(images) + 1}"

        filename = f"{safe_name}{ext}" if not safe_name.endswith(ext) else safe_name

        images.append({
            "url": full_url,
            "alt": alt,
            "filename": filename,
        })

    return images


def download_images(images: list[dict], dest_dir: Path) -> list[dict]:
    """Download images to dest_dir. Returns updated list with local_path added."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    for img in images:
        dest = dest_dir / img["filename"]
        # Avoid overwriting: append counter if needed
        counter = 1
        while dest.exists():
            stem = os.path.splitext(img["filename"])[0]
            ext = os.path.splitext(img["filename"])[1]
            dest = dest_dir / f"{stem}-{counter}{ext}"
            counter += 1
        try:
            req = urllib.request.Request(img["url"], headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                dest.write_bytes(resp.read())
            img["local_path"] = str(dest)
        except Exception as e:
            img["local_path"] = None
            img["download_error"] = str(e)
    return images


def extract_with_trafilatura(html: str, url: str) -> dict | None:
    try:
        import trafilatura
    except ImportError:
        return None

    doc = trafilatura.extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        output_format="json",
        with_metadata=True,
    )
    if not doc:
        return None

    data = json.loads(doc)
    return {
        "title": data.get("title", ""),
        "author": data.get("author", ""),
        "date": data.get("date", ""),
        "body": data.get("text", ""),
        "source_url": url,
        "platform": detect_platform(url),
        "extractor": "trafilatura",
    }


def extract_with_bs4(html: str, url: str) -> dict | None:
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return None

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.select(
        "nav, footer, header, aside, script, style, "
        ".comments, .sidebar, .ad, .advertisement, "
        ".nav, .footer, .header, .menu, .share, "
        '[role="navigation"], [role="banner"], [role="contentinfo"]'
    ):
        tag.decompose()

    title = ""
    og_title = soup.find("meta", property="og:title")
    if og_title:
        title = og_title.get("content", "")
    if not title:
        t = soup.find("title")
        if t:
            title = t.get_text(strip=True)
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)

    author = ""
    og_author = soup.find("meta", property="article:author")
    if og_author:
        author = og_author.get("content", "")

    date = ""
    og_date = soup.find("meta", property="article:published_time")
    if og_date:
        date = og_date.get("content", "")[:10]

    body = ""
    article = soup.find("article")
    if article:
        body = article.get_text("\n", strip=True)
    else:
        main = soup.find("main") or soup.find("body")
        if main:
            body = main.get_text("\n", strip=True)

    body = re.sub(r"\n{3,}", "\n\n", body)

    return {
        "title": title,
        "author": author,
        "date": date,
        "body": body,
        "source_url": url,
        "platform": detect_platform(url),
        "extractor": "bs4",
    }


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main():
    parser = argparse.ArgumentParser(
        description="Extract clean article text + images from a URL"
    )
    parser.add_argument("url", help="Article URL")
    parser.add_argument(
        "--save-raw",
        action="store_true",
        help="Save raw text + images to raw/articles/{slug}/",
    )
    parser.add_argument(
        "--wiki-root",
        default=None,
        help="Wiki root directory (required with --save-raw)",
    )
    parser.add_argument(
        "--output-json",
        default=None,
        help="Save JSON output to this file path",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image extraction (text only)",
    )
    args = parser.parse_args()

    url = args.url.strip()

    # Fetch
    print(f"Fetching: {url}", file=sys.stderr)
    try:
        html = fetch_url(url)
    except Exception as e:
        print(json.dumps({"error": f"Failed to fetch URL: {e}"}))
        sys.exit(1)

    # Extract text
    result = extract_with_trafilatura(html, url)
    if not result:
        result = extract_with_bs4(html, url)

    if not result or not result.get("body"):
        print(json.dumps({"error": "Could not extract article content"}))
        sys.exit(1)

    # Generate slug
    title_slug = slugify(result["title"]) if result["title"] else "untitled"
    date_prefix = datetime.now().strftime("%Y%m%d")
    slug = f"{date_prefix}-{title_slug}"
    result["slug"] = slug

    # Extract images
    images = []
    if not args.no_images:
        raw_images = extract_images(html, url)
        print(f"Found {len(raw_images)} images", file=sys.stderr)
        if raw_images and args.save_raw and args.wiki_root:
            img_dir = Path(args.wiki_root) / "raw" / "articles" / "images" / slug
            images = download_images(raw_images, img_dir)
            downloaded = sum(1 for i in images if i.get("local_path"))
            print(f"Downloaded {downloaded}/{len(images)} images", file=sys.stderr)
        else:
            images = raw_images  # URLs only, no download

    result["images"] = images

    # Save raw if requested
    if args.save_raw:
        if not args.wiki_root:
            print(
                json.dumps({"error": "--wiki-root required with --save-raw"}),
                file=sys.stderr,
            )
            sys.exit(1)

        raw_dir = Path(args.wiki_root) / "raw" / "articles"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_path = raw_dir / f"{slug}.md"

        # Build image references for the raw file
        img_refs = ""
        if images:
            img_refs = "\n## 图片\n\n"
            for i, img in enumerate(images):
                local = img.get("local_path")
                if local:
                    rel = Path(local).relative_to(Path(args.wiki_root))
                    img_refs += f"- ![{img['alt'] or f'Figure {i+1}'}]({rel})\n"
                else:
                    img_refs += f"- [{img['alt'] or f'Figure {i+1}'}]({img['url']}) (未下载)\n"

        raw_content = f"""---
title: "{result['title']}"
source_url: {url}
platform: {result['platform']}
author: {result['author']}
date: {result['date']}
extracted: {datetime.now().strftime('%Y-%m-%d')}
extractor: {result['extractor']}
images: {len(images)} found, {sum(1 for i in images if i.get('local_path'))} downloaded
---

# {result['title']}

{result['body']}
{img_refs}"""
        raw_path.write_text(raw_content, encoding="utf-8")
        result["raw_path"] = str(raw_path)
        print(f"Saved raw: {raw_path}", file=sys.stderr)

    # Output JSON
    output = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output_json:
        Path(args.output_json).write_text(output, encoding="utf-8")
        print(f"Saved JSON: {args.output_json}", file=sys.stderr)

    print(output)


if __name__ == "__main__":
    main()
