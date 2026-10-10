"""Conops HTML checks and unchanged Markdown CLI/JSON contract."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/conops/scripts/quality_gate.py'
spec = importlib.util.spec_from_file_location('conops_quality_gate', SCRIPT)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def document(html=False, includes=1, excludes=1):
    parts = []
    for section in gate.REQUIRED_SECTIONS:
        parts.append(f'<h2>{section}</h2>' if html else f'## {section}\n')
        parts.append('<p>具体约束与验收。</p>' if html else '具体约束与验收。\n')
        if section == '方案范围':
            for title, count in [('本次包含', includes), ('本次不包含', excludes)]:
                if html:
                    parts.append(f'<h3>{title}</h3><ul>' + '<li>范围条目</li>' * count + '</ul>')
                else:
                    parts.append(f'### {title}\n' + '- 范围条目\n' * count)
    return ''.join(parts)


class QualityGateTests(unittest.TestCase):
    def run_gate(self, text, suffix):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ('design' + suffix)
            path.write_text(text)
            result = subprocess.run([sys.executable, str(SCRIPT), str(path), '--json'],
                                    text=True, capture_output=True)
            return result.returncode, json.loads(result.stdout)

    def test_markdown_cli_json_compatibility(self):
        self.assertEqual(self.run_gate(document(), '.md'), (0, {'verdict': 'pass', 'failed': []}))

    def test_markdown_empty_scope_retains_old_verdict(self):
        self.assertEqual(self.run_gate(document(False, 0, 0), '.md'),
                         (0, {'verdict': 'pass', 'failed': []}))

    def test_html_scope_ignores_directory_anchor_text(self):
        page = '<nav><a href="#include">本次包含</a><a href="#exclude">本次不包含</a></nav>'
        self.assertEqual(self.run_gate(page + document(True), '.html'),
                         (0, {'verdict': 'pass', 'failed': []}))

    def test_html_prose_cannot_replace_scope_headings(self):
        page = document(True).replace('<h3>本次包含</h3>', '<p>本次包含</p>')
        page = page.replace('<h3>本次不包含</h3>', '<p>本次不包含</p>')
        status, output = self.run_gate(page, '.html')
        self.assertEqual(status, 1)
        self.assertTrue(any('4.scope' in failure for failure in output['failed']))

    def test_html_direct_without_markdown(self):
        page = '<html><head><title>此外</title><style>此外</style></head><body>' + document(True) + '</body></html>'
        self.assertEqual(self.run_gate(page, '.html'), (0, {'verdict': 'pass', 'failed': []}))

    def test_html_missing_section_not_supplied_by_non_body_text(self):
        page = document(True).replace('<h2>Core Logic</h2>', '')
        page += '<script>Core Logic</script><style>Core Logic</style><!-- Core Logic --><p>Core Logic</p>'
        status, output = self.run_gate(page, '.html')
        self.assertEqual(status, 1)
        self.assertTrue(any('3.sections' in failure for failure in output['failed']))

    def test_html_preformatted_text_cannot_replace_section_heading(self):
        page = document(True).replace('<h2>Core Logic</h2>', '<pre><code>## Core Logic</code></pre>')
        status, output = self.run_gate(page, '.html')
        self.assertEqual(status, 1)
        self.assertTrue(any('3.sections' in failure for failure in output['failed']))

    def test_html_inline_forbidden_text_and_entities(self):
        status, output = self.run_gate(document(True) + '<p>此<strong>外</strong>&#12290;</p>', '.html')
        self.assertEqual(status, 1)
        self.assertTrue(any('2.forbidden' in failure for failure in output['failed']))

    def test_html_scope_uses_list_items(self):
        status, output = self.run_gate(document(True, 2, 1), '.html')
        self.assertEqual(status, 1)
        self.assertTrue(any('include=2 exclude=1' in failure for failure in output['failed']))

    def test_html_prose_bullets_do_not_count_as_list_items(self):
        page = document(True, 2, 1).replace('</ul>', '</ul><p>- extra prose</p>')
        status, output = self.run_gate(page, '.html')
        self.assertEqual(status, 1)
        self.assertTrue(any('include=2 exclude=1' in failure for failure in output['failed']))

    def test_html_empty_scope_is_blocked(self):
        status, output = self.run_gate(document(True, 0, 0), '.html')
        self.assertEqual(status, 1)
        self.assertTrue(any('4.scope' in failure for failure in output['failed']))


if __name__ == '__main__':
    unittest.main()
