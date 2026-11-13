import concurrent.futures
import datetime as dt
import importlib.util
import json
import multiprocessing
from pathlib import Path
import stat
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('paid_budget', Path(__file__).parents[1] / 'scripts/paid_budget.py')
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)
NOW = dt.datetime(2026, 11, 13, 10, tzinfo=g.ZONE)


class BudgetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.p = Path(self.tmp.name)
        self.policy = {'services': {'firecrawl': dict(unit='credits', daily_limit='20', task_limit='10', cycle_limit='1000', cycle_start='2026-10-26T07:34:50Z', cycle_end='2026-11-26T07:34:50Z', observed_spend='710')}}
        self.save_policy()
        (self.p/'budget-state.json').write_text('{"schema_version":1,"reservations":[]}')

    def tearDown(self):
        self.tmp.cleanup()

    def save_policy(self):
        (self.p/'policy.json').write_text(json.dumps(self.policy))

    def reserve(self, units='1', task='issue-2026-W46', operation='scrape', provider='firecrawl', now=NOW):
        return g.reserve(dict(provider=provider, task=task, operation=operation, units=units), self.p, now)

    def test_exact_decimal_sum(self):
        cfg = self.policy['services']['firecrawl']
        cfg.update(observed_spend='0.7', cycle_limit='1', daily_limit='1', task_limit='1')
        self.save_policy()
        self.reserve('0.1')
        self.reserve('0.2')
        with self.assertRaises(g.Denied):
            self.reserve('0.000000000001')
        s = g.status(self.p, NOW)
        self.assertEqual(s['providers']['firecrawl']['cycle_remaining'], '0.0')

    def test_cycle_observed_plus_reservations(self):
        cfg = self.policy['services']['firecrawl']
        cfg.update(daily_limit='1000', task_limit='1000')
        self.save_policy()
        self.reserve('290')
        with self.assertRaises(g.Denied):
            self.reserve('1', task='new-task')

    def test_day_and_task_budget(self):
        self.reserve('10')
        with self.assertRaises(g.Denied):
            self.reserve('1')
        self.reserve('10', task='second')
        with self.assertRaises(g.Denied):
            self.reserve('1', task='third')
        self.reserve('1', task='third', now=NOW+dt.timedelta(days=1))
        with self.assertRaises(g.Denied):
            self.reserve('1', task='issue-2026-W46', now=NOW+dt.timedelta(days=1))

    def test_cycle_boundary_and_future_cycle_denied(self):
        for when in [dt.datetime(2026,10,1,tzinfo=g.ZONE), g.instant('2026-11-26T07:34:50Z'), dt.datetime(2026,12,1,tzinfo=g.ZONE)]:
            with self.subTest(when=when), self.assertRaises(g.Denied):
                self.reserve(now=when)
        self.assertEqual(g.status(self.p, dt.datetime(2026,12,1,tzinfo=g.ZONE))['providers']['firecrawl']['status'], 'blocked')

    def test_unknown_missing_and_invalid_budget_denied(self):
        with self.assertRaises(g.Denied):
            self.reserve(provider='unknown')
        for field in ['unit','daily_limit','task_limit','cycle_limit','cycle_start','cycle_end','observed_spend']:
            cfg = self.policy['services']['firecrawl']
            saved = cfg[field]
            cfg[field] = None
            self.save_policy()
            with self.subTest(field=field), self.assertRaises(g.Denied):
                self.reserve()
            cfg[field] = saved
        self.save_policy()
        for units in [None, 0, -1, 0.1, 'NaN', 'Infinity', '1e-13', '1e100', True]:
            with self.subTest(units=units), self.assertRaises(g.Denied):
                self.reserve(units=units)

    def test_corrupt_or_missing_state(self):
        for content in ['garbage', '{}', '{"schema_version":1,"reservations":[{}]}']:
            (self.p/'budget-state.json').write_text(content)
            with self.assertRaises(g.Denied):
                self.reserve()
        (self.p/'budget-state.json').unlink()
        with self.assertRaises(g.Denied):
            self.reserve()

    def test_status_does_not_write(self):
        before = {f.name:(f.read_bytes(),f.stat().st_mtime_ns) for f in self.p.iterdir()}
        g.status(self.p,NOW)
        after = {f.name:(f.read_bytes(),f.stat().st_mtime_ns) for f in self.p.iterdir()}
        self.assertEqual(before, after)

    def test_concurrency_global_budget(self):
        def attempt(n):
            try:
                self.reserve('1',task='task-'+str(n))
                return True
            except g.Denied:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(attempt, range(40)))
        self.assertEqual(sum(results),20)
        self.assertEqual(len(json.loads((self.p/'budget-state.json').read_text())['reservations']),20)

    def test_cross_process_budget(self):
        ctx=multiprocessing.get_context('fork')
        q=ctx.Queue()
        def attempt(n):
            try:
                self.reserve('10',task='process-'+str(n))
                q.put(True)
            except g.Denied:
                q.put(False)
        children=[ctx.Process(target=attempt,args=(i,)) for i in range(8)]
        for c in children:c.start()
        for c in children:
            c.join(10)
            self.assertEqual(c.exitcode,0)
        self.assertEqual(sum(q.get(timeout=2) for c in children),2)

    def test_metadata_only_and_private_ledger(self):
        self.reserve(task='a-private-but-stable-task')
        p=self.p/'budget-state.json'
        self.assertEqual(stat.S_IMODE(p.stat().st_mode),0o600)
        self.assertNotIn('a-private-but-stable-task',p.read_text())
        with self.assertRaises(g.Denied):
            self.reserve(operation='a complete request body with spaces')
        with self.assertRaises(g.Denied):
            g.reserve({'provider':'firecrawl','task':'task','operation':'scrape','units':'1','body':'private'},self.p,NOW)

    def test_unit_change_does_not_hide_reservations(self):
        self.reserve()
        self.policy['services']['firecrawl']['unit']='USD'
        self.save_policy()
        with self.assertRaises(g.Denied):self.reserve()
        self.assertEqual(g.status(self.p,NOW)['providers']['firecrawl']['status'],'blocked')


if __name__=='__main__':
    unittest.main()
