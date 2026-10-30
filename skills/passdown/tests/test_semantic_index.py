import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from unittest import mock

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import semantic_index as semantic


class FakeModel:
    def encode(self, texts, **kwargs):
        result = []
        for text in texts:
            v = np.zeros(384, dtype='f4')
            v[0 if 'apple' in text else 1] = 1
            result.append(v)
        return np.asarray(result)


def session(path, text):
    path.write_text(json.dumps({'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':text}]}})+'\n')


def test_sync_scope_delete_and_source_read_only(tmp_path):
    state = tmp_path / 'state'
    a, b = tmp_path / 'a.jsonl', tmp_path / 'b.jsonl'
    session(a, 'apple first')
    session(b, 'banana second')
    original = a.read_bytes()
    def req(paths):
        return {'focus':'apple', 'candidates':[{'path':str(p),'runtime':'codex','mtime':1} for p in paths]}
    with mock.patch.object(semantic, 'STATE', state), mock.patch.object(semantic, 'load_model', return_value=(FakeModel(), 'v1')):
        first = semantic.run(req([a,b]))
        assert first['fresh_sessions'] == 2
        assert first['matches'][0]['path'] == str(a)
        assert a.read_bytes() == original
        assert state.stat().st_mode & 0o077 == 0
        # A changed source gets new embeddings; out-of-scope records cannot rank.
        session(a, 'banana modified')
        narrowed = semantic.run(req([a]))
        assert [x['path'] for x in narrowed['matches']] == [str(a)]
        assert narrowed['matches'][0]['score'] == 0
        b.unlink()
        semantic.run(req([a]))
        with sqlite3.connect(state / 'index.sqlite3') as db:
            assert db.execute('select count(*) from docs where path=?',(str(b),)).fetchone()[0] == 0
            assert b'banana modified' not in (state / 'index.sqlite3').read_bytes()


def test_source_change_during_embedding_is_not_published(tmp_path):
    state = tmp_path / 'state'
    path = tmp_path / 'session.jsonl'
    session(path, 'apple original')
    class ChangingModel(FakeModel):
        def encode(self, texts, **kwargs):
            if texts and texts[0].startswith('passage:'):
                session(path, 'banana changed during encode')
            return super().encode(texts, **kwargs)
    req = {'focus':'apple','candidates':[{'path':str(path),'runtime':'codex','mtime':1}]}
    with mock.patch.object(semantic, 'STATE', state), mock.patch.object(semantic, 'load_model', return_value=(ChangingModel(), 'v1')):
        result = semantic.run(req)
        assert result['failed'] == 1
        assert result['matches'] == []
        with sqlite3.connect(state / 'index.sqlite3') as db:
            assert db.execute('select count(*) from docs').fetchone()[0] == 0


def test_automation_prompt_is_not_embedded(tmp_path):
    path = tmp_path / 'session.jsonl'
    prompt = ('Automation: 模型巡检\nAutomation ID: automation-7\nAutomation memory: /memory\n'
              'Last run: never\n\n只在说明里的语义检索文本')
    rows = [
        {'type':'response_item','payload':{'role':'user','content':[{'type':'input_text','text':prompt}]}},
        {'type':'response_item','payload':{'role':'assistant','content':[{'type':'output_text','text':'apple 实际运行结果'}]}},
    ]
    path.write_text(''.join(json.dumps(row, ensure_ascii=False)+'\n' for row in rows))
    encoded = []
    class RecordingModel(FakeModel):
        def encode(self, texts, **kwargs):
            encoded.extend(texts)
            return super().encode(texts, **kwargs)
    req = {'focus':'apple','candidates':[{'path':str(path),'runtime':'codex','mtime':1}]}
    with mock.patch.object(semantic, 'STATE', tmp_path / 'state'), mock.patch.object(semantic, 'load_model', return_value=(RecordingModel(), 'v1')):
        result = semantic.run(req)
    assert result['matches'][0]['ordinal'] == 1
    assert all('只在说明里' not in text for text in encoded)


