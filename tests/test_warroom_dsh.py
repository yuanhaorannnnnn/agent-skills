from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import socket
import threading
from unittest.mock import patch
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/warroom/scripts/dsh_agent.py'
spec = importlib.util.spec_from_file_location('warroom_dsh', SCRIPT)
dsh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dsh)


def catalog():
    return {
        'models': {'models': [{'enabled': True, 'selectionId': 'model-base',
                               'metadata': {'provider': 'provider', 'model': 'model'},
                               'reasoningItems': [{'enabled': True, 'id': 'low', 'selectionId': 'model-low'}]}]},
        'permissions': {'permissions': [{'enabled': True, 'selectionId': 'read-only',
                                         'metadata': {'preset': 'read-only'}}]},
        'presets': {'presets': [{'enabled': True, 'id': 'minimal'}]},
    }


class FakeBridge:
    identity = {'identity': {'runtime': 'dsh', 'protocolVersion': '1.0'}}

    def __init__(self):
        self.calls = []
        self.permission = 'read-only'
        self.model = 'model-low'

    def call(self, method, params=None):
        self.calls.append((method, params))
        catalogs = catalog()
        if method == 'catalog.listModels':
            return catalogs['models']
        if method == 'catalog.listPermissions':
            return catalogs['permissions']
        if method == 'catalog.listAgentPresets':
            return catalogs['presets']
        if method == 'session.getState':
            return {'status': 'idle', 'selections': {'permission': self.permission, 'model': self.model}}
        if method in ('session.createAndStart', 'session.startTurn', 'session.interrupt'):
            return {'accepted': True, 'sessionId': params['sessionId']}
        if method == 'session.getSnapshot':
            return {'items': ['first' if 'cursor' not in params else 'second'],
                    'nextCursor': 'page2' if 'cursor' not in params else None}
        raise AssertionError(method)


class JointAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.export = self.root / 'export'
        self.export.mkdir()
        self.material = self.export / 'evidence.md'
        self.material.write_text('S1: Route A succeeded in 9 of 10 trials.\n')
        self.packet = self.export / 'packet.json'
        self.write_packet('evidence.md', self.material.read_bytes())
        self.args = argparse.Namespace(command='start', packet=self.packet,
                                       job=self.root/'review'/'job.json', provider='provider',
                                       model='model', effort='low')

    def write_packet(self, path, data):
        self.packet.write_text(json.dumps({'version': 'v1',
                                          'question': 'What can this evidence establish?',
                                          'files': [{'path': path, 'sha256': hashlib.sha256(data).hexdigest()}]}))

    def test_only_allowlisted_bytes_sent_and_original_unchanged(self):
        (self.export/'not-shared.txt').write_text('UNSHARED SECRET')
        before = self.material.read_bytes()
        text, digest = dsh.packet_text(self.packet)
        self.assertIn('S1: Route A', text)
        self.assertNotIn('UNSHARED SECRET', text)
        self.assertEqual(self.material.read_bytes(), before)
        self.assertEqual(len(digest), 64)

    def test_inline_background_without_dossier_or_files(self):
        packet = {'version': 'discussion-v1', 'question': 'Which route should we test?',
                  'background': 'S1: Current chat proposes route A; unverified.', 'files': []}
        self.packet.write_text(json.dumps(packet))
        text, digest = dsh.packet_text(self.packet)
        self.assertIn(packet['background'], text)
        self.assertNotIn('Dossier reference:', text)
        packet['background'] = 'S1: Current chat proposes route B; unverified.'
        self.packet.write_text(json.dumps(packet))
        self.assertNotEqual(digest, dsh.packet_text(self.packet)[1])
        packet.pop('background')
        self.packet.write_text(json.dumps(packet))
        self.assertIn(packet['question'], dsh.packet_text(self.packet)[0])

    def test_legacy_dossier_reference_is_optional_and_preserved(self):
        packet = json.loads(self.packet.read_text())
        packet['dossier_id'] = 'existing-dossier'
        self.packet.write_text(json.dumps(packet))
        text, _ = dsh.packet_text(self.packet)
        self.assertIn('Dossier reference: existing-dossier', text)
        self.assertIn('S1: Route A', text)

    def test_rejects_invalid_background_packet_metadata(self):
        valid = {'version': 'v1', 'question': 'Review route A', 'files': []}
        for packet in ([], {**valid, 'version': ''}, {**valid, 'question': None},
                       {**valid, 'files': None}, {**valid, 'background': []},
                       {**valid, 'dossier_id': ''}):
            with self.subTest(packet=packet):
                self.packet.write_text(json.dumps(packet))
                with self.assertRaises(dsh.AdapterError):
                    dsh.packet_text(self.packet)

    def test_rejects_hash_change_escape_and_symlink(self):
        self.material.write_text('changed')
        with self.assertRaises(dsh.AdapterError):
            dsh.packet_text(self.packet)
        outside = self.root/'outside.txt'
        outside.write_text('outside')
        self.write_packet('../outside.txt', outside.read_bytes())
        with self.assertRaises(dsh.AdapterError):
            dsh.packet_text(self.packet)
        (self.export/'link.txt').symlink_to(outside)
        self.write_packet('link.txt', outside.read_bytes())
        with self.assertRaises(dsh.AdapterError):
            dsh.packet_text(self.packet)

    def test_rejects_oversized_material_before_dispatch(self):
        data = b'x' * (dsh.MAX_PACKET + 1)
        self.material.write_bytes(data)
        self.write_packet('evidence.md', data)
        with self.assertRaises(dsh.AdapterError):
            dsh.packet_text(self.packet)

    def test_permission_missing_never_falls_back_to_full_access(self):
        c = catalog()
        c['permissions']['permissions'][0]['metadata']['preset'] = 'danger-full-access'
        with self.assertRaises(dsh.AdapterError):
            dsh.selections(c, 'provider', 'model', 'low')

    def test_unknown_model_or_effort_does_not_silently_replace(self):
        for provider, model, effort in [('other', 'model', 'low'), ('provider', 'old', 'low'),
                                         ('provider', 'model', 'max')]:
            with self.subTest(model=model, effort=effort), self.assertRaises(dsh.AdapterError):
                dsh.selections(catalog(), provider, model, effort)

    def test_start_selects_before_prompt_and_persists_private_job(self):
        bridge = FakeBridge()
        result = dsh.execute(self.args, bridge)
        self.assertTrue(result['accepted'])
        sent = next(params for method, params in bridge.calls if method == 'session.createAndStart')
        self.assertEqual(sent['selections'], {'model': 'model-low', 'permission': 'read-only'})
        self.assertEqual(sent['agentPreset'], 'minimal')
        self.assertNotEqual(Path(sent['cwd']), self.export)
        job = dsh.read_job(self.args.job)
        self.assertEqual(sent['clientMessageId'], job['requestId'])
        self.assertEqual(self.args.job.stat().st_mode & 0o777, 0o600)
        with self.assertRaises(FileExistsError):
            dsh.execute(self.args, bridge)
        self.assertEqual(sum(m == 'session.createAndStart' for m, _ in bridge.calls), 1)

    def test_followup_reuses_job_and_rejects_permission_or_model_drift(self):
        bridge = FakeBridge()
        dsh.execute(self.args, bridge)
        brief = self.root/'follow-up.txt'
        brief.write_text('Which missing observation matters most?')
        args = argparse.Namespace(command='follow-up', job=self.args.job, brief=brief)
        for permission, model in [('danger-full-access', 'model-low'), ('read-only', 'changed')]:
            bridge.permission, bridge.model = permission, model
            with self.assertRaises(dsh.AdapterError):
                dsh.execute(args, bridge)
        self.assertFalse(any(m == 'session.startTurn' for m, _ in bridge.calls))
        bridge.permission, bridge.model = 'read-only', 'model-low'
        dsh.execute(args, bridge)
        sent = next(params for method, params in bridge.calls if method == 'session.startTurn')
        self.assertEqual(sent['sessionId'], dsh.read_job(self.args.job)['sessionId'])

    def test_result_collects_pages_and_cancel_targets_own_job(self):
        bridge = FakeBridge()
        dsh.execute(self.args, bridge)
        args = argparse.Namespace(command='result', job=self.args.job)
        result = dsh.execute(args, bridge)
        self.assertEqual([p['items'] for p in result['pages']], [['first'], ['second']])
        args.command = 'cancel'
        self.assertTrue(dsh.execute(args, bridge)['accepted'])
        self.assertEqual(bridge.calls[-1][1]['sessionId'], dsh.read_job(self.args.job)['sessionId'])

    def test_completion_requires_latest_request_terminal_event_and_actual_model(self):
        job = {'requestId': 'latest', 'provider': 'provider', 'model': 'model'}
        def page(request='latest', model='model', complete=True, terminal=True):
            items = [
                {'role': 'user', 'turnId': 'turn1', 'source': {'clientMessageId': request}},
                {'type': 'system', 'role': 'assistant', 'content': {'kind': 'reasoning', 'text': 'private'}},
                {'type': 'message', 'role': 'assistant', 'status': 'done', 'turnId': 'turn1',
                 'content': {'kind': 'markdown', 'text': 'opinion'},
                 'source': {'provider': 'provider', 'model': model}},
            ]
            if terminal:
                items.append({'type': 'turn.end', 'turnId': 'turn1',
                              'content': {'reason': {'kind': 'completed'}}})
            return {'items': items, 'snapshotComplete': complete, 'nextCursor': None}
        for kwargs in ({'request': 'old'}, {'model': 'other'}, {'complete': False}, {'terminal': False}):
            with self.subTest(kwargs=kwargs):
                self.assertFalse(dsh.summarize({'status': 'idle'}, [page(**kwargs)], job)['completed'])
        result = dsh.summarize({'status': 'idle'}, [page()], job)
        self.assertTrue(result['completed'])
        self.assertEqual(result['finalMessages'], ['opinion'])
        self.assertNotIn('private', json.dumps(result))
        with_tool = page()
        with_tool['items'].append({'type': 'tool-call', 'turnId': 'turn1'})
        result = dsh.summarize({'status': 'idle'}, [with_tool], job)
        self.assertTrue(result['toolsObserved'])
        self.assertFalse(result['completed'])

    def test_real_transport_correlates_fragmented_frames_and_redacts_remote_errors(self):
        endpoint = self.root/'endpoint.json'
        endpoint.write_text(json.dumps({'version': 1, 'host': '127.0.0.1', 'port': 1234, 'token': 'secret'}))
        endpoint.chmod(0o600)
        client, server = socket.socketpair()
        server_errors = []
        def serve():
            try:
                with server, server.makefile('rwb') as stream:
                    request = json.loads(stream.readline())
                    self.assertEqual(request['params']['authToken'], 'secret')
                    frame = json.dumps({'jsonrpc': '2.0', 'id': request['id'],
                                        'result': {'identity': {'runtime': 'dsh', 'protocolVersion': '1.0'}}}).encode()+b'\n'
                    stream.write(frame[:11]); stream.flush()
                    stream.write(frame[11:]); stream.flush()
                    request = json.loads(stream.readline())
                    stream.write((json.dumps({'jsonrpc': '2.0', 'method': 'notification', 'params': {}})+'\n').encode())
                    stream.write((json.dumps({'jsonrpc': '2.0', 'id': request['id'],
                                              'error': {'code': -1, 'message': 'secret'}})+'\n').encode())
                    stream.flush()
            except BaseException as error:
                server_errors.append(error)
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        with patch.object(dsh.socket, 'create_connection', return_value=client):
            bridge = dsh.Bridge(endpoint, timeout=2)
            try:
                with self.assertRaises(dsh.AdapterError) as caught:
                    bridge.call('ping')
                self.assertNotIn('secret', str(caught.exception))
            finally:
                bridge.close()
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(server_errors, [])

    def test_endpoint_permissions_and_remote_host_rejected_without_connecting(self):
        endpoint = self.root/'endpoint.json'
        endpoint.write_text(json.dumps({'version': 1, 'host': 'evil.example', 'port': 443, 'token': 'secret'}))
        endpoint.chmod(0o600)
        with self.assertRaises(dsh.AdapterError):
            dsh.Bridge(endpoint)
        endpoint.chmod(0o644)
        with self.assertRaises(dsh.AdapterError):
            dsh.Bridge(endpoint)


if __name__ == '__main__':
    unittest.main()
