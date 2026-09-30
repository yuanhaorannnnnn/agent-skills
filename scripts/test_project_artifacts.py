import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from project_artifacts import task_dir

ROOT = Path(__file__).resolve().parents[1]


class ProjectArtifactsTests(unittest.TestCase):
    def test_layout_requires_both_project_markers_and_rejects_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.agent-artifacts-repo-owned').touch()
            self.assertEqual(task_dir(root, 'req'), root / '.proposal/req')
            (root / 'Docs/guides').mkdir(parents=True)
            (root / 'Docs/guides/documentation.md').touch()
            self.assertEqual(task_dir(root, 'req', runtime=True), root / '.local/tasks/req')
            self.assertEqual(task_dir(root, 'bug', 'repair'), root / 'Docs/tasks/repair-bug')
            for value in ('', '..', '../escape', '/absolute', 'a\\b'):
                with self.assertRaises(ValueError):
                    task_dir(root, value)

    def test_all_gate_commands_keep_their_output_in_selected_layout(self):
        for owned in (False, True):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                subprocess.run(['git', 'init', '-q', str(root)], check=True)
                if owned:
                    (root / '.agent-artifacts-repo-owned').touch()
                    (root / 'Docs/guides').mkdir(parents=True)
                    (root / 'Docs/guides/documentation.md').touch()
                for workflow in ('repair', 'tasking'):
                    for script in (ROOT / 'skills' / workflow / 'scripts').glob('*gate.py'):
                        with self.subTest(owned=owned, gate=script.name):
                            # Missing Phase 0 deliberately blocks; path routing must still work.
                            result = subprocess.run([sys.executable, str(script), 'layout-routing-test-unassigned', '--repo', str(root), '--json'], capture_output=True, text=True)
                            self.assertNotIn('Traceback', result.stderr)
                            output = task_dir(root, 'layout-routing-test-unassigned', workflow) / (script.stem + '.json')
                            self.assertTrue(output.is_file(), result.stderr)
                            self.assertEqual(json.loads(output.read_text())['verdict'], 'blocked')
                if owned:
                    self.assertFalse((root / '.proposal').exists())
                    self.assertFalse((root / '.planning').exists())

    def test_traceback_uses_matching_local_cache(self):
        script = ROOT / 'skills/tasking/scripts/engage_gate.py'
        spec = importlib.util.spec_from_file_location('engage_gate', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / '.agent-artifacts-repo-owned').touch()
            (root / 'Docs/guides').mkdir(parents=True)
            (root / 'Docs/guides/documentation.md').touch()
            with patch.object(module.subprocess, 'run') as run:
                run.return_value.returncode = 1
                run.return_value.stdout = '{}'
                module.check_traceback(root, 'req')
                command = run.call_args.args[0]
                self.assertEqual(command[command.index('--dir') + 1], str(root / '.local/tasks/req'))


if __name__ == '__main__':
    unittest.main()