def test_repeated_failures_do_not_starve_later_sessions(tmp_path):
    paths = []
    for i in range(5):
        path = tmp_path / f'{i}.jsonl'
        session(path, 'BAD' if i < 4 else 'apple good')
        paths.append(path)
    class SometimesFails(FakeModel):
        def encode(self, texts, **kwargs):
            if texts and texts[0].startswith('passage:') and 'BAD' in texts[0]:
                raise RuntimeError('cannot encode this source')
            return super().encode(texts, **kwargs)
    req = {'focus':'apple','candidates':[{'path':str(p),'runtime':'codex','mtime':10-i} for i,p in enumerate(paths)]}
    before = [p.read_bytes() for p in paths]
    with mock.patch.object(semantic, 'STATE', tmp_path / 'state'), mock.patch.object(semantic, 'load_model', return_value=(SometimesFails(), 'v1')):
        first = semantic.run(req)
        second = semantic.run(req)
    assert first['failed'] == 4 and first['fresh_sessions'] == 0
    assert second['fresh_sessions'] == 1
    assert second['matches'][0]['path'] == str(paths[4])
    assert [p.read_bytes() for p in paths] == before


def test_semantic_offset_preserves_middle_passage_under_budget(tmp_path):
    import extract_handoff as ex
    path = tmp_path / 'long.jsonl'
    body = 'a' * 13800 + ' apple EVIDENCE_IN_MIDDLE ' + 'b' * 13800
    session(path, body)
    req = {'focus':'apple','candidates':[{'path':str(path),'runtime':'codex','mtime':1}]}
    with mock.patch.object(semantic, 'STATE', tmp_path / 'state'), mock.patch.object(semantic, 'load_model', return_value=(FakeModel(), 'v1')):
        hit = semantic.run(req)['matches'][0]
    assert hit['ordinal'] == 0 and 13200 <= hit['offset'] <= 13800
    assert hit['source_stamp'] == semantic.stamp(path)
    turns, stats = ex.budget_turns([{'role':'user','text':body,'semantic_hit':True,'semantic_offset':hit['offset']}], 'apple', 8000)
    assert stats['budget_applied']
    assert 'EVIDENCE_IN_MIDDLE' in turns[0]['text']
    assert turns[0]['text_truncated']
    assert sum(ex.estimate_tokens(t['text']) for t in turns) <= 8000


def test_legacy_index_migrates_without_deleting_source(tmp_path):
    state = tmp_path / 'state'
    state.mkdir()
    path = tmp_path / 'legacy.jsonl'
    session(path, 'apple legacy')
    old = np.zeros(384, dtype='<f4').tobytes()
    with sqlite3.connect(state / 'index.sqlite3') as db:
        db.execute('CREATE TABLE docs (path TEXT PRIMARY KEY, runtime TEXT NOT NULL, stamp TEXT NOT NULL, signature TEXT NOT NULL, truncated INTEGER NOT NULL)')
        db.execute('CREATE TABLE chunks (path TEXT NOT NULL REFERENCES docs(path) ON DELETE CASCADE, ordinal INTEGER NOT NULL, vector BLOB NOT NULL)')
        db.execute('INSERT INTO docs VALUES (?,?,?,?,?)', (str(path),'codex',semantic.stamp(path),'old-signature',0))
        db.execute('INSERT INTO chunks VALUES (?,?,?)', (str(path),0,old))
    original = path.read_bytes()
    req = {'focus':'apple','candidates':[{'path':str(path),'runtime':'codex','mtime':1}]}
    with mock.patch.object(semantic, 'STATE', state), mock.patch.object(semantic, 'load_model', return_value=(FakeModel(), 'new-signature')):
        result = semantic.run(req)
    assert result['matches'][0]['offset'] == 0
    assert path.read_bytes() == original
    with sqlite3.connect(state / 'index.sqlite3') as db:
        assert db.execute('SELECT offset FROM chunks').fetchone()[0] == 0
        assert db.execute('SELECT signature FROM docs').fetchone()[0] == 'new-signature'


def test_tiny_budget_marks_partially_retained_semantic_passage():
    import extract_handoff as ex
    text = 'a' * 1200 + '苹果' * 300 + 'b' * 1200
    turns, stats = ex.budget_turns([{'role':'user','text':text,'semantic_hit':True,'semantic_offset':1200}], '苹果', 20)
    assert stats['budget_applied']
    assert turns[0]['semantic_passage_truncated'] is True
    assert sum(ex.estimate_tokens(t['text']) for t in turns) <= 20
