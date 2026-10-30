#!/usr/bin/env python3
"""Private, disposable candidate index for filtered session turns.

The caller supplies the currently permitted source files; this process never
searches outside that list or writes to source sessions.
"""
from __future__ import annotations
import bisect
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sqlite3
import sys

MODEL = Path(os.environ.get('PASSDOWN_EMBEDDING_MODEL_PATH', '/media/yhr/2T/files/wiki/.research/wiki-semantic/model'))
STATE = Path(os.environ.get('PASSDOWN_SEMANTIC_STATE_DIR', str(Path.home() / '.agents/passdown-semantic')))
MAX_CHUNKS = 160
MAX_NEW_SESSIONS = 4
FORMAT = 'passdown-e5-v4-chunk-offset-600-160'


def load_model():
    os.environ.update(USE_TF='0', TRANSFORMERS_OFFLINE='1', HF_HUB_OFFLINE='1', TOKENIZERS_PARALLELISM='false')
    import torch
    from sentence_transformers import SentenceTransformer
    torch.set_num_threads(4)
    digest = hashlib.sha256(FORMAT.encode())
    for name in ('model.safetensors', 'config.json', 'modules.json', 'tokenizer.json', 'tokenizer_config.json', 'sentencepiece.bpe.model', 'special_tokens_map.json', 'sentence_bert_config.json', '1_Pooling/config.json'):
        with (MODEL / name).open('rb') as f:
            for block in iter(lambda: f.read(1024 * 1024), b''):
                digest.update(block)
    for package in ('torch', 'transformers', 'sentence-transformers'):
        digest.update((package + ':' + importlib.metadata.version(package)).encode())
    return SentenceTransformer(str(MODEL), local_files_only=True, device='cpu'), digest.hexdigest()


def stamp(path):
    s = path.stat()
    return f'{s.st_dev}:{s.st_ino}:{s.st_size}:{s.st_mtime_ns}'


