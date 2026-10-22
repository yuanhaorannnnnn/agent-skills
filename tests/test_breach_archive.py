import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/breach/scripts/render_archive.py'
spec = importlib.util.spec_from_file_location('render_archive', SCRIPT)
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.package = self.root / 'package'
        self.package.mkdir()
        self.entry = self.package / 'dossier.md'
        self.entry.write_text('# Overview\n\nPreserve **facts** and `identifiers`.\n')
        self.source = self.root / 'original.md'
        self.source.write_text('# Source\n\nOriginal boundary.\n')
        self.manifest = self.package / 'manifest.json'
        self.catalog = self.root / 'dossier-index.json'
        self.data = dict(schema_version=1, id='example', title='Example archive', aliases=['Example dossier'], scope='test/example', as_of='2026-10-20', entry='dossier.md', materials=[dict(id='M01', title='Original', kind='report', source_ref='S01', sources=['S01'])], sources=[dict(id='S01', path=str(self.source), evidence='original', read_status='partial', locator='lines 1-3', read_at='2026-10-20', sha256=hashlib.sha256(self.source.read_bytes()).hexdigest())], gaps=['One explicit gap'])

    def save_inputs(self):
        self.manifest.write_text(json.dumps(self.data))
        row = {k: self.data[k] for k in ('id', 'scope', 'title', 'aliases')}
        row['path'] = str(self.manifest)
        self.catalog.write_text(json.dumps(dict(schema_version=1, dossiers=[row])))

    def run_render(self):
        self.save_inputs()
        before = {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        document, receipt = renderer.render(self.manifest, self.catalog)
        self.assertEqual(before, {str(p): p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        return document, receipt

    def test_preserves_content_and_does_not_write(self):
        document, receipt = self.run_render()
        self.assertIn('Original boundary.', document)
        self.assertIn('One explicit gap', document)
        self.assertIn('lines 1-3', document)
        self.assertIn('original / partial', document)
        self.assertEqual(receipt['source_mutations'], 0)
        self.assertEqual(receipt['material_count'], 1)
        self.assertEqual(receipt['design_sha256'], hashlib.sha256(renderer.DESIGN.read_bytes()).hexdigest())
        self.assertEqual(receipt['inputs'][str(renderer.DESIGN)], receipt['design_sha256'])

    def test_changed_original_rejected(self):
        self.source.write_text('Changed')
        with self.assertRaisesRegex(ValueError, 'source changed'):
            self.run_render()

    def test_escape_and_dangling_source_rejected(self):
        self.data['entry'] = '../original.md'
        with self.assertRaisesRegex(ValueError, 'escapes'):
            self.run_render()
        self.data['entry'] = 'dossier.md'
        self.data['materials'][0]['sources'] = ['unknown']
        with self.assertRaisesRegex(ValueError, 'unresolved'):
            self.run_render()

    def test_duplicate_material_rejected(self):
        self.data['materials'].append(self.data['materials'][0].copy())
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            self.run_render()

    def test_unread_source_not_embedded(self):
        self.data['sources'][0]['read_status'] = 'unread'
        document, _ = self.run_render()
        self.assertNotIn('Original boundary.', document)
        self.assertIn('正文未嵌入', document)

    def test_html_is_escaped_and_remote_images_do_not_load(self):
        self.entry.write_text('<script>alert(1)</script>\n\n![remote](https://example.invalid/pixel.png)\n\n[unsafe](javascript:alert(1))\n\n{{SOURCES}}\n')
        document, _ = self.run_render()
        self.assertNotIn('<script>alert(1)', document)
        self.assertNotIn('src="https://', document)
        self.assertNotIn('href="javascript:', document)
        self.assertIn('{{SOURCES}}', document)

    def test_registered_image_preserves_bytes(self):
        raw = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aV1cAAAAASUVORK5CYII=')
        image = self.root / 'image.png'
        image.write_bytes(raw)
        self.entry.write_text(f'![original]({image})')
        self.data['sources'].append(dict(id='S02', path=str(image), evidence='original', read_status='read', read_at='2026-10-20', locator='full image', sha256=hashlib.sha256(raw).hexdigest()))
        document, _ = self.run_render()
        self.assertIn('data:image/png;base64,' + base64.b64encode(raw).decode(), document)
        self.data['sources'].pop()
        with self.assertRaisesRegex(ValueError, 'unregistered'):
            self.run_render()

    def test_markdown_table_and_graph_code_preserved(self):
        self.entry.write_text('| Name | Value |\n| --- | --- |\n| Strict | 50ms |\n\n```mermaid\ngraph TD\nA-->B\n```')
        document, _ = self.run_render()
        self.assertIn('<table>', document)
        self.assertIn('50ms', document)
        self.assertIn('language-mermaid', document)
        self.assertIn('A--&gt;B', document)

    def test_cli_requires_archive_and_rejects_input_overwrite(self):
        self.save_inputs()
        before = self.entry.read_bytes()
        result = subprocess.run([sys.executable, str(SCRIPT), '--archive', str(self.manifest), '--catalog', str(self.catalog), '-o', str(self.entry)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.entry.read_bytes(), before)
        target = self.root / 'render/index.html'
        result = subprocess.run([sys.executable, str(SCRIPT), '--archive', str(self.manifest), '--catalog', str(self.catalog), '-o', str(target)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(target.is_file())
        self.assertEqual(json.loads(target.with_suffix('.render.json').read_text())['route'], 'archive')

    def test_output_cannot_overwrite_unembedded_registered_source(self):
        self.data['sources'][0]['read_status'] = 'unread'
        self.save_inputs()
        before = self.source.read_bytes()
        result = subprocess.run([sys.executable, str(SCRIPT), '--archive', str(self.manifest), '--catalog', str(self.catalog), '-o', str(self.source)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.source.read_bytes(), before)

    def test_unregistered_or_mismatched_dossier_rejected(self):
        self.save_inputs()
        self.catalog.write_text(json.dumps(dict(schema_version=1, dossiers=[])))
        with self.assertRaisesRegex(ValueError, 'exactly one catalog entry'):
            renderer.render(self.manifest, self.catalog)
        self.save_inputs()
        data = json.loads(self.catalog.read_text())
        data['dossiers'][0]['path'] = str(self.source)
        self.catalog.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'catalog path mismatch'):
            renderer.render(self.manifest, self.catalog)

    def test_nonstandard_dossier_cannot_bypass_upstream_gate(self):
        self.save_inputs()
        self.data.pop('aliases')
        self.manifest.write_text(json.dumps(self.data))
        with self.assertRaisesRegex(ValueError, 'dossier gate rejected'):
            renderer.render(self.manifest, self.catalog)

    def test_cli_catalog_is_required(self):
        self.save_inputs()
        target = self.root / 'output.html'
        result = subprocess.run([sys.executable, str(SCRIPT), '--archive', str(self.manifest), '-o', str(target)], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(target.exists())

    def test_telemetry_accepts_archive_route(self):
        log = self.root / 'telemetry.jsonl'
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/skill_telemetry.py'), '--path', str(log), '--skill', 'breach', '--runtime', 'codex', '--trigger', 'explicit', '--outcome', 'pass', '--route', 'archive', '--expected-route', 'archive', '--decision', 'style=archive-template'], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(log.read_text())['route_match'])


if __name__ == '__main__':
    unittest.main()
