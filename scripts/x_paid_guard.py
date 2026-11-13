#!/usr/bin/env python3
"""Bound X reads before execution; reservations survive failures and concurrent calls.

This protects this CLI entry point, not the provider account or direct HTTP clients.
The original xurl binary must be installed at REAL_BINARY by the operator.
"""
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, urlsplit
from zoneinfo import ZoneInfo

REAL_BINARY = '/home/yhr/.local/libexec/xurl-real'
DIRECTORY = Path('/home/yhr/.codex/paid-usage-guard')
SHANGHAI = ZoneInfo('Asia/Shanghai')


class Denied(Exception):
    pass


def money(value):
    try:
        n = Decimal(str(value)) * 1_000_000
        if not n.is_finite() or n <= 0 or n != n.to_integral_value():
            raise ValueError()
        return int(n)
    except (InvalidOperation, ValueError):
        raise Denied('invalid monetary policy') from None


def plan(args, max_results=20):
    """Parse conservatively; an unclassified operation never reaches xurl."""
    if args in (['--help'], ['-h'], ['help'], ['--version'], ['version']):
        return {'kind': 'local', 'cost': 0}
    # Auth is a separate xurl command tree; never a paid API transport.
    auth_args = list(args)
    while len(auth_args) >= 2 and auth_args[0] in ('--app', '--auth', '-u', '--username'):
        auth_args = auth_args[2:]
    if len(auth_args) >= 2 and auth_args[0] == 'auth' and auth_args[1] in ('status', 'default', 'oauth1', 'oauth2', 'apps'):
        return {'kind': 'local', 'cost': 0}
    i = 0
    positional = []
    while i < len(args):
        a = args[i]
        if a in ('--app', '--auth', '-u', '--username', '-X', '--method'):
            if i + 1 >= len(args):
                raise Denied('missing flag value')
            if a in ('-X', '--method') and args[i + 1] != 'GET':
                raise Denied('write operations require a separately approved budget')
            i += 2
        elif any(a.startswith(k + '=') for k in ('--app', '--auth', '--username')):
            if not a.split('=', 1)[1]:
                raise Denied('missing flag value')
            i += 1
        elif a.startswith('-'):
            raise Denied('unsupported flag; headers, data, tracing and streaming are blocked')
        else:
            positional.append(a)
            i += 1
    if positional and positional[0] == 'auth':
        # xurl auth manages credentials but does not read billable resources.
        # Restrict to known auth verbs; leave credential handling to xurl.
        if len(positional) >= 2 and positional[1] in ('status', 'default', 'oauth1', 'oauth2', 'apps'):
            return {'kind': 'local', 'cost': 0}
        raise Denied('unsupported auth command')
    if positional and positional[0] == 'mcp':
        raise Denied('unmetered MCP bridge blocked; use bounded raw GET through xurl')
    if len(positional) != 1:
        raise Denied('use a single bounded raw GET endpoint')
    target = positional[0]
    if target == 'whoami':
        return {'kind': 'user', 'cost': 10000}
    u = urlsplit(target)
    if u.scheme and (u.scheme != 'https' or u.netloc not in ('api.x.com', 'api.twitter.com')):
        raise Denied('unsupported API origin')
    if not u.scheme and (not target.startswith('/') or u.netloc):
        raise Denied('use an absolute API path')
    if u.fragment or '%' in u.path or '//' in u.path:
        raise Denied('ambiguous API path')
    q = parse_qs(u.query, keep_blank_values=True)
    if any(len(values) != 1 for values in q.values()):
        raise Denied('duplicate query parameters')
    if 'expansions' in q:
        raise Denied('expansions blocked: additional returned resources are separately billable')
    path = u.path
    fields = {'tweet.fields', 'post.fields', 'user.fields'}
    if path == '/2/usage/credits':
        if q:
            raise Denied('unsupported credits query')
        return {'kind': 'credits', 'cost': 0}
    if path == '/2/tweets/search/all':
        raise Denied('full-archive search disabled; preserve unresolved evidence instead')
    kind, cost, allowed = None, None, set()
    if re.fullmatch(r'/2/tweets/\d+', path):
        kind, cost, allowed = 'post', 5000, fields
    elif path == '/2/tweets':
        ids = q.get('ids', [''])[0].split(',')
        if not 1 <= len(ids) <= max_results or any(not x.isdigit() for x in ids):
            raise Denied('ids must contain 1–20 numeric post IDs')
        kind, cost, allowed = 'posts', len(ids) * 5000, fields | {'ids'}
    elif re.fullmatch(r'/2/users/(me|\d+|by/username/[A-Za-z0-9_]+)', path):
        kind, cost, allowed = 'user', 10000, {'user.fields'}
    elif re.fullmatch(r'/2/users/\d+/(tweets|liked_tweets|bookmarks|mentions)', path) or path == '/2/tweets/search/recent':
        try:
            count = int(q['max_results'][0])
        except (KeyError, ValueError):
            raise Denied('explicit max_results is required') from None
        if not 1 <= count <= max_results:
            raise Denied(f'max_results must not exceed {max_results}')
        kind, cost = 'post-page', count * 5000
        allowed = fields | {'max_results', 'pagination_token', 'next_token', 'start_time', 'end_time', 'since_id', 'until_id', 'exclude', 'query', 'sort_order'}
    else:
        raise Denied('unknown endpoint or shortcut: no verified upper cost bound')
    if set(q) - allowed:
        raise Denied('unsupported query parameters')
    return {'kind': kind, 'cost': cost}


def read_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        raise Denied(f'missing or corrupt guard file: {path.name}') from None


