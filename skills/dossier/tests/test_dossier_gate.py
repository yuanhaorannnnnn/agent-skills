import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('dossier_gate', Path(__file__).parents[1] / 'scripts/dossier_gate.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class DossierGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'dossier.md').write_text('A sourced dossier')
        (self.root / 'source.md').write_text('Original record')
        self.manifest = self.root / 'manifest.json'
        self.catalog = self.root / 'catalog.json'
        self.data = dict(schema_version=1, id='lidar-weather', scope='simulation/lidar-weather', title='天气模型', aliases=['LiDAR 天气'], as_of='2026-10-20', entry='dossier.md', gaps=[], materials=[dict(id='M01', title='记录', kind='brief', path='dossier.md', sources=['S01'])], sources=[dict(id='S01', path=str(self.root / 'source.md'), locator='line 1', evidence='original', read_status='read', read_at='2026-10-20')])
        self.row = {k: self.data[k] for k in ('id', 'scope', 'title', 'aliases')}
        self.row['path'] = str(self.manifest)

    def run_gate(self, rows=None):
        self.manifest.write_text(json.dumps(self.data))
        self.catalog.write_text(json.dumps(dict(schema_version=1, dossiers=rows if rows is not None else [self.row])))
        before = {p: p.read_bytes() for p in self.root.iterdir()}
        result = gate.validate(self.manifest, self.catalog)
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.iterdir()})
        return result

    def test_valid_and_read_only(self):
        self.assertEqual(self.run_gate(), [])

    def test_duplicate_id(self):
        self.assertIn('duplicate dossier id', self.run_gate([self.row, copy.deepcopy(self.row)]))

    def test_normalized_alias_collision(self):
        other = dict(self.row, id='second', title='另一标题', aliases=['ＬＩＤＡＲ天气'])
        self.assertIn('scope/title/alias collision', self.run_gate([self.row, other]))

    def test_same_name_different_scope_allowed(self):
        other = dict(self.row, id='other', scope='other/project')
        self.assertEqual(self.run_gate([self.row, other]), [])

    def test_dangling_source(self):
        self.data['materials'][0]['sources'] = ['S99']
        self.assertIn('unresolved material sources', self.run_gate())

    def test_path_escape(self):
        self.data['entry'] = '../outside.md'
        self.assertIn('package path escapes root', self.run_gate())

    def test_missing_requires_gap(self):
        self.data['sources'][0]['read_status'] = 'missing'
        self.assertIn('missing source requires gap record', self.run_gate())
        self.data['gaps'] = ['S01 original unavailable']
        self.assertEqual(self.run_gate(), [])

    def test_stale_catalog_pointer(self):
        row = dict(self.row, path=str(self.root / 'dossier.md'))
        self.assertIn('catalog path mismatch', self.run_gate([row]))


if __name__ == '__main__':
    unittest.main()
