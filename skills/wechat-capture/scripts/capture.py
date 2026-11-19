#!/usr/bin/env python3
"""Capture public WeChat articles into caller-selected directories."""
import os
import argparse
import hashlib
import json
from pathlib import Path

_DSH_ROOT = os.environ.get("DSH_DATA_ROOT") or os.path.join("/media", os.environ.get("USER", ""), "2T")
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from urllib.parse import urlsplit

SCRIPTS = Path(__file__).resolve().parents[3] / 'skills' / 'acquisition' / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import ingest_wechat_article as adapter
import discover_wechat_album as albums
import source_identity


def capture(url, output, command):
    adapter.validate_wechat_url(url)
    if urlsplit(url).path != '/s' and not urlsplit(url).path.startswith('/s/'):
        raise ValueError('expected a WeChat article URL')
    identity = hashlib.sha256(source_identity.canonical_url(url).encode()).hexdigest()[:20]
    target = output / identity
    if target.exists():
        raise FileExistsError(f'capture already exists: {target}')
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.wechat-', dir=output) as temp:
        temp = Path(temp)
        log = adapter.run_cli_in_staging(url, temp / 'source', command)
        source = adapter.single_markdown_file(temp / 'source')
        text = source.read_text(encoding='utf-8')
        title, author, published, body = adapter.parse_cli_markdown(text, url)
        references = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', body)
        missing = []
        for ref in references:
            if not ref.startswith('images/'):
                missing.append(ref)
                continue
            path = (source.parent / ref).resolve()
            image_root = (source.parent / 'images').resolve()
            if not path.is_relative_to(image_root) or not path.is_file() or not path.stat().st_size:
                missing.append(ref)
        counts = re.findall(r'✅\s*(\d+)\s*/\s*(\d+)', log)
        downloaded, detected = map(int, counts[-1]) if counts else (0, 0)
        if '图片下载失败' in log and not missing:
            missing.append('image download failure reported by extractor')
        if detected != downloaded:
            missing.append(f'extractor downloaded {downloaded} of {detected} images')
        result = {'source_url': url, 'title': title, 'author': author,
                  'published': published, 'markdown': 'article.md',
                  'images_detected': detected, 'images_downloaded': downloaded,
                  'image_references': len(references), 'missing_images': missing,
                  'image_status': 'partial' if missing else ('checked' if counts else 'unverified'),
                  'content_completeness': 'unverified',
                  'extractor': 'wechat-article-to-markdown'}
        bundle = temp / 'bundle'
        bundle.mkdir()
        (bundle / 'article.md').write_text(text + '\n', encoding='utf-8')
        if (source.parent / 'images').exists():
            shutil.copytree(source.parent / 'images', bundle / 'images')
        (bundle / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        bundle.rename(target)
    return {'path': str(target), **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', help='public article or album URL')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--limit', type=int, help='required for album capture')
    parser.add_argument('--order', choices=['latest', 'oldest'], default='latest')
    parser.add_argument('--command', default='wechat-article-to-markdown')
    args = parser.parse_args()
    try:
        if urlsplit(args.url).path == '/mp/appmsgalbum':
            if not args.limit or args.limit < 1:
                raise ValueError('album capture requires a positive --limit')
            data = albums.compile_manifest(args.url, albums.fetch_album_dom(args.url, args.command, albums.DEFAULT_MAX_SCROLLS))
            # An unknown declared count cannot establish complete discovery.
            if data['declared_items'] is None or not data['complete']:
                raise ValueError('album completeness cannot be established; no articles captured')
            if not str(data['album_id']).isdigit():
                raise ValueError('album ID must be numeric')
            data = albums.apply_selection(data, args.limit, args.order)
            urls = [item['url'] for item in data['items']]
        else:
            if args.limit is not None:
                raise ValueError('--limit is only for album capture')
            data = None
            urls = [args.url]
        results = []
        for url in urls:
            try:
                results.append({'status': 'captured', **capture(url, args.output.resolve(), args.command)})
            except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
                results.append({'status': 'error', 'source_url': url, 'error': str(error)})
        report = {'album': data, 'results': results}
        if data is not None:
            args.output.mkdir(parents=True, exist_ok=True)
            report_path = args.output / f"album-{data['album_id']}-{uuid.uuid4().hex[:12]}.json"
            report['report_path'] = str(report_path.resolve())
            with report_path.open('x', encoding='utf-8') as file:
                json.dump(report, file, ensure_ascii=False, indent=2)
                file.write('\n')
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if any(item['status'] == 'error' or item.get('image_status') == 'partial' for item in results) else 0
    except (OSError, RuntimeError, ValueError, subprocess.TimeoutExpired) as error:
        print(f'error: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