def run(request):
    import numpy as np
    import extract_handoff as ex
    model, signature = load_model()
    STATE.mkdir(mode=0o700, parents=True, exist_ok=True)
    STATE.chmod(0o700)
    index = STATE / 'index.sqlite3'
    db = sqlite3.connect(index, timeout=3)
    index.chmod(0o600)
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('CREATE TABLE IF NOT EXISTS docs (path TEXT PRIMARY KEY, runtime TEXT NOT NULL, stamp TEXT NOT NULL, signature TEXT NOT NULL, truncated INTEGER NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS chunks (path TEXT NOT NULL REFERENCES docs(path) ON DELETE CASCADE, ordinal INTEGER NOT NULL, vector BLOB NOT NULL, offset INTEGER NOT NULL DEFAULT -1)')
    db.execute('CREATE TABLE IF NOT EXISTS progress (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    if 'offset' not in {row[1] for row in db.execute('PRAGMA table_info(chunks)')}:
        try:
            db.execute('ALTER TABLE chunks ADD COLUMN offset INTEGER NOT NULL DEFAULT -1')
        except sqlite3.OperationalError:
            if 'offset' not in {row[1] for row in db.execute('PRAGMA table_info(chunks)')}:
                raise
    db.commit()
    allowed = {}
    for c in request['candidates']:
        path = Path(c['path'])
        try:
            allowed[str(path)] = (c, stamp(path))
        except OSError:
            continue
    parsers = {'codex': ex.parse_codex, 'pi': ex.parse_pi, 'claude': ex.parse_claude, 'dsh': ex.parse_dsh}
    # Remove records whose source no longer exists; other scopes remain intact.
    with db:
        for (old_path,) in db.execute('SELECT path FROM docs').fetchall():
            if not Path(old_path).is_file():
                db.execute('DELETE FROM docs WHERE path=?', (old_path,))
    previous = {p: (r, s, sig, trunc) for p, r, s, sig, trunc in db.execute('SELECT path,runtime,stamp,signature,truncated FROM docs')}
    fresh = {p for p, (c, s) in allowed.items() if previous.get(p, (None, None, None, None))[:3] == (c['runtime'], s, signature)}
    # Persist the last attempted path so repeatedly failing files cannot starve others.
    pending = sorted(p for p in allowed if p not in fresh)
    row = db.execute("SELECT value FROM progress WHERE key='cursor'").fetchone()
    start = bisect.bisect_right(pending, row[0]) if row else 0
    pending = pending[start:] + pending[:start]
    failed = 0
    for path in pending[:MAX_NEW_SESSIONS]:
        with db:
            db.execute("INSERT OR REPLACE INTO progress VALUES ('cursor', ?)", (path,))
        c, before = allowed[path]
        try:
            turns = parsers[c['runtime']](Path(path))['turns']
            chunks = [(i, j, t['text'][j:j+600]) for i, t in enumerate(turns)
                      if not ex.automation_context(t)
                      for j in range(0, len(t['text']), 600) if t['text'][j:j+600].strip()]
            truncated = len(chunks) > MAX_CHUNKS
            # Spread sampling across the complete conversation, including its end.
            if truncated:
                indexes = np.linspace(0, len(chunks)-1, MAX_CHUNKS, dtype=int)
                chunks = [chunks[i] for i in indexes]
            vectors = model.encode(['passage: '+v for _, _, v in chunks], batch_size=24, normalize_embeddings=True, show_progress_bar=False) if chunks else []
            if stamp(Path(path)) != before or len(vectors) != len(chunks):
                raise RuntimeError('source changed during indexing')
            with db:
                db.execute('DELETE FROM docs WHERE path=?', (path,))
                db.execute('INSERT INTO docs VALUES (?,?,?,?,?)', (path,c['runtime'],before,signature,int(truncated)))
                for (ordinal, offset, _), vector in zip(chunks, vectors):
                    vec = np.asarray(vector, dtype='<f4')
                    if vec.shape != (384,) or not np.isfinite(vec).all():
                        raise RuntimeError('invalid embedding')
                    db.execute('INSERT INTO chunks(path,ordinal,offset,vector) VALUES (?,?,?,?)', (path,ordinal,offset,vec.tobytes()))
            fresh.add(path)
        except (OSError, ValueError, RuntimeError, sqlite3.Error):
            failed += 1
    query = np.asarray(model.encode(['query: '+request['focus']], normalize_embeddings=True, show_progress_bar=False)[0], dtype='<f4')
    scores = {}
    validated = set()
    # Restrict before ranking: no out-of-scope or stale vectors may participate.
    for path in fresh:
        try:
            if stamp(Path(path)) != allowed[path][1]:
                continue
            validated.add(path)
            rows = db.execute('SELECT ordinal,offset,vector FROM chunks WHERE path=?', (path,)).fetchall()
            if not rows:
                continue
            matrix = np.vstack([np.frombuffer(r[2], dtype='<f4') for r in rows])
            values = matrix @ query
            best = int(np.argmax(values))
            scores[path] = (float(values[best]), rows[best][0], rows[best][1])
        except (OSError, ValueError):
            failed += 1
    fresh = validated
    matches = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)[:3]
    truncated_count = sum(bool(db.execute('SELECT truncated FROM docs WHERE path=?', (p,)).fetchone()[0]) for p in fresh)
    db.close()
    return {'matches': [{'path': p, 'score': round(v[0], 6), 'ordinal': v[1], 'offset': v[2], 'source_stamp': allowed[p][1]} for p,v in matches],
            'scope_sessions': len(allowed), 'fresh_sessions': len(fresh), 'failed': failed,
            'sampled_sessions_in_index': truncated_count, 'sampling_limit_per_session': MAX_CHUNKS}


if __name__ == '__main__':
    try:
        print(json.dumps(run(json.load(sys.stdin)), ensure_ascii=False))
    except Exception as exc:
        print(json.dumps({'error': type(exc).__name__}), file=sys.stderr)
        sys.exit(1)
