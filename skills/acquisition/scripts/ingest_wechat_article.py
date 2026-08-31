#!/usr/bin/env python3
"""Capture one public WeChat article into the wiki raw-article contract.

This is a bounded fallback for ``extract_article.py``.  The third-party
``wechat-article-to-markdown`` CLI has no output-directory flag, so this
adapter invokes its installed module with an isolated staging directory and
then normalizes the result into ``raw/articles``.
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
import tempfile
from urllib.parse import urlparse


MIN_BODY_CHARACTERS = 200


def validate_wechat_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "mp.weixin.qq.com":
        raise ValueError("only public https://mp.weixin.qq.com/... URLs are supported")
    if not parsed.path:
        raise ValueError("WeChat article URL has no path")
    return url


def safe_yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def canonical_stem(url: str, today: dt.date | None = None) -> str:
    date_prefix = (today or dt.date.today()).strftime("%Y%m%d")
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:12]
    return f"{date_prefix}-wechat-{digest}"


def parse_cli_markdown(markdown: str, source_url: str) -> tuple[str, str, str, str]:
    """Return title, author, published, and body from the CLI's Markdown."""
    text = markdown.replace("\r\n", "\n").strip()
    lines = text.splitlines()
    if not lines or not lines[0].startswith("# "):
        raise ValueError("CLI output has no title heading")

    title = lines[0][2:].strip()
    if not title:
        raise ValueError("CLI output title is empty")

    author = ""
    published = ""
    separator = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            separator = index
            break
        if line.startswith("> 公众号:"):
            author = line.split(":", 1)[1].strip()
        elif line.startswith("> 发布时间:"):
            published = line.split(":", 1)[1].strip()

    if separator is None:
        body = "\n".join(lines[1:]).strip()
    else:
        body = "\n".join(lines[separator + 1 :]).strip()
    if len(re.sub(r"\s+", "", body)) < MIN_BODY_CHARACTERS:
        raise ValueError("CLI output body is too short for a reliable raw archive")
    if not source_url:
        raise ValueError("source URL is required")
    return title, author, published, body


def rewrite_image_paths(markdown: str, image_directory_name: str) -> str:
    return re.sub(
        r"\]\(images/",
        f"](images/{image_directory_name}/",
        markdown,
    )


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


def run_cli_in_staging(url: str, staging_dir: Path, command: str) -> None:
    python_path = installed_cli_python(command)
    launcher = "\n".join(
        [
            "import asyncio",
            "from pathlib import Path",
            "import sys",
            "import wechat_article_to_markdown as article",
            "article.OUTPUT_DIR = Path(sys.argv[2])",
            "asyncio.run(article.fetch_article(sys.argv[1]))",
        ]
    )
    completed = subprocess.run(
        [python_path, "-c", launcher, url, str(staging_dir)],
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip().splitlines()[-1:]
        suffix = detail[0] if detail else f"exit code {completed.returncode}"
        raise RuntimeError(f"WeChat fallback extraction failed: {suffix}")


def single_markdown_file(staging_dir: Path) -> Path:
    candidates = list(staging_dir.glob("*/*.md"))
    if len(candidates) != 1:
        raise ValueError(f"expected exactly one Markdown result, found {len(candidates)}")
    return candidates[0]


def build_raw_document(
    *,
    title: str,
    author: str,
    published: str,
    source_url: str,
    extracted: str,
    fallback_reason: str,
    images_downloaded: int,
    body: str,
) -> str:
    frontmatter = [
        "---",
        f"title: {safe_yaml_string(title)}",
        f"source_url: {safe_yaml_string(source_url)}",
        "platform: wechat",
        f"author: {safe_yaml_string(author)}",
        f"published: {safe_yaml_string(published)}",
        f"extracted: {extracted}",
        'extractor: "wechat-article-to-markdown Camoufox fallback"',
        f"fallback_reason: {safe_yaml_string(fallback_reason)}",
        f"images_downloaded: {images_downloaded}",
        "---",
        "",
        f"# {title}",
        "",
        body.rstrip(),
        "",
    ]
    return "\n".join(frontmatter)


def archive_article(
    *,
    wiki_root: Path,
    source_url: str,
    fallback_reason: str,
    command: str,
) -> dict[str, object]:
    validate_wechat_url(source_url)
    raw_articles = wiki_root / "raw" / "articles"
    raw_articles.mkdir(parents=True, exist_ok=True)
    stem = canonical_stem(source_url)
    final_markdown = raw_articles / f"{stem}.md"
    final_images = raw_articles / "images" / stem
    if final_markdown.exists() or final_images.exists():
        raise FileExistsError(
            f"refusing to overwrite an existing raw capture: {final_markdown}"
        )

    with tempfile.TemporaryDirectory(prefix="acquisition-wechat-") as temporary:
        staging_dir = Path(temporary) / "output"
        run_cli_in_staging(source_url, staging_dir, command)
        cli_markdown = single_markdown_file(staging_dir)
        title, author, published, body = parse_cli_markdown(
            cli_markdown.read_text(encoding="utf-8"), source_url
        )
        staging_images = cli_markdown.parent / "images"
        image_count = (
            len([path for path in staging_images.rglob("*") if path.is_file()])
            if staging_images.exists()
            else 0
        )
        body = rewrite_image_paths(body, stem)
        document = build_raw_document(
            title=title,
            author=author,
            published=published,
            source_url=source_url,
            extracted=dt.date.today().isoformat(),
            fallback_reason=fallback_reason,
            images_downloaded=image_count,
            body=body,
        )

        created_images = False
        try:
            if staging_images.exists() and image_count:
                final_images.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(staging_images, final_images)
                created_images = True
            final_markdown.write_text(document, encoding="utf-8")
        except Exception:
            if final_markdown.exists():
                final_markdown.unlink()
            if created_images and final_images.exists():
                shutil.rmtree(final_images)
            raise

    return {
        "raw_path": str(final_markdown),
        "images_dir": str(final_images) if image_count else None,
        "images_downloaded": image_count,
        "title": title,
        "fallback_reason": fallback_reason,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="Public https://mp.weixin.qq.com/... article URL")
    parser.add_argument("--wiki-root", required=True, type=Path)
    parser.add_argument(
        "--fallback-reason",
        required=True,
        help="Observed direct-extraction gate failure; stored with the raw archive.",
    )
    parser.add_argument(
        "--command",
        default="wechat-article-to-markdown",
        help="Installed CLI command (mainly for controlled testing).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = archive_article(
            wiki_root=args.wiki_root.resolve(),
            source_url=args.url,
            fallback_reason=args.fallback_reason,
            command=args.command,
        )
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
