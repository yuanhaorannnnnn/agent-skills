from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_monthly_harness_eval as monthly


class MonthlyEvalTests(unittest.TestCase):
    def test_blind_grading_cannot_override_failed_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            arms = {a: {'returncode': 0, 'response': 'answer', 'artifact_pass': False,
                        'artifact_checks': [{'passed': False}]} for a in ('baseline', 'skill')}
            report = {'cases': [{'id': 1, 'prompt': 'task', 'expected_output': 'oracle', **arms}]}
            (directory / 'execute.json').write_text(json.dumps(report))
            scores = {'cases': [{'id': 'execute:1', **{label: {'verdict': 'pass', 'reason': 'judge claim'}
                                                      for label in ('A', 'B')}}]}
            with patch.dict('os.environ', {'CODEX_HOME': tmp + '/custom-auth'}), patch.object(monthly, 'run_arm', return_value={'returncode': 0, 'response': json.dumps(scores)}) as call:
                grading = monthly.grade(directory)
            self.assertEqual(call.call_args.args[1], directory / "custom-auth/auth.json")
            prompt = call.call_args.args[3]
            self.assertNotIn('"baseline"', prompt)
            self.assertNotIn('"skill"', prompt)
            self.assertEqual(grading['scores']['cases'][0]['A']['verdict'], 'fail')
            self.assertEqual(grading['scores']['cases'][0]['B']['verdict'], 'fail')
            self.assertEqual(len(grading['disputes']), 2)
            self.assertEqual(grading['raw_scores']['cases'][0]['A']['verdict'], 'pass')
            monthly.write_report(directory, grading)
            self.assertIn('真实人工介入', (directory / 'report.md').read_text())

    def test_suite_preserves_scoped_source_snapshots(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = ['scripts/run_skill_ab_eval.py', 'scripts/run_monthly_harness_eval.py',
                     'tests/test_skill_ab_eval.py', 'tests/test_monthly_harness_eval.py',
                     'references/model-skill-ab-eval.md', 'skills/execute/SKILL.md',
                     'skills/execute/evals/evals.json', *monthly.TELEMETRY_SOURCES]
            for name in names:
                p = root / name
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text('source snapshot')
            arm = {'returncode': 0, 'response': 'answer', 'artifact_checks': [], 'artifact_pass': None}
            def fake_run(command, **kwargs):
                output = Path(command[command.index('--output') + 1])
                output.write_text(json.dumps({'cases': [{'id': 1, 'prompt': 'task',
                    'expected_output': 'oracle', 'baseline': arm, 'skill': arm}]}))
                return monthly.subprocess.CompletedProcess(command, 0)
            score = {'cases': [{'id': 'execute:1', **{label: {'verdict': 'pass', 'reason': 'ok'}
                        for label in ('A', 'B')}}]}
            with patch.object(monthly, 'ROOT', root), patch.object(monthly, 'SKILLS', ('execute',)), \
                    patch.object(monthly.subprocess, 'check_output', return_value='fixture') as check, \
                    patch.object(monthly.subprocess, 'run', side_effect=fake_run), \
                    patch.object(monthly, 'run_arm', return_value={'returncode': 0, 'response': json.dumps(score)}):
                self.assertEqual(monthly.main(), 0)
            directory = next((root / '.eval/monthly').iterdir())
            self.assertEqual((directory / 'sources/scripts/run_monthly_harness_eval.py').read_text(), 'source snapshot')
            self.assertTrue(any(c.args[0][:3] == ['git', 'diff', 'HEAD'] for c in check.call_args_list))
            self.assertTrue((directory / 'report.md').is_file())

    def test_initialization_failure_leaves_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with patch.object(monthly, 'ROOT', root), patch.object(monthly.subprocess,
                    'check_output', side_effect=FileNotFoundError('codex absent')):
                self.assertEqual(monthly.main(), 1)
            dirs = list((root / '.eval/monthly').iterdir())
            self.assertEqual(len(dirs), 1)
            self.assertTrue((dirs[0] / 'report.md').is_file())
            self.assertEqual(json.loads((dirs[0] / 'manifest.json').read_text())['error'], 'initialization_failed')

    def test_judge_missing_cases_is_not_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            report = {'cases': [{'id': 1, 'prompt': 'task', 'expected_output': 'oracle',
                       **{a: {'returncode': 0, 'response': 'answer', 'artifact_checks': []}
                          for a in ('baseline', 'skill')}}]}
            (directory / 'codify.json').write_text(json.dumps(report))
            bad_outputs = [
                {"cases": []},
                {"cases": [{"id": "codify:1", "A": {"verdict": "pass"}, "B": {"verdict": "pass"}}]},
            ]
            for output in bad_outputs:
                with self.subTest(output=output), patch.object(monthly, 'run_arm', return_value={
                        'returncode': 0, 'response': json.dumps(output)}):
                    grading = monthly.grade(directory)
                self.assertIsNone(grading['scores'])
                self.assertEqual(grading['error'], 'judge_output_invalid')

    def test_telemetry_uses_previous_shanghai_month_and_no_private_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'events.jsonl'
            def event(timestamp, **extra):
                return {'skill': 'breach', 'outcome': 'pass', 'timestamp': timestamp, **extra}
            events = [
                event('2026-08-31T15:59:59+00:00'),  # before September in Shanghai
                event('2026-08-31T16:00:00+00:00', route='general-page',
                      expected_route='discussion-digest', steps={'render': 'pending'}, prompt='PRIVATE'),
                event('2026-09-30T15:59:59+00:00'),  # legacy event, within September
                event('2026-09-30T16:00:00+00:00'),  # October start: excluded
                event('2026-09-01T00:00:00'),  # no timezone: excluded with warning
                event('invalid'),
            ]
            path.write_text('\n'.join(json.dumps(row) for row in events) + '\npartial')
            summary = monthly.collect_telemetry(datetime(2026, 10, 1, 3, tzinfo=ZoneInfo('Asia/Shanghai')), path)
            self.assertEqual(summary['period'], '2026-09')
            data = summary['skills']['breach']
            self.assertEqual(data['outcomes'], {'breach:pass': 2})
            self.assertEqual(data['routes']['breach:unobserved'], 1)
            self.assertEqual(data['unknown_expectations'], 1)
            self.assertEqual(data['mismatches'], {'breach:discussion-digest->general-page': 1})
            self.assertEqual(data['invalid_timestamps'], 2)
            self.assertEqual(data['invalid_lines'], 1)
            self.assertNotIn('PRIVATE', json.dumps(summary))
            self.assertNotIn('partial', json.dumps(summary))
            self.assertEqual(summary['skills']['execute']['outcomes'], {})
            report = '\n'.join(monthly.telemetry_lines(summary))
            self.assertIn('| breach | 2 | 2 / 0 / 0 / 0 | 1/2 | 1 | 1 |', report)
            self.assertIn('步骤状态', report)

    def test_missing_telemetry_is_unmeasured_and_year_rollover_is_correct(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = monthly.collect_telemetry(datetime(2027, 1, 1, tzinfo=ZoneInfo('Asia/Shanghai')),
                                               Path(tmp) / 'missing')
            self.assertEqual(summary['period'], '2026-12')
            self.assertEqual(summary['status'], 'missing')
            self.assertIn('未测', '\n'.join(monthly.telemetry_lines(summary)))

    def test_eval_failure_report_still_includes_saved_telemetry(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            log = directory / 'events.jsonl'
            log.write_text('')
            summary = monthly.collect_telemetry(datetime(2026, 10, 1, tzinfo=ZoneInfo('Asia/Shanghai')), log)
            (directory / 'telemetry-summary.json').write_text(json.dumps(summary))
            monthly.write_report(directory, {'scores': None})
            report = (directory / 'report.md').read_text()
            self.assertIn('Judge 未产生有效结果', report)
            self.assertIn('Skill 使用遥测 — 2026-09', report)
            self.assertIn('| sanitize | 0 |', report)



if __name__ == '__main__':
    unittest.main()
