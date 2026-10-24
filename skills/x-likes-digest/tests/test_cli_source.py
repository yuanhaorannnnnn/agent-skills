import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'digest', Path(__file__).resolve().parents[1] / 'scripts/x_likes_digest.py'
)
digest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(digest)


class RoutingTests(unittest.TestCase):
    def test_cli_only_reads_allowlisted_endpoints(self):
        result = subprocess.CompletedProcess([], 0, '{"data":[]}', '')
        with patch.object(digest.subprocess, 'run', return_value=result) as run:
            digest.run_xurl('/2/users/123/liked_tweets?max_results=5')
            command = run.call_args.args[0]
            self.assertEqual(command[-5:-1], ['--auth', 'oauth2', '-X', 'GET'])
            self.assertEqual(run.call_args.kwargs['timeout'], 45)
            for path in ['/2/tweets', '/2/users/123/bookmarks', 'https://example.com/2/users/me']:
                with self.assertRaises(ValueError):
                    digest.run_xurl(path)
            self.assertEqual(run.call_count, 1)

    def test_cli_api_errors_cannot_become_empty_success(self):
        for payload in [{'errors': [{'title': 'Forbidden'}]}, {'status': 402}, []]:
            result = subprocess.CompletedProcess([], 0, json.dumps(payload), '')
            with patch.object(digest.subprocess, 'run', return_value=result):
                with self.assertRaises(RuntimeError):
                    digest.run_xurl('/2/users/me')

    def test_cli_auth_and_credit_failures_stop_without_echoing_diagnostics(self):
        for stdout, stderr in [('{"status":402}', 'private diagnostic'),
                               ('{}', 'OAuth refresh failed: private diagnostic')]:
            result = subprocess.CompletedProcess([], 1, stdout, stderr)
            with patch.object(digest.subprocess, 'run', return_value=result):
                with self.assertRaisesRegex(RuntimeError, 'stop') as error:
                    digest.run_xurl('/2/users/me')
                self.assertNotIn('private diagnostic', str(error.exception))

    def snapshot(self, root, posts, next_token=None):
        raw = {'user': {'id': '123', 'username': 'haoran_yuan'},
               'data': [{'id': p, 'text': 'post ' + p} for p in posts],
               'includes': {}, 'meta': {}}
        if next_token:
            raw['meta']['next_token'] = next_token
        p = root / 'mcp.json'
        p.write_text(json.dumps(raw))
        return p

    def test_mcp_seen_boundary_and_incomplete_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p = self.snapshot(root, ['3', '2', '1'], 'next')
            _, posts, _ = digest.load_mcp_source(str(p), {'seen': {'2': 'seen'}})
            self.assertEqual([post['id'] for post in posts], ['3'])
            with self.assertRaisesRegex(ValueError, 'Partial'):
                digest.load_mcp_source(str(p), {'seen': {}})
            raw = json.loads(p.read_text())
            raw['user']['username'] = 'other'
            p.write_text(json.dumps(raw))
            with self.assertRaises(ValueError):
                digest.load_mcp_source(str(p), {})

    def test_mcp_build_preserves_ledger_and_uses_no_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.snapshot(root, ['3', '2', '1'], 'next')
            state = {'baseline_at': '2026-10-01', 'seen': {'2': 'seen'}}
            state_path = root / 'state.json'
            state_path.write_text(json.dumps(state))
            before = state_path.read_bytes()
            args = argparse.Namespace(source_json=None, mcp_source=str(source), limit=0)
            with patch.object(digest, 'STATE_PATH', state_path), \
                 patch.object(digest, 'ISSUES_DIR', root / 'issues'), \
                 patch.object(digest, 'run_xurl', side_effect=AssertionError('CLI called')), \
                 contextlib.redirect_stdout(io.StringIO()):
                digest.probe(args)
                digest.build(args)
            manifests = list((root / 'issues').glob('*/pending.json'))
            self.assertEqual(len(manifests), 1)
            manifest = json.loads(manifests[0].read_text())
            self.assertEqual(manifest['parts'][0]['post_ids'], ['3'])
            self.assertEqual(state_path.read_bytes(), before)
            state_path.write_text('{}')
            with patch.object(digest, 'STATE_PATH', state_path):
                with self.assertRaisesRegex(ValueError, 'baseline-missing'):
                    digest.build(args)


if __name__ == '__main__':
    unittest.main()
