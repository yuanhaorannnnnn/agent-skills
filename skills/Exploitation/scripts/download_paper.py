#!/usr/bin/env python3
"""
download_paper.py: Download papers from URLs to the wiki raw directory.

Supports:
  - arXiv: https://arxiv.org/abs/XXXX.XXXXX or https://arxiv.org/pdf/XXXX.XXXXX.pdf
  - OpenReview: https://openreview.net/pdf?id=XXXX
  - Direct PDF URLs: any URL ending in .pdf

Output: absolute path to the downloaded PDF file.
"""

import argparse
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

# Wiki root — where papers get stored
WIKI_ROOT = Path("/media/yhr/2T/files/wiki")
PAPERS_DIR = WIKI_ROOT / "raw" / "papers" / "paper"

# User-Agent to avoid 403 from arXiv and others
HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def parse_arxiv_id(url: str) -> str | None:
    """Extract arXiv ID from URL.

    Handles:
      - https://arxiv.org/abs/2301.12345
      - https://arxiv.org/abs/2301.12345v2
      - https://arxiv.org/pdf/2301.12345.pdf
      - https://arxiv.org/pdf/2301.12345v2.pdf
      - arxiv.org/abs/2301.12345 (no scheme)
    """
    patterns = [
        r"arxiv\.org/abs/([\w.-]+)",
        r"arxiv\.org/pdf/([\w.-]+?)(?:\.pdf)?$",
    ]
    for pat in patterns:
        m = re.search(pat, url)
        if m:
            return m.group(1)
    return None


def parse_openreview_id(url: str) -> str | None:
    """Extract OpenReview paper ID from URL.

    Handles:
      - https://openreview.net/pdf?id=XXXX
      - https://openreview.net/forum?id=XXXX
    """
    m = re.search(r"openreview\.net/(?:pdf|forum)\?id=([\w-]+)", url)
    if m:
        return m.group(1)
    return None


def download_file(url: str, dest: Path) -> None:
    """Download a file from URL to destination path."""
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        dest.write_bytes(resp.read())


def main():
    parser = argparse.ArgumentParser(
        description="Download a paper PDF from URL to wiki raw/papers/paper/"
    )
    parser.add_argument("url", help="Paper URL (arXiv, OpenReview, or direct PDF)")
    parser.add_argument(
        "--name",
        help="Custom base filename (without .pdf). Default: auto-derived from URL.",
        default=None,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without downloading",
    )
    args = parser.parse_args()

    url = args.url.strip()

    # Ensure papers directory exists
    PAPERS_DIR.mkdir(parents=True, exist_ok=True)

    # Determine source and download URL
    arxiv_id = parse_arxiv_id(url)
    openreview_id = parse_openreview_id(url)

    if arxiv_id:
        # arXiv paper
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        filename = args.name or f"arxiv-{arxiv_id}"
        print(f"Source: arXiv | ID: {arxiv_id}")
        print(f"Download URL: {pdf_url}")
    elif openreview_id:
        # OpenReview paper
        pdf_url = f"https://openreview.net/pdf?id={openreview_id}"
        filename = args.name or f"openreview-{openreview_id}"
        print(f"Source: OpenReview | ID: {openreview_id}")
        print(f"Download URL: {pdf_url}")
    elif url.endswith(".pdf") or "/pdf/" in url:
        # Direct PDF URL — derive filename from URL path
        pdf_url = url
        if args.name:
            filename = args.name
        else:
            # Try to extract a reasonable name from the URL
            parsed = urlparse(url)
            path_parts = parsed.path.strip("/").split("/")
            last = path_parts[-1] if path_parts else "paper"
            filename = last.replace(".pdf", "") if last.endswith(".pdf") else last
        print(f"Source: Direct PDF URL")
    else:
        print(
            f"Error: Cannot determine download method for URL: {url}",
            file=sys.stderr,
        )
        print(
            "Supported: arXiv (abs/pdf), OpenReview (pdf/forum), direct .pdf URLs",
            file=sys.stderr,
        )
        sys.exit(1)

    # Sanitize filename
    filename = re.sub(r"[^\w\-.]", "-", filename).strip("-")
    dest = PAPERS_DIR / f"{filename}.pdf"

    if dest.exists():
        print(f"Warning: File already exists: {dest}")
        print(f"Skipping download. Use --name to specify a different filename.")
        print(f"\n{dest}")
        return

    if args.dry_run:
        print(f"Would download to: {dest}")
        return

    print(f"Downloading to: {dest}")
    try:
        download_file(pdf_url, dest)
        file_size = dest.stat().st_size
        print(f"Downloaded: {file_size:,} bytes")
        print(f"\n{dest}")
    except Exception as e:
        print(f"Error downloading: {e}", file=sys.stderr)
        # Clean up partial download
        if dest.exists():
            dest.unlink()
        sys.exit(1)


if __name__ == "__main__":
    main()
