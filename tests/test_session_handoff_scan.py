import importlib.util
import json
import multiprocessing
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/session_handoff_scan.py'
spec = importlib.util.spec_from_file_location('session_handoff_scan', SCRIPT)
scan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scan)


def entry(key, source='user', compactions=3, idle=180):
    return {'session_id': key, 'cwd': '/project', 'thread_sources': [] if source is None else [source],
            'compactions': compactions, 'last_ts': datetime.now(timezone.utc) - timedelta(minutes=idle), 'files': []}


def concurrent_mark(path, key):
    scan.mark_stage(Path(path), key, 'successor_created', 'child-' + key, 'test')


class RoutingTests(unittest.TestCase):
    def select(self, entries, handled=None, include=False):
        skipped = []
        found = scan.candidates({x['session_id']: x for x in entries}, {'handled': handled or {}}, 3, 120, 30, include, skipped)
        return found, skipped

    def test_native_user_and_agent_created_threads_remain_eligible(self):
        found, skipped = self.select([entry('user'), entry('created', 'agent_created_thread')])
        self.assertEqual([x['session_id'] for x in found], ['user', 'created'])
        self.assertTrue(all(x['action'] == 'handoff' for x in found))
        self.assertEqual(skipped, [])

    def test_automation_run_is_retained_without_handoff(self):
        found, skipped = self.select([entry('scheduled', 'automation')])
        self.assertEqual(found, [])
        self.assertEqual((skipped[0]['continuation_mode'], skipped[0]['continuation_reason']), ('scheduler', 'scheduled-run'))

    def test_unknown_and_conflicting_sources_do_not_guess(self):
        conflict = entry('conflict'); conflict['thread_sources'] = ['automation', 'user']
        found, skipped = self.select([entry('legacy', None), entry('future', 'new-kind'), conflict])
        self.assertEqual(found, [])
        self.assertEqual(len(skipped), 3)
        self.assertTrue(all(x['continuation_mode'] == 'unresolved' for x in skipped))

    def test_subagents_are_not_user_conversations_even_with_override(self):
        found, skipped = self.select([entry('worker', 'subagent')], {'worker': {'continuation_mode': 'handoff'}})
        self.assertEqual(found, [])
        self.assertEqual(skipped[0]['continuation_reason'], 'subagent')

    def test_recorded_automation_successor_inherits_scheduler(self):
        records = {'parent': {'stage': 'complete', 'successor_thread_id': 'child'}}
        found, skipped = self.select([entry('parent', 'automation'), entry('child', 'agent_created_thread')], records)
        self.assertEqual(found, [])
        self.assertEqual(skipped[0]['session_id'], 'child')
        self.assertEqual(skipped[0]['continuation_mode'], 'scheduler')

    def test_multiple_generation_inheritance(self):
        records = {'a': {'stage': 'complete', 'successor_thread_id': 'b'},
                   'b': {'stage': 'complete', 'successor_thread_id': 'c'}}
        found, skipped = self.select([entry('a', 'automation'), entry('b', 'agent_created_thread'), entry('c', 'agent_created_thread')], records)
        self.assertEqual(found, [])
        self.assertEqual(skipped[0]['session_id'], 'c')
        self.assertEqual(skipped[0]['continuation_mode'], 'scheduler')

    def test_interactive_successor_still_handoffs(self):
        records = {'parent': {'stage': 'complete', 'successor_thread_id': 'child'}}
        found, skipped = self.select([entry('parent'), entry('child', 'agent_created_thread')], records)
        self.assertEqual([x['session_id'] for x in found], ['child'])
        self.assertEqual(skipped, [])

    def test_long_recorded_chain_does_not_hit_python_recursion_limit(self):
        entries = {'root': entry('root', 'automation')}
        parents = {'c0': ['root']}
        parents.update({'c' + str(n): ['c' + str(n - 1)] for n in range(1, 1100)})
        self.assertEqual(scan.continuation('c1099', entries, {}, parents), ('scheduler', 'scheduled-run'))

    def test_explicit_handoff_can_promote_scheduled_run_or_successor(self):
        records = {'parent': {'stage': 'complete', 'successor_thread_id': 'child'},
                   'child': {'continuation_mode': 'handoff', 'continuation_reason': 'explicit user decision'}}
        found, _ = self.select([entry('parent', 'automation'), entry('child', 'agent_created_thread')], records)
        self.assertEqual([x['session_id'] for x in found], ['child'])
        found, _ = self.select([entry('fresh', 'automation')], {'fresh': {'continuation_mode': 'handoff', 'continuation_reason': 'explicit user decision'}})
        self.assertEqual(found[0]['action'], 'handoff')

    def test_explicit_scheduler_can_retain_interactive_thread(self):
        found, skipped = self.select([entry('user')], {'user': {'continuation_mode': 'scheduler', 'continuation_reason': 'explicit user decision'}})
        self.assertEqual(found, [])
        self.assertEqual(skipped[0]['continuation_reason'], 'explicit-continuation')

    def test_invalid_override_never_silently_falls_back_to_handoff(self):
        for record in [{'continuation_mode': 'typo', 'continuation_reason': 'user'},
                       {'continuation_mode': 'handoff'},
                       {'continuation_mode': 'handoff', 'continuation_reason': ' '}]:
            found, skipped = self.select([entry('user')], {'user': record})
            self.assertEqual(found, [])
            self.assertEqual(skipped[0]['continuation_reason'], 'continuation-override-invalid')

    def test_pending_successor_is_recovered_without_a_new_create(self):
        records = {'run': {'stage': 'successor_created', 'successor_thread_id': 'existing'}}
        found, skipped = self.select([entry('run', 'automation')], records)
        self.assertEqual(found[0]['action'], 'recover-existing')
        self.assertEqual(found[0]['successor_thread_id'], 'existing')
        self.assertEqual(skipped, [])

    def test_broken_pending_record_never_falls_back_to_create(self):
        found, skipped = self.select([entry('run')], {'run': {'stage': 'successor_created'}})
        self.assertEqual(found, [])
        self.assertEqual(skipped[0]['continuation_reason'], 'handoff-state-needs-verification')

    def test_unrecognized_stage_is_retained_for_verification(self):
        for stage in ['', False, 'unexpected']:
            found, skipped = self.select([entry('run')], {'run': {'stage': stage}})
            self.assertEqual(found, [])
            self.assertEqual(skipped[0]['continuation_reason'], 'handoff-state-needs-verification')

    def test_missing_parent_cycle_and_multiple_parents_are_unresolved(self):
        variants = [
            {'gone': {'stage': 'complete', 'successor_thread_id': 'child'}},
            {'child': {'successor_thread_id': 'other'}, 'other': {'successor_thread_id': 'child'}},
            {'a': {'successor_thread_id': 'child'}, 'b': {'successor_thread_id': 'child'}},
        ]
        for records in variants:
            with self.subTest(records=records):
                # A legacy record is already complete; include it only for read-only route diagnostics.
                found, skipped = self.select([entry('child', 'agent_created_thread')], records, include=True)
                self.assertEqual(found, [])
                self.assertEqual(skipped[0]['continuation_mode'], 'unresolved')

    def test_complete_and_legacy_records_stay_complete(self):
        for record in [{'stage': 'complete'}, {'handled_at': '2026-01-01'}, {'reason': 'legacy'}]:
            self.assertEqual(self.select([entry('done')], {'done': record}), ([], []))
        found, skipped = self.select([entry('done')], {'done': {'stage': 'complete'}}, include=True)
        self.assertEqual(found, [])
        self.assertEqual(skipped[0]['continuation_reason'], 'handoff-complete')

    def test_threshold_idle_age_and_compaction_order_unchanged(self):
        stale = entry('old'); stale['last_ts'] -= timedelta(days=31)
        found, _ = self.select([entry('small', compactions=2), entry('busy', idle=119), stale, entry('three'), entry('five', compactions=5)])
        self.assertEqual([x['session_id'] for x in found], ['five', 'three'])


