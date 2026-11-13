import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1]/'scripts'/'visual_telemetry.py'
spec = importlib.util.spec_from_file_location('visual_telemetry', SCRIPT)
visual = importlib.util.module_from_spec(spec); spec.loader.exec_module(visual)


class VisualTelemetryTests(unittest.TestCase):
    def test_cli_records_only_closed_metadata_and_reports_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'private'/'events.jsonl'
            subprocess.run([sys.executable,str(SCRIPT),'--path',str(path),'record','--medium','image',
                            '--inspection','reported_done','--delivery','unknown'],check=True)
            event = json.loads(path.read_text())
            self.assertTrue(visual.valid(event))
            self.assertEqual(event['content_idea'],'unknown')
            self.assertEqual(event['delivery'],'unknown')
            self.assertEqual(path.stat().st_mode & 0o777,0o600)
            self.assertEqual(visual.report(path)['counts']['inspection'],{'reported_done':1})
            with path.open('a') as f: f.write('{"private_content":"must not appear"}\n')
            result = visual.report(path)
            self.assertEqual(result['records'],1); self.assertEqual(result['invalid_lines'],1)
            self.assertNotIn('must not appear',json.dumps(result))

    def test_missing_and_symlink_do_not_create_or_follow(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d)/'private'; parent.mkdir(mode=0o700)
            missing = parent/'missing'
            self.assertEqual(visual.report(missing)['records'],0)
            self.assertFalse(missing.exists())
            target = Path(d)/'target'; target.write_text('protected')
            (parent/'events').symlink_to(target)
            event = {'schema_version':1,'timestamp':'2026-11-13T00:00:00+00:00',**{k:'unknown' for k in visual.FIELDS}}
            with self.assertRaises(OSError): visual.append(parent/'events',event)
            with self.assertRaises(OSError): visual.report(parent/'events')
            self.assertEqual(target.read_text(),'protected')
            target.chmod(0o600)
            os.link(target,parent/'hardlink')
            with self.assertRaises(PermissionError): visual.append(parent/'hardlink',event)
            self.assertEqual(target.read_text(),'protected')
            os.mkfifo(parent/'pipe')
            with self.assertRaises(OSError): visual.append(parent/'pipe',event)

    def test_concurrent_appends_are_whole_events(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'private'/'events'
            processes = [subprocess.Popen([sys.executable,str(SCRIPT),'--path',str(path),'record']) for _ in range(12)]
            self.assertTrue(all(p.wait()==0 for p in processes))
            result = visual.report(path)
            self.assertEqual(result['records'],12); self.assertEqual(result['invalid_lines'],0)

    def test_invalid_value_does_not_write(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)/'private'/'events'
            result = subprocess.run([sys.executable,str(SCRIPT),'--path',str(path),'record',
                                     '--medium','arbitrary-private-text'],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse(path.exists())


if __name__ == '__main__': unittest.main()
