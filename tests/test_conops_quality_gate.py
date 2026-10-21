"""Regression probes for false approval and artificial document constraints."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/conops/scripts/quality_gate.py'

class QualityGateTests(unittest.TestCase):
    def run_gate(self, text, suffix='.md'):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ('design' + suffix)
            if text is not None:
                path.write_text(text)
            result = subprocess.run([sys.executable, str(SCRIPT), str(path), '--json'],
                                    text=True, capture_output=True)
            output = json.loads(result.stdout)
            self.assertEqual(output['check_kind'], 'structure_lint')
            self.assertEqual(output['semantic_review'], 'required')
            return result.returncode, output

    def test_short_real_body_no_fixed_sections(self):
        self.assertEqual(self.run_gate('# 筛选\n默认显示全部；解析后按 level 过滤，坏行保留既有处理。')[0], 0)

    def test_all_placeholder_sections_block(self):
        self.assertEqual(self.run_gate('\n'.join(f'## Section {i}\n待定。' for i in range(14)))[0], 1)

    def test_empty_heading_and_metadata_block(self):
        for text in ['', '# Design', '---\nowner: test\n---\n# Design\n<!-- body -->']:
            with self.subTest(text=text): self.assertEqual(self.run_gate(text)[0], 1)

    def test_missing_file_is_machine_readable(self):
        self.assertEqual(self.run_gate(None)[0], 1)

    def test_exclusions_and_words_are_not_quality_proxies(self):
        self.assertEqual(self.run_gate('## 本次包含\n- 筛选\n- 导出\n## 本次不包含\n- 云同步\n此外，最大数据量需要实测。')[0], 0)

    def test_open_question_does_not_block_substantive_draft(self):
        self.assertEqual(self.run_gate('导出采用流式写入，失败保留原文件。\n## 最大数据量\n待定。')[0], 0)

    def test_html_headings_scripts_and_placeholders_not_body(self):
        text = '<head><title>Real design</title></head><h1>Design</h1><script>substance</script><style>substance</style><p>待定。</p>'
        self.assertEqual(self.run_gate(text, '.html')[0], 1)

    def test_html_inline_body_preserved(self):
        self.assertEqual(self.run_gate('<h1>导出</h1><p>写入<strong>临时文件</strong>后原子替换。</p>', '.html')[0], 0)

if __name__ == '__main__': unittest.main()