class FileAndStateTests(unittest.TestCase):
    def test_rollouts_aggregate_sources_and_compactions_without_double_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for number, source in enumerate(['user', 'automation']):
                rows = [{'type': 'session_meta', 'payload': {'id': 'same', 'cwd': '/p', 'thread_source': source}},
                        {'type': 'compacted', 'payload': {}},
                        {'type': 'event_msg', 'payload': {'type': 'context_compacted'}}]
                (root / f'{number}.jsonl').write_text('\n'.join(json.dumps(x) for x in rows) + '\n')
            data = scan.aggregate(root)['same']
            self.assertEqual(data['compactions'], 2)
            self.assertEqual(data['thread_sources'], ['automation', 'user'])

    def test_source_is_never_inferred_from_automation_title_or_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 's.jsonl'
            path.write_text(json.dumps({'type': 'session_meta', 'payload': {'id': 's', 'source': 'vscode'}}) + '\n' +
                            json.dumps({'type': 'response_item', 'payload': {'text': 'Automation: fake'}}) + '\n')
            self.assertEqual(scan.scan_file(path)['thread_sources'], [])

    def test_mode_update_preserves_completed_records_and_other_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            original = {'version': 2, 'other': {'keep': 1}, 'handled': {'done': {'stage': 'complete', 'successor_thread_id': 'child', 'reason': 'verified'}}}
            path.write_text(json.dumps(original))
            scan.set_continuation(path, 'done', 'scheduler', 'user instruction')
            data = scan.load_state(path)
            self.assertEqual(data['other'], original['other'])
            for key, value in original['handled']['done'].items():
                self.assertEqual(data['handled']['done'][key], value)
            scan.mark_stage(path, 'done', 'complete', None, 'again')
            self.assertEqual(scan.load_state(path)['handled']['done']['continuation_mode'], 'scheduler')

    def test_mode_only_record_does_not_count_as_legacy_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            scan.set_continuation(path, 'run', 'handoff', 'user promotion')
            self.assertNotIn('stage', scan.load_state(path)['handled']['run'])
            self.assertEqual(RoutingTests().select([entry('run', 'automation')], scan.load_state(path)['handled'])[0][0]['action'], 'handoff')

    def test_adding_override_does_not_reopen_version_one_completion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            path.write_text(json.dumps({'version': 1, 'handled': {'old': {'reason': 'verified in v1'}}}))
            scan.set_continuation(path, 'old', 'handoff', 'user preference')
            state = scan.load_state(path)
            self.assertEqual(state['handled']['old']['stage'], 'complete')
            self.assertEqual(RoutingTests().select([entry('old')], state['handled']), ([], []))

    def test_concurrent_writers_do_not_lose_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.json'
            context = multiprocessing.get_context('fork')
            processes = [context.Process(target=concurrent_mark, args=(str(path), str(n))) for n in range(12)]
            for process in processes: process.start()
            for process in processes:
                process.join(10)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(len(scan.load_state(path)['handled']), 12)

    def test_cli_read_only_output_and_explicit_override_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); sessions = root / 'sessions'; sessions.mkdir(); state = root / 'state.json'
            rows = [{'timestamp': (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(),
                     'type': 'session_meta', 'payload': {'id': 'run', 'cwd': '/p', 'thread_source': 'automation'}}]
            rows += [{'type': 'compacted', 'payload': {}} for _ in range(3)]
            (sessions / 'run.jsonl').write_text('\n'.join(json.dumps(x) for x in rows))
            state.write_text('{"version": 2, "handled": {}}\n'); before = state.read_bytes()
            args = [sys.executable, str(SCRIPT), '--sessions-dir', str(sessions), '--state', str(state)]
            result = subprocess.run(args + ['--json'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertEqual(value['candidates'], [])
            self.assertEqual(value['skipped'][0]['continuation_mode'], 'scheduler')
            self.assertEqual(state.read_bytes(), before)
            self.assertFalse(state.with_suffix('.json.lock').exists())
            result = subprocess.run(args + ['--set-continuation', 'run', '--mode', 'handoff'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(state.read_bytes(), before)
            result = subprocess.run(args + ['--set-continuation', 'run', '--mode', 'handoff', '--reason', 'explicit user decision'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = subprocess.run(args + ['--json'], capture_output=True, text=True)
            self.assertEqual(json.loads(result.stdout)['candidates'][0]['action'], 'handoff')


if __name__ == '__main__':
    unittest.main()