def atomic(path, value):
    fd, tmp = tempfile.mkstemp(prefix='.guard-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, ensure_ascii=False)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def validate_state(state):
    if not isinstance(state, dict) or state.get('schema_version') != 1 or not isinstance(state.get('reservations'), list):
        raise Denied('invalid budget state')
    if state.get('blocked') is not None and (not isinstance(state['blocked'], dict) or state['blocked'].get('status') not in (401, 402, 403)):
        raise Denied('invalid circuit-breaker state')
    ids = set()
    for r in state['reservations']:
        if not isinstance(r, dict) or not all(isinstance(r.get(k), str) and r[k] for k in ('id', 'day', 'month', 'task', 'kind', 'status')):
            raise Denied('invalid reservation state')
        if type(r.get('cost')) is not int or r['cost'] < 0 or r['id'] in ids:
            raise Denied('invalid reservation cost or identity')
        try:
            date = dt.date.fromisoformat(r['day'])
            if date.strftime('%Y-%m') != r['month']:
                raise ValueError()
        except ValueError:
            raise Denied('invalid reservation date') from None
        ids.add(r['id'])


def reserve(args, directory=DIRECTORY, now=None, task=None):
    now = (now or dt.datetime.now(SHANGHAI)).astimezone(SHANGHAI)
    day, month = now.strftime('%Y-%m-%d'), now.strftime('%Y-%m')
    task = task or 'daily-fallback:' + day
    if not directory.is_dir():
        raise Denied('guard directory missing; installation required')
    lockfd = os.open(directory / 'x.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(lockfd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        policy = read_json(directory / 'policy.json')
        x = policy.get('x') if isinstance(policy, dict) else None
        if not isinstance(x, dict) or type(x.get('max_results')) is not int or not 1 <= x['max_results'] <= 20:
            raise Denied('invalid X guard policy')
        limits = {k: money(x.get(k)) for k in ('task_limit_usd', 'daily_limit_usd', 'monthly_limit_usd')}
        request = plan(args, x['max_results'])
        state = read_json(directory / 'x-state.json')
        validate_state(state)
        if request['cost'] == 0:
            return request, None
        if state.get('blocked') is not None:
            raise Denied('account circuit open after auth/credit failure; inspect free credits/auth before explicit reset')
        rows = state['reservations']
        for limit, predicate in (
            ('task_limit_usd', lambda r: r['task'] == task),
            ('daily_limit_usd', lambda r: r['day'] == day),
            ('monthly_limit_usd', lambda r: r['month'] == month),
        ):
            if sum(r['cost'] for r in rows if predicate(r)) + request['cost'] > limits[limit]:
                raise Denied('budget exhausted: ' + limit + '; no network request made')
        record = dict(id=f'{now.timestamp():.6f}-{os.getpid()}-{len(rows)}', day=day, month=month, task=task,
                      kind=request['kind'], cost=request['cost'], status='reserved')
        rows.append(record)
        atomic(directory / 'x-state.json', state)
        return request, record


def finish(directory, record, status, stdout, stderr):
    # Save each response before releasing it to caller. Failed/uncertain charges stay reserved.
    cp = directory / 'checkpoints'
    cp.mkdir(mode=0o700, exist_ok=True)
    os.chmod(cp, 0o700)
    atomic(cp / (record['id'] + '.json'), {'id': record['id'], 'kind': record['kind'], 'cost': record['cost'],
                                        'status': status, 'stdout': stdout, 'stderr': stderr})
    fd = os.open(directory / 'x.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = read_json(directory / 'x-state.json')
        validate_state(state)
        matches = [r for r in state['reservations'] if r['id'] == record['id']]
        if len(matches) != 1:
            raise Denied('reservation disappeared; checkpoint retained')
        matches[0]['status'] = status
        try:
            response = json.loads(stdout)
            failure = response.get('status') if isinstance(response, dict) else None
            if failure in (401, 402, 403):
                state['blocked'] = {'status': failure, 'reservation_id': record['id']}
        except ValueError:
            pass
        atomic(directory / 'x-state.json', state)


def run(args, directory=DIRECTORY, transport=subprocess.run, now=None, task=None):
    preliminary = plan(args)
    if preliminary['kind'] == 'local':
        request, record = preliminary, None
    else:
        request, record = reserve(args, directory, now, task)
    try:
        result = transport([REAL_BINARY, *args], capture_output=True, text=True, timeout=45)
        code, stdout, stderr = result.returncode, result.stdout, result.stderr
        status = 'returned' if code == 0 else 'failed_reserved'
    except subprocess.TimeoutExpired as exc:
        code, status = 124, 'timeout_reserved'
        stdout = exc.stdout or ''
        if isinstance(stdout, bytes):
            stdout = stdout.decode('utf-8', errors='replace')
        stderr = 'xurl timed out; reservation retained'
    except OSError:
        code, status, stdout, stderr = 126, 'execution_failed_reserved', '', 'xurl execution failed; reservation retained'
    if record:
        finish(directory, record, status, stdout, stderr)
    return code, stdout, stderr


def main():
    args = sys.argv[1:]
    # Help/version must remain usable during recovery, even with absent guard files.
    if args in (['--help'], ['-h'], ['help'], ['--version'], ['version']):
        return subprocess.call([REAL_BINARY, *args], timeout=45)
    task = os.environ.get('CODEX_THREAD_ID') or os.environ.get('CLAUDE_SESSION_ID')
    if task:
        task = hashlib.sha256(task.encode()).hexdigest()
    try:
        code, stdout, stderr = run(args, task=task)
        sys.stdout.write(stdout)
        sys.stderr.write(stderr)
        return code
    except (Denied, OSError) as exc:
        print('X paid guard: ' + str(exc), file=sys.stderr)
        return 78


if __name__ == '__main__':
    sys.exit(main())
