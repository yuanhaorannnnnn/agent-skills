#!/usr/bin/env python3
"""Read-only package and identity-catalog checks. No semantic deduplication."""
import argparse
import json
import re
import unicodedata
from datetime import date
from pathlib import Path


def norm(value):
    return ''.join(unicodedata.normalize('NFKC', value).casefold().split())


def validate(manifest_path, catalog_path):
    errors = []

    def need(ok, message):
        if not ok:
            errors.append(message)

    def identity(row):
        for field in ('id', 'scope', 'title'):
            need(isinstance(row.get(field), str) and bool(row[field].strip()), f'missing {field}')
        need(bool(re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', row.get('id', ''))), 'invalid id')
        need(isinstance(row.get('aliases'), list) and all(isinstance(x, str) and x.strip() for x in row['aliases']), 'invalid aliases')

    def local_file(value, base=None):
        need(isinstance(value, str) and bool(value), 'invalid file path')
        if not isinstance(value, str) or not value:
            return
        p = Path(value)
        if base is not None:
            need(not p.is_absolute() and (base / p).resolve().is_relative_to(base), 'package path escapes root')
            p = base / p
        else:
            need(p.is_absolute(), 'source/catalog path must be absolute')
        need(p.is_file(), f'file unavailable: {value}')

    manifest_path = Path(manifest_path).resolve()
    package = json.loads(manifest_path.read_text())
    catalog = json.loads(Path(catalog_path).read_text())
    need(package.get('schema_version') == 1, 'unsupported manifest schema')
    need(catalog.get('schema_version') == 1, 'unsupported catalog schema')
    identity(package)
    date.fromisoformat(package['as_of'])
    local_file(package.get('entry'), manifest_path.parent)
    need(isinstance(package.get('gaps'), list), 'missing gaps list')
    sources = package['sources']
    source_ids = set()
    for source in sources:
        sid = source['id']
        need(isinstance(sid, str) and bool(sid) and sid not in source_ids, 'duplicate/empty source id')
        source_ids.add(sid)
        need(bool(source.get('path')) != bool(source.get('url')), 'source needs path xor url')
        need(source.get('evidence') in ('original', 'derived'), 'invalid evidence')
        status = source.get('read_status')
        need(status in ('read', 'partial', 'unread', 'missing'), 'invalid read status')
        need(bool(source.get('locator')), 'missing source locator')
        if status in ('read', 'partial'):
            date.fromisoformat(source['read_at'])
        if source.get('path') and status != 'missing':
            local_file(source['path'])
        if status == 'missing':
            need(bool(package.get('gaps')), 'missing source requires gap record')
        if source.get('url'):
            need(bool(re.match(r'https?://[^/\s]+', source['url'])), 'invalid source url')
    material_ids = set()
    need(bool(package['materials']), 'empty materials')
    for item in package['materials']:
        mid = item['id']
        need(isinstance(mid, str) and bool(mid) and mid not in material_ids, 'duplicate/empty material id')
        material_ids.add(mid)
        need(bool(item.get('title')) and bool(item.get('kind')), 'missing material identity')
        refs = item.get('sources')
        need(isinstance(refs, list) and bool(refs) and all(x in source_ids for x in refs), 'unresolved material sources')
        need(bool(item.get('path')) != bool(item.get('source_ref')), 'material needs path xor source_ref')
        if item.get('path'):
            local_file(item['path'], manifest_path.parent)
        if item.get('source_ref'):
            need(item['source_ref'] in source_ids and item['source_ref'] in (refs or []), 'unresolved source_ref')
    ids, names, matches = set(), {}, []
    for row in catalog['dossiers']:
        identity(row)
        rid = row['id']
        need(rid not in ids, 'duplicate dossier id')
        ids.add(rid)
        local_file(row.get('path'))
        for name in {norm(x) for x in [row['title']] + row['aliases']}:
            key = (norm(row['scope']), name)
            need(key not in names or names[key] == rid, 'scope/title/alias collision')
            names[key] = rid
        if rid == package['id']:
            matches.append(row)
    need(len(matches) == 1, 'manifest must have exactly one catalog entry')
    if len(matches) == 1:
        row = matches[0]
        need(norm(row['scope']) == norm(package['scope']), 'catalog scope mismatch')
        need(row['title'] == package['title'] and set(row['aliases']) == set(package['aliases']), 'catalog identity mismatch')
        need(Path(row['path']).resolve() == manifest_path, 'catalog path mismatch')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest')
    parser.add_argument('--catalog', required=True)
    args = parser.parse_args()
    try:
        errors = validate(args.manifest, args.catalog)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors = [f'invalid input: {type(exc).__name__}']
    print(json.dumps({'verdict': 'blocked' if errors else 'pass', 'errors': errors}, ensure_ascii=False))
    return int(bool(errors))


if __name__ == '__main__':
    raise SystemExit(main())
