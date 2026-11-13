import concurrent.futures
import datetime as dt
import importlib.util
import json
import multiprocessing
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('guard', Path(__file__).parents[1] / 'scripts/x_paid_guard.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
NOW = dt.datetime(2026, 11, 13, 9, tzinfo=g.SHANGHAI)
PAGE = ['/2/users/123/tweets?max_results=20&tweet.fields=created_at']


class GuardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)
        self.policy = {'x': {'task_limit_usd': '1', 'daily_limit_usd': '1', 'monthly_limit_usd': '6', 'max_results': 20}}
        self.write_policy()
        (self.p / 'x-state.json').write_text('{"schema_version":1,"reservations":[]}')

    def tearDown(self):
        self.tmp.cleanup()

    def write_policy(self):
        (self.p / 'policy.json').write_text(json.dumps(self.policy))

    def reserve(self, args=PAGE, task='task', now=NOW):
        return g.reserve(args, self.p, now, task)

    def test_allowed_costs(self):
        self.assertEqual(g.plan(PAGE)['cost'], 100000)
        self.assertEqual(g.plan(['/2/tweets?ids=1,2,3'])['cost'], 15000)
        self.assertEqual(g.plan(['--app', 'named', '/2/users/me'])['cost'], 10000)
        self.assertEqual(g.plan(['/2/tweets/123'])['cost'], 5000)
        self.assertEqual(g.plan(['/2/usage/credits'])['cost'], 0)

    def test_unknown_write_unbounded_and_expansion_denied(self):
        cases = [
            ['/2/tweets/search/all?query=test&max_results=10'],
            ['/2/users/123/tweets'], ['/2/users/123/tweets?max_results=21'],
            ['/2/users/123/tweets?max_results=20&max_results=1'],
            ['/2/users/123/tweets?max_results=10&expansions=author_id'],
            ['-X', 'POST', '/2/tweets'], ['post', 'hello'],
            ['-d', '{}', '/2/tweets'], ['-H', 'Authorization: secret', '/2/users/me'],
            ['--verbose', '/2/users/me'], ['token'], ['mcp', 'https://api.x.com/mcp'],
            ['/2/unknown'], ['https://other.example/2/users/me'],
            ['//api.x.com/2/users/me'], ['/2/users/%6de'],
            ['/2/tweets?ids=' + ','.join(str(x) for x in range(21))],
            ['/2/usage/credits?foo=bar'],
        ]
        for args in cases:
            with self.subTest(args=args), self.assertRaises(g.Denied):
                self.reserve(args)
        self.assertEqual(json.loads((self.p/'x-state.json').read_text())['reservations'], [])

    def test_task_daily_monthly_limits(self):
        for limit in ['task_limit_usd', 'daily_limit_usd', 'monthly_limit_usd']:
            with self.subTest(limit=limit):
                (self.p/'x-state.json').write_text('{"schema_version":1,"reservations":[]}')
                self.policy['x'] = dict(task_limit_usd='100', daily_limit_usd='100', monthly_limit_usd='100', max_results=20)
                self.policy['x'][limit] = '0.10'
                self.write_policy()
                self.reserve()
                with self.assertRaises(g.Denied):
                    self.reserve(task='task' if limit=='task_limit_usd' else 'other')

    def test_new_day_does_not_reset_month(self):
        self.policy['x']['monthly_limit_usd'] = '.10'
        self.write_policy()
        self.reserve()
        with self.assertRaises(g.Denied):
            self.reserve(task='new-task', now=NOW+dt.timedelta(days=1))

    def test_concurrent_reservations_do_not_overspend(self):
        def attempt(_):
            try:
                self.reserve(task='distinct-'+str(_))
                return True
            except g.Denied:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as pool:
            successes = list(pool.map(attempt, range(30)))
        self.assertEqual(sum(successes), 10)
        rows = json.loads((self.p/'x-state.json').read_text())['reservations']
        self.assertEqual(sum(x['cost'] for x in rows), 1000000)

    def test_cross_process_account_limit(self):
        ctx = multiprocessing.get_context('fork')
        q = ctx.Queue()
        def attempt(n):
            try:
                self.reserve(task=f'process-{n}')
                q.put(True)
            except g.Denied:
                q.put(False)
        processes = [ctx.Process(target=attempt, args=(i,)) for i in range(20)]
        for child in processes:
            child.start()
        for child in processes:
            child.join(10)
            self.assertEqual(child.exitcode, 0)
        self.assertEqual(sum(q.get(timeout=2) for _ in processes), 10)

    def test_missing_or_corrupt_state_and_policy_fail_closed(self):
        for name, content in [('x-state.json', 'bad'), ('x-state.json', '{}'), ('x-state.json', '{"schema_version":1,"reservations":[{}]}'), ('policy.json', 'bad')]:
            with self.subTest(name=name,content=content):
                self.setUp_files()
                (self.p/name).write_text(content)
                with self.assertRaises(g.Denied):
                    self.reserve()
        for name in ['x-state.json', 'policy.json']:
            self.setUp_files()
            (self.p/name).unlink()
            with self.assertRaises(g.Denied):
                self.reserve()

    def setUp_files(self):
        self.write_policy()
        (self.p/'x-state.json').write_text('{"schema_version":1,"reservations":[]}')

    def test_response_checkpoint_and_failure_reservation(self):
        called = []
        def fake(cmd, **kw):
            called.append((cmd, kw))
            # Reservation is durably visible before any network action.
            self.assertEqual(len(json.loads((self.p/'x-state.json').read_text())['reservations']), 1)
            return subprocess.CompletedProcess(cmd, 1, '{"status":402}', 'payment required')
        code, out, err = g.run(PAGE, self.p, fake, NOW, 'task')
        self.assertEqual(code, 1)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0][1]['timeout'], 45)
        self.assertEqual(called[0][0][0], g.REAL_BINARY)
        cp = list((self.p/'checkpoints').glob('*.json'))
        self.assertEqual(len(cp), 1)
        self.assertEqual(stat.S_IMODE(cp[0].stat().st_mode), 0o600)
        self.assertEqual(json.loads(cp[0].read_text())['stdout'], out)
        record = json.loads((self.p/'x-state.json').read_text())['reservations'][0]
        self.assertEqual(record['cost'], 100000)
        self.assertEqual(record['status'], 'failed_reserved')
        with self.assertRaises(g.Denied):
            self.reserve(task='other-task')
        self.assertEqual(self.reserve(['/2/usage/credits'])[1], None)
        self.assertEqual(stat.S_IMODE((self.p/'x-state.json').stat().st_mode), 0o600)

    def test_timeout_keeps_reservation(self):
        def timeout(*a, **kw):
            raise subprocess.TimeoutExpired('fake', 45, output=b'partial')
        code, out, err = g.run(PAGE, self.p, timeout, NOW, 'task')
        self.assertEqual((code, out), (124, 'partial'))
        row = json.loads((self.p/'x-state.json').read_text())['reservations'][0]
        self.assertEqual(row['status'], 'timeout_reserved')
        self.assertEqual(row['cost'], 100000)

    def test_recovery_local_commands_need_no_state(self):
        (self.p/'x-state.json').unlink()
        for args in [['--version'], ['auth', 'status'], ['auth', 'apps', 'add', 'name', '--client-id', 'test'], ['--app','name','auth','oauth2']]:
            with self.subTest(args=args):
                fake=lambda cmd,**kw:subprocess.CompletedProcess(cmd,0,'local','')
                self.assertEqual(g.run(args,self.p,fake,NOW,'task')[0],0)


if __name__ == '__main__':
    unittest.main()
