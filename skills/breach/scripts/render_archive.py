#!/usr/bin/env python3
"""Render an existing dossier manifest without changing its package or sources."""
import argparse
import base64
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import tempfile
from urllib.parse import unquote, urlsplit

TEMPLATE = Path(__file__).resolve().parents[1] / 'assets/archive.html'
DESIGN = TEMPLATE.with_name('archive-DESIGN.md')
TYPEWRITER_FONT = TEMPLATE.with_name('ZhaohuaTypeWriter.woff2')
FONT_LICENSE = TEMPLATE.with_name('archive-typewriter-LICENSE.txt')


def esc(value):
    return html.escape(str(value), quote=True)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def render(manifest_path, catalog_path, template_path=TEMPLATE):
    from markdown_it import MarkdownIt
    manifest_path = Path(manifest_path).resolve()
    root = manifest_path.parent
    inputs = {}

    def read(path, expected=None):
        path = path.resolve()
        raw = path.read_bytes()
        digest = sha(raw)
        if expected and digest != expected:
            raise ValueError(f'source changed; update dossier first: {path}')
        inputs[str(path)] = digest
        return raw

    def inside(value):
        path = Path(value)
        resolved = (root / path).resolve()
        if path.is_absolute() or not resolved.is_relative_to(root):
            raise ValueError('package path escapes root')
        return resolved

    catalog_path = Path(catalog_path).resolve()
    # Dossier owns validation. Archive cannot accept a free-form manifest as a substitute.
    gate_path = Path(__file__).resolve().parents[2] / 'dossier/scripts/dossier_gate.py'
    spec = importlib.util.spec_from_file_location('dossier_input_gate', gate_path)
    gate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate)
    try:
        errors = gate.validate(manifest_path, catalog_path)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ValueError('dossier gate rejected malformed input') from exc
    if errors:
        raise ValueError('dossier gate rejected input: ' + '; '.join(errors))
    read(catalog_path)
    data = json.loads(read(manifest_path))
    sources = {source['id']: source for source in data['sources']}
    registered = {Path(s['path']).resolve(): s for s in sources.values() if s.get('path')}
    md = MarkdownIt('commonmark', {'html': False}).enable('table')

    def path_button(path, label):
        return f'<button class="path-link" data-path="{esc(path)}">{esc(label)}</button>'

    def asset(path):
        source = registered.get(path.resolve())
        if not path.resolve().is_relative_to(root) and not source:
            raise ValueError('unregistered local image read')
        if source and source['read_status'] in ('missing', 'unread'):
            return None
        raw = read(path, source.get('sha256') if source else None)
        mime = ('image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else
                'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else
                'image/gif' if raw.startswith((b'GIF87a', b'GIF89a')) else
                'image/webp' if raw[:4] == b'RIFF' and raw[8:12] == b'WEBP' else None)
        if not mime:
            return None
        return f'data:{mime};base64,' + base64.b64encode(raw).decode()

    def links(tokens, idx, options, env):
        token = tokens[idx]
        href = token.attrGet('href') or ''
        scheme = urlsplit(href).scheme.lower()
        if scheme in ('http', 'https', 'mailto'):
            return f'<a href="{esc(href)}" target="_blank" rel="noreferrer noopener">'
        if href.startswith('#'):
            # Original heading anchors may belong to another material; show the identity.
            return f'<a href="#" data-path="{esc(href)}">'
        return f'<a href="#" data-path="{esc(unquote(href))}">'

    def images(tokens, idx, options, env):
        token = tokens[idx]
        src = token.attrGet('src') or ''
        alt = token.content
        if urlsplit(src).scheme or src.startswith('//'):
            return f'<span class="attachment-note">图片链接：{esc(alt)} · {esc(src)}</span>'
        path = Path(unquote(src))
        path = path.resolve() if path.is_absolute() else (env['base'] / path).resolve()
        uri = asset(path)
        if uri:
            return f'<img class="evidence-image" src="{uri}" alt="{esc(alt)}" tabindex="0" role="button" aria-label="放大：{esc(alt)}">'
        return path_button(path, alt or '图片附件未预览')

    md.add_render_rule('link_open', lambda self, tokens, idx, options, env: links(tokens, idx, options, env))
    md.add_render_rule('image', lambda self, tokens, idx, options, env: images(tokens, idx, options, env))

    def content(path, expected=None):
        suffix = path.suffix.lower()
        if suffix in ('.png', '.jpg', '.jpeg', '.gif', '.webp'):
            uri = asset(path)
            return f'<img class="evidence-image" src="{uri}" alt="{esc(path.name)}" tabindex="0" role="button" aria-label="放大附件">' if uri else path_button(path, '附件未预览')
        if suffix not in ('.md', '.markdown', '.txt', '.json', '.py', '.csv', '.log'):
            return path_button(path, '查看附件位置（未预览）')
        text = read(path, expected).decode('utf-8')
        if suffix in ('.md', '.markdown'):
            # Frontmatter is metadata, already exposed separately, not body prose.
            text = re.sub(r'\A---\r?\n.*?\r?\n---\r?\n', '', text, count=1, flags=re.S)
            return md.render(text, {'base': path.parent})
        return '<pre><code>' + esc(text) + '</code></pre>'

    def source_buttons(refs):
        return ''.join(f'<button class="source-button" data-source="{esc(sid)}">{esc(sid)}</button>' for sid in refs)

    entry = inside(data['entry'])
    overview_id = 'overview'
    material_ids = {item['id'] for item in data['materials']}
    while overview_id in material_ids:
        overview_id = '_' + overview_id
    articles = [f'<article class="paper" data-panel="{esc(overview_id)}" tabindex="-1"><div class="sheet-head"><span>卷宗概览</span><span>{esc(data["id"])}</span></div>{content(entry)}</article>']
    nav, contents, ids = [], [], set()
    for i, item in enumerate(data['materials'], 1):
        mid = item['id']
        refs = item['sources']
        ids.add(mid)
        title, kind = item['title'], item['kind']
        label = f'<span class="material-number">{esc(mid)}</span><span>{esc(title)}<small>{esc(kind)}</small></span>'
        nav.append(f'<button data-select="{esc(mid)}">{label}</button>')
        contents.append(f'<li><span>{esc(mid)}</span><span>{esc(title)}</span><small>{esc(kind)}</small></li>')
        note = ''
        if item.get('source_ref'):
            sid = item['source_ref']
            source = sources[sid]
            note = f'<p class="status">来源登记：{esc(source["evidence"])} / {esc(source["read_status"])} · {esc(source.get("locator", ""))}</p>'
            if source['read_status'] in ('missing', 'unread') or source.get('url'):
                body = '<p>正文未嵌入；请查看来源登记。</p>'
            else:
                body = content(Path(source['path']).resolve(), source.get('sha256'))
        else:
            body = content(inside(item['path']))
        articles.append(f'<article class="paper" data-panel="{esc(mid)}" tabindex="-1" hidden><div class="sheet-head"><span>{esc(data["id"])} / {esc(mid)}</span><span>{i:02} / {len(data["materials"]):02}</span></div><div class="type">{esc(kind)}</div><h1>{esc(title)}</h1>{note}{body}<footer class="sheet-footer">来源登记 {source_buttons(refs)}</footer></article>')
    source_details = []
    for sid, source in sources.items():
        path = source.get('path') or source['url']
        source_details.append(f'<section data-source-panel="{esc(sid)}" hidden><h3>{esc(sid)}</h3><p>{esc(source["evidence"])} / {esc(source["read_status"])}</p><p>{esc(source.get("locator", ""))}</p><code class="source-path">{esc(path)}</code><p>登记读取日期：{esc(source.get("read_at", "未登记"))}</p><p>登记 hash：<code>{esc(source.get("sha256", "未登记"))}</code></p></section>')
    template_bytes = Path(template_path).read_bytes()
    design_bytes = read(DESIGN)
    substitutions = dict(OVERVIEW_ID=esc(overview_id), TITLE=esc(data['title']), ID=esc(data['id']), SCOPE=esc(data['scope']), DATE=esc(data['as_of']), COUNT=str(len(ids)), CONTENTS=''.join(contents), NAV=''.join(nav), ARTICLES=''.join(articles), SOURCES=''.join(source_details), SOURCE_BUTTONS=source_buttons(sources), GAPS=''.join('<li>'+esc(x)+'</li>' for x in data['gaps']) or '<li>材料包未登记缺口。</li>', PROVENANCE=esc(f'route=archive; dossier_gate=pass; catalog={catalog_path}; manifest={manifest_path}; manifest_sha256={inputs[str(manifest_path)]}; template={Path(template_path).resolve()}; template_sha256={sha(template_bytes)}'))
    substitutions['TYPEWRITER_FONT'] = base64.b64encode(read(TYPEWRITER_FONT)).decode()
    substitutions['FONT_LICENSE'] = esc(read(FONT_LICENSE).decode())
    substitutions['PROVENANCE'] += esc(f'; design={DESIGN}; design_sha256={sha(design_bytes)}')
    document = re.sub(r'\{\{([A-Z_]+)\}\}', lambda m: substitutions[m[1]], template_bytes.decode())
    receipt = dict(route='archive', manifest=str(manifest_path), catalog=str(catalog_path), dossier_gate='pass', dossier_id=data['id'], inputs=inputs, template=str(Path(template_path).resolve()), template_sha256=sha(template_bytes), material_count=len(ids), source_count=len(sources), network_fetches=0, source_mutations=0, protected_paths=[str(p) for p in registered])
    receipt.update(design=str(DESIGN), design_sha256=sha(design_bytes))
    return document, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive', required=True, type=Path, help='Existing dossier manifest.json')
    parser.add_argument('--catalog', required=True, type=Path, help='Dossier identity catalog; must register this exact manifest')
    parser.add_argument('-o', '--output', required=True, type=Path)
    args = parser.parse_args()
    try:
        output = args.output.resolve()
        if output.is_relative_to(args.archive.resolve().parent):
            raise ValueError('output must be outside source package')
        document, receipt = render(args.archive, args.catalog)
        metadata = output.with_suffix('.render.json')
        protected = set(receipt['inputs']) | set(receipt['protected_paths']) | {str(TEMPLATE.resolve())}
        if str(output) in protected or str(metadata) in protected:
            raise ValueError('output would overwrite a source or template')
        receipt['output_sha256'] = sha(document.encode())
        output.parent.mkdir(parents=True, exist_ok=True)
        for target, text in [(output, document), (metadata, json.dumps(receipt, ensure_ascii=False, indent=2)+'\n')]:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=target.parent, delete=False) as stream:
                stream.write(text)
                temp = Path(stream.name)
            temp.replace(target)
        print(json.dumps({'status': 'pass', 'output': str(output), 'materials': receipt['material_count']}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, KeyError, TypeError, ImportError, AttributeError) as exc:
        parser.exit(1, f'Archive render blocked: {exc}\n')


if __name__ == '__main__':
    main()
