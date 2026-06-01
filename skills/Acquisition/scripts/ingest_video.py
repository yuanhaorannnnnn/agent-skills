#!/usr/bin/env python3
"""Download an online video into a wiki raw asset directory."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


SUPPORTED_HOSTS = {
    "youtube": ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"),
    "bilibili": ("bilibili.com", "www.bilibili.com", "m.bilibili.com", "b23.tv"),
    "x": ("x.com", "www.x.com", "twitter.com", "www.twitter.com", "mobile.twitter.com"),
    "xiaohongshu": (
        "xiaohongshu.com",
        "www.xiaohongshu.com",
        "xhslink.com",
        "www.xhslink.com",
    ),
}


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower().split(":")[0]
    for platform, hosts in SUPPORTED_HOSTS.items():
        if host in hosts or any(host.endswith("." + allowed) for allowed in hosts):
            return platform
    return "unknown"


def ensure_supported(url: str) -> str:
    platform = detect_platform(url)
    if platform == "unknown":
        supported = ", ".join(sorted(SUPPORTED_HOSTS))
        raise SystemExit(f"Unsupported URL host. Supported platforms: {supported}")
    return platform


def build_command(args: argparse.Namespace, output_dir: Path) -> list[str]:
    command = [
        args.yt_dlp,
        args.url,
        "--paths",
        f"home:{output_dir}",
        "--output",
        "%(id)s/%(id)s.%(ext)s",
        "--merge-output-format",
        "mp4",
        "--write-info-json",
        "--write-thumbnail",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs",
        args.sub_langs,
    ]

    if not args.playlist:
        command.append("--no-playlist")

    if args.cookies:
        command.extend(["--cookies", str(args.cookies)])

    if args.cookies_from_browser:
        command.extend(["--cookies-from-browser", args.cookies_from_browser])

    if args.proxy:
        command.extend(["--proxy", args.proxy])

    if args.user_agent:
        command.extend(["--user-agent", args.user_agent])

    if args.format:
        command.extend(["--format", args.format])

    if args.referer:
        command.extend(["--referer", args.referer])

    if args.js_runtime:
        command.extend(["--js-runtimes", args.js_runtime])

    return command


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a video from X/Twitter, Xiaohongshu, Bilibili, or YouTube into raw/assets/video."
    )
    parser.add_argument("url", help="Video URL to download.")
    parser.add_argument(
        "--wiki-root",
        type=Path,
        default=Path.cwd(),
        help="Wiki root directory. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory. Defaults to <wiki-root>/raw/assets/video.",
    )
    parser.add_argument(
        "--sub-langs",
        default="zh-Hans,zh,en.*",
        help="Subtitle languages passed to yt-dlp. Defaults to zh-Hans,zh,en.*",
    )
    parser.add_argument("--cookies", type=Path, help="Path to a Netscape cookies.txt file.")
    parser.add_argument(
        "--cookies-from-browser",
        help="Browser name for yt-dlp cookie import, for example chrome or firefox.",
    )
    parser.add_argument("--proxy", help="Proxy URL passed to yt-dlp.")
    parser.add_argument("--user-agent", help="Custom User-Agent passed to yt-dlp.")
    parser.add_argument("--referer", help="Custom Referer passed to yt-dlp.")
    parser.add_argument("--js-runtime", default="node", help="JS runtime for yt-dlp bot challenge solving (default: node).")
    parser.add_argument("--format", help="yt-dlp format selector.")
    parser.add_argument(
        "--playlist",
        action="store_true",
        help="Allow playlist downloads. Disabled by default.",
    )
    parser.add_argument(
        "--yt-dlp",
        default=shutil.which("yt-dlp") or "yt-dlp",
        help="yt-dlp executable path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned command without downloading.",
    )
    parser.add_argument(
        "--note",
        choices=("none", "summary", "concept", "comparison", "query", "auto"),
        default="none",
        help="Structured note mode for the surrounding workflow. Download v1 records this value only.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    platform = ensure_supported(args.url)

    if shutil.which(args.yt_dlp) is None and not Path(args.yt_dlp).exists():
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "yt-dlp not found",
                    "hint": "Install yt-dlp or pass --yt-dlp /path/to/yt-dlp.",
                },
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 127

    wiki_root = args.wiki_root.expanduser().resolve()
    output_dir = (
        args.output_dir.expanduser().resolve()
        if args.output_dir
        else wiki_root / "raw" / "assets" / "video"
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    command = build_command(args, output_dir)
    summary = {
        "ok": True,
        "platform": platform,
        "wiki_root": str(wiki_root),
        "output_dir": str(output_dir),
        "command": command,
        "dry_run": args.dry_run,
        "note": args.note,
        "note_implemented": False,
    }

    print(json.dumps(summary, ensure_ascii=False, indent=2))

    if args.dry_run:
        return 0

    completed = subprocess.run(command, check=False)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
