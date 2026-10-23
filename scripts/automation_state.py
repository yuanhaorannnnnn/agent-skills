"""Atomic automation facts, business/notification results and send guard. No network calls."""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from contextlib import contextmanager


def body_hash(body):
    # MIME-decoded HTML text, UTF-8, newline-normalized; no other HTML rewriting.
    return hashlib.sha256(body.replace('\r\n', '\n').replace('\r', '\n').encode('utf-8')).hexdigest()


@contextmanager
def locked(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / '.reliability.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


def atomic(path, value):
    fd, temporary = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    with os.fdopen(fd, 'w') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def transition(directory, action, data):
    directory = Path(directory)
    with locked(directory):
        path = directory / 'reliability-state.json'
        state = json.loads(path.read_text()) if path.exists() else {'items': {}, 'issues': {}, 'months': {}}
        key = data['key']
        if action == 'run':
            assert set(data) <= {'key', 'business_status', 'notification_status', 'gate', 'artifact', 'updated_at'}
            assert data['business_status'] in ('running', 'completed', 'no_op', 'partial', 'blocked', 'failed')
            assert data['notification_status'] in ('not_needed', 'pending', 'reported_in_chat', 'confirmed', 'unverified', 'failed')
            result = dict(data)
            state.setdefault('runs', {})[key] = result
        elif action == 'item':
            assert data['status'] in ('pending', 'failed', 'completed')
            assert set(data) <= {'key', 'status', 'source_hash', 'query', 'stage'}
            previous = state['items'].get(key)
            if previous and previous['status'] == 'completed':
                if previous.get('source_hash') == data.get('source_hash'):
                    return previous
                state.setdefault('item_history', {}).setdefault(key, []).append(previous)
            state['items'][key] = data
            result = data
        elif action == 'month':
            # First registration wins; the monthly runner's printed directory is then attached.
            created = key not in state['months']
            result = state['months'].setdefault(key, {'status': 'reserved', 'run_dir': None})
            if 'run_dir' in data:
                assert result['run_dir'] in (None, data['run_dir'])
                result['run_dir'] = data['run_dir']
            if 'status' in data:
                assert data['status'] in ('reserved', 'partial', 'completed')
                if result['status'] != 'completed':
                    result['status'] = data['status']
        elif action == 'prepare':
            issue = state['issues'].get(key)
            if issue:
                return issue
            assert set(data) == {'key', 'body', 'subject', 'recipient', 'date', 'manifest'}
            token = hashlib.sha256(key.encode()).hexdigest()
            artifact = directory / ('prepared-' + token + '.html')
            # Save immutable artifact before registering ready-to-send issue.
            if artifact.exists():
                assert body_hash(artifact.read_text()) == body_hash(data['body']), 'orphan artifact differs: manual recovery required'
            else:
                with artifact.open('x', encoding='utf-8', newline='') as stream:
                    stream.write(data['body'])
                    stream.flush()
                    os.fsync(stream.fileno())
            result = {'status': 'prepared', 'artifact': str(artifact), 'body_sha256': body_hash(data['body']),
                      'subject': data['subject'], 'recipient': data['recipient'], 'date': data['date'],
                      'manifest': data['manifest']}
            state['issues'][key] = result
        elif action == 'posting':
            result = state['issues'][key]
            assert result['status'] == 'prepared', 'sent/uncertain issue cannot send again'
            assert body_hash(Path(result['artifact']).read_text()) == result['body_sha256']
            result['status'] = 'posting'
        elif action == 'receipt':
            result = state['issues'][key]
            assert result['status'] in ('posting', 'maybe_sent', 'sent')
            assert isinstance(data.get('message_id'), str) and data['message_id'].strip()
            if result['status'] == 'sent':
                assert result['message_id'] == data['message_id']
            result.update(status='sent', message_id=data['message_id'])
        elif action == 'recover':
            result = state['issues'][key]
            if result['status'] == 'posting':
                result['status'] = 'maybe_sent'
            # Actual Sent evidence only: decoded body plus exact routing metadata and message id.
            matches = [m for m in data.get('sent', []) if isinstance(m.get('message_id'), str) and m['message_id'].strip() and
                       all(m.get(k) == result[k] for k in ('recipient', 'subject', 'date')) and
                       'body' in m and body_hash(m['body']) == result['body_sha256']]
            if result['status'] == 'maybe_sent' and len(matches) == 1:
                result.update(status='sent', message_id=matches[0]['message_id'])
        elif action == 'facts':
            assert set(data) <= {'key', 'revision', 'record_date', 'conclusion', 'gate', 'status'}
            assert data.get('status') == 'completed', 'failed attempts cannot replace successful revision'
            state.setdefault('facts', {})[key] = data
            result = data
        else:
            raise ValueError('unknown action')
        atomic(path, state)
        return dict(result, created=created) if action == 'month' else result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('action', choices=['item', 'month', 'prepare', 'posting', 'receipt', 'recover', 'facts', 'run'])
    parser.add_argument('--input', type=Path, required=True, help='JSON input, never shell-interpolated HTML')
    args = parser.parse_args()
    allowed = (Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')) / 'automations').resolve()
    assert args.directory.resolve().parent == allowed, 'CLI writes only one automation directory'
    print(json.dumps(transition(args.directory, args.action, json.loads(args.input.read_text())), ensure_ascii=False))
