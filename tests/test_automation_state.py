import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from automation_state import transition, body_hash

class StateTests(unittest.TestCase):
    def test_uncertain_delivery_cannot_resend_and_unique_match_recovers(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            data = dict(key='issue', body='a\r\nb', subject='test', recipient='fixture@example.invalid', date='2026-10-23', manifest=[])
            transition(d, 'prepare', data)
            transition(d, 'posting', {'key': 'issue'})
            transition(d, 'recover', {'key': 'issue'})
            with self.assertRaises(AssertionError): transition(d, 'posting', {'key': 'issue'})
            candidate = {k: data[k] for k in ('body', 'subject', 'recipient', 'date')}
            candidate['message_id'] = 'fixture-id'
            self.assertEqual(transition(d, 'recover', {'key': 'issue', 'sent': [candidate,candidate]})['status'], 'maybe_sent')
            self.assertEqual(transition(d, 'recover', {'key': 'issue', 'sent': [candidate]})['status'], 'sent')
            with self.assertRaises(AssertionError): transition(d, 'posting', {'key': 'issue'})
            self.assertEqual(body_hash('a\r\nb'), body_hash('a\nb'))

    def test_run_result_does_not_fabricate_notification_or_overwrite_facts(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            transition(d, 'facts', dict(key='doc', status='completed', revision=2, conclusion='fixture'))
            result=transition(d, 'run', dict(key='run-1', business_status='partial', notification_status='unverified', gate='fixture'))
            self.assertEqual(result['business_status'], 'partial')
            self.assertEqual(result['notification_status'], 'unverified')
            with self.assertRaises(AssertionError): transition(d, 'facts', dict(key='doc', status='failed'))
            import json
            state=json.loads((d/'reliability-state.json').read_text())
            self.assertEqual(state['facts']['doc']['revision'], 2)
            self.assertEqual(state['issues'], {})
