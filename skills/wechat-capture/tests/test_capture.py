import importlib.util
from pathlib import Path
import tempfile
import unittest
import sys
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('capture', Path(__file__).parents[1] / 'scripts/capture.py')
capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(capture)
URL = 'https://mp.weixin.qq.com/s/example'


def staging(url, root, command):
    article = root / 'article'
    (article / 'images').mkdir(parents=True)
    (article / 'images/a.png').write_bytes(b'image')
    (article / 'article.md').write_text('# Title\n\n---\n\n' + '正文' * 120 + '\n![a](images/a.png)\n![b](https://example.com/missing.png)', encoding='utf-8')
    return '✅ 1/2\n图片下载失败'


class CaptureTests(unittest.TestCase):
    @patch.object(capture.adapter, 'run_cli_in_staging', staging)
    def test_partial_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            out = Path(folder)
            result = capture.capture(URL, out, 'unused')
            self.assertEqual(result['image_status'], 'partial')
            self.assertEqual(result['images_detected'], 2)
            self.assertTrue((Path(result['path']) / 'images/a.png').exists())
            with self.assertRaises(FileExistsError):
                capture.capture(URL, out, 'unused')
            self.assertTrue((Path(result['path']) / 'article.md').exists())

    @patch.object(capture.adapter, 'run_cli_in_staging', staging)
    def test_invalid_host_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                capture.capture('https://example.com/s/x', Path(folder), 'unused')

    def test_album_requires_confirmed_complete_discovery(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(sys, 'argv', ['capture', 'https://mp.weixin.qq.com/mp/appmsgalbum?__biz=x&album_id=1', '--output', folder, '--limit', '1']), patch.object(capture.albums, 'fetch_album_dom', return_value={}), patch.object(capture.albums, 'compile_manifest', return_value={'declared_items': None, 'complete': True}), patch.object(capture, 'capture') as run, redirect_stderr(StringIO()):
            self.assertEqual(capture.main(), 1)
            run.assert_not_called()

    def test_album_records_success_and_failure(self):
        data = {'declared_items': 2, 'complete': True, 'album_id': '1', 'items': [{'url': URL, 'article_number': 2}, {'url': URL + '2', 'article_number': 1}]}
        with tempfile.TemporaryDirectory() as folder, patch.object(sys, 'argv', ['capture', 'https://mp.weixin.qq.com/mp/appmsgalbum?__biz=x&album_id=1', '--output', folder, '--limit', '2']), patch.object(capture.albums, 'fetch_album_dom', return_value={}), patch.object(capture.albums, 'compile_manifest', return_value=data), patch.object(capture, 'capture', side_effect=[{'image_status': 'checked'}, RuntimeError('failed')]), redirect_stdout(StringIO()):
            self.assertEqual(capture.main(), 1)
            import json
            reports = list(Path(folder).glob('album-*.json'))
            self.assertEqual(len(reports), 1)
            self.assertEqual([x['status'] for x in json.loads(reports[0].read_text())['results']], ['captured', 'error'])

if __name__ == '__main__':
    unittest.main()
