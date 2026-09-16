#!/usr/bin/env python3
"""Find an acquisition source already represented in the Wiki."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_KEYS = {
    "fbclid", "gclid", "igshid", "poc_token", "scene", "scenenote",
    "search_click_id", "subscene", "vd_source",
}
URL_FIELDS = ("source_url", "source", "url")


def canonical_url(value: str) -> str:
    value = value.strip().strip("<>\"'")
    parts = urlsplit(value)
    if parts.scheme.lower() not in {"http", "https"} or not parts.netloc:
        return ""
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    query = []
    for key, item in parse_qsl(parts.query, keep_blank_values=True):
        lower = key.lower()
        if lower.startswith("utm_") or lower in TRACKING_KEYS:
            continue
        if host in {"x.com", "twitter.com"} and lower == "s":
            continue
        query.append((key, item))
    query.sort()
    path = re.sub(r"/{2,}", "/", parts.path) or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(query), ""))


def body_hash(text: str) -> str:
    text = re.sub(r"^---\n.*?\n---(?:\n|$)", "", text, count=1, flags=re.DOTALL)
    normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""


def frontmatter_url(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---(?:\n|$)", text, re.DOTALL)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() in URL_FIELDS:
            found = canonical_url(value)
            if found:
                return found
    return ""


def candidate_files(root: Path) -> list[Path]:
    paths: list[Path] = []
    for relative in ("Clippings", "raw", "queries"):
        directory = root / relative
        if directory.exists():
            paths.extend(directory.rglob("*.md"))
            paths.extend(directory.rglob("*.txt"))
    return sorted(path for path in set(paths) if path.is_file())


def inspect(root: Path, url: str, source_file: Path | None) -> dict[str, object]:
    target_text = source_file.read_text(encoding="utf-8", errors="replace") if source_file else ""
    target_url = canonical_url(url) or frontmatter_url(target_text)
    target_hash = body_hash(target_text) if target_text else ""
    matches: list[dict[str, str]] = []
    for path in candidate_files(root):
        if source_file and path.resolve() == source_file.resolve():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        existing_url = frontmatter_url(text)
        kinds: list[str] = []
        if target_url and existing_url == target_url:
            kinds.append("canonical_url")
        if target_hash and path.parts[-2] != "queries" and body_hash(text) == target_hash:
            kinds.append("content_hash")
        if kinds:
            matches.append({"path": str(path), "match": "+".join(kinds)})
    return {
        "canonical_url": target_url or None,
        "content_sha256": target_hash or None,
        "duplicate": bool(matches),
        "matches": matches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wiki-root", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", default="")
    group.add_argument("--file", type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect(args.wiki_root, args.url, args.file), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
