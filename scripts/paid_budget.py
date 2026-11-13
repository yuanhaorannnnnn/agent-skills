#!/usr/bin/env python3
"""Manual, pre-call reservations for paid APIs; does not intercept network calls.

No release/refund action exists: errors and uncertain requests keep reservations.
Cycle observation is a baseline; callers must not fold existing reservations into
observed_spend without reconciling the baseline, or they will be double-counted.
"""
import argparse
import datetime as dt
from decimal import Decimal, InvalidOperation
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from zoneinfo import ZoneInfo

DIRECTORY = Path('/home/yhr/.codex/paid-usage-guard')
ZONE = ZoneInfo('Asia/Shanghai')


class Denied(Exception):
    pass


def number(value, positive=False):
    if value is None or isinstance(value, (bool, float)):
        raise Denied('amounts require exact decimal strings or integers')
    try:
        result = Decimal(value)
        if not result.is_finite() or result < 0 or positive and result == 0:
            raise ValueError()
        if result.adjusted() > 12 or result.as_tuple().exponent < -12:
            raise ValueError()
        return result
    except (ValueError, TypeError, InvalidOperation):
        raise Denied('invalid nonnegative decimal amount') from None


def instant(value):
    if not isinstance(value, str):
        raise Denied('cycle timestamps are required')
    try:
        t = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        return t.replace(tzinfo=ZONE) if t.tzinfo is None else t.astimezone(ZONE)
    except ValueError:
        raise Denied('invalid cycle timestamp') from None


def load(path):
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (OSError, ValueError):
        raise Denied('missing or corrupt ' + path.name) from None


def atomic(path, value):
    fd, temp = tempfile.mkstemp(prefix='.budget-', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(value, out, ensure_ascii=False, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
        fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def validate_state(state):
    if state.get('schema_version') != 1 or not isinstance(state.get('reservations'), list):
        raise Denied('invalid budget ledger')
    ids = set()
    for row in state['reservations']:
        if not isinstance(row, dict) or not all(isinstance(row.get(k), str) and row[k] for k in ('id', 'provider', 'unit', 'task_hash', 'operation', 'at', 'day', 'cycle_start', 'cycle_end', 'units')):
            raise Denied('invalid reservation record')
        if row['id'] in ids or not re.fullmatch('[a-f0-9]{64}', row['task_hash']):
            raise Denied('invalid reservation identity')
        ids.add(row['id'])
        number(row['units'], positive=True)
        at, start, end = instant(row['at']), instant(row['cycle_start']), instant(row['cycle_end'])
        if not start <= at < end or row['day'] != at.strftime('%Y-%m-%d'):
            raise Denied('invalid reservation time window')


def service(policy, provider, now):
    services = policy.get('services')
    if not isinstance(services, dict) or provider not in services or not isinstance(services[provider], dict):
        raise Denied('unknown provider; no approved budget')
    cfg = services[provider]
    if not isinstance(cfg.get('unit'), str) or not re.fullmatch('[A-Za-z][A-Za-z0-9_-]{0,31}', cfg['unit']):
        raise Denied('budget unit missing or invalid')
    limits = {k: number(cfg.get(k), positive=True) for k in ('daily_limit', 'task_limit', 'cycle_limit')}
    observed = number(cfg.get('observed_spend'))
    start, end = instant(cfg.get('cycle_start')), instant(cfg.get('cycle_end'))
    if not start <= now < end:
        raise Denied('budget cycle is not current; refresh account observation before spending')
    if observed > limits['cycle_limit']:
        raise Denied('observed spending already exceeds cycle budget')
    return cfg, limits, observed, start, end


def request(data):
    if not isinstance(data, dict) or set(data) != {'provider', 'task', 'operation', 'units'}:
        raise Denied('reserve requires only provider/task/operation/units')
    for field in ('provider', 'operation'):
        if not isinstance(data[field], str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.:-]{0,95}', data[field]):
            raise Denied('provider and operation must be short identifiers, not content')
    task = data['task']
    if not isinstance(task, str) or not task.strip() or len(task) > 256 or any(ord(c) < 32 for c in task):
        raise Denied('stable task/issue identifier is required')
    return number(data['units'], positive=True), hashlib.sha256(task.encode()).hexdigest()


def totals(rows, provider, now, start, end, task_hash=None):
    relevant = [r for r in rows if r['provider'] == provider]
    # Use actual reservation timestamps so a policy boundary change cannot hide spend.
    cycle = sum((number(r['units']) for r in relevant if start <= instant(r['at']) < end), Decimal(0))
    day = sum((number(r['units']) for r in relevant if r['day'] == now.strftime('%Y-%m-%d')), Decimal(0))
    task = sum((number(r['units']) for r in relevant if r['task_hash'] == task_hash), Decimal(0))
    return dict(cycle=cycle, day=day, task=task)


def reserve(data, directory=DIRECTORY, now=None):
    units, task_hash = request(data)
    now = (now or dt.datetime.now(ZONE)).astimezone(ZONE)
    if not directory.is_dir():
        raise Denied('guard directory not installed')
    fd = os.open(directory / 'budget.lock', os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        policy = load(directory / 'policy.json')
        cfg, limits, observed, start, end = service(policy, data['provider'], now)
        state = load(directory / 'budget-state.json')
        validate_state(state)
        if any(r['unit'] != cfg['unit'] for r in state['reservations'] if r['provider'] == data['provider']):
            raise Denied('provider unit changed; explicit ledger migration required')
        used = totals(state['reservations'], data['provider'], now, start, end, task_hash)
        for label, total, limit in [('task', used['task'], limits['task_limit']), ('day', used['day'], limits['daily_limit']), ('cycle', observed + used['cycle'], limits['cycle_limit'])]:
            if total + units > limit:
                raise Denied(label + ' budget exceeded; no reservation made')
        row = dict(id=f'{now.timestamp():.6f}-{os.getpid()}-{len(state["reservations"])}', provider=data['provider'],
                   unit=cfg['unit'], task_hash=task_hash, operation=data['operation'], units=str(units),
                   at=now.isoformat(), day=now.strftime('%Y-%m-%d'), cycle_start=start.isoformat(), cycle_end=end.isoformat())
        state['reservations'].append(row)
        atomic(directory / 'budget-state.json', state)
        return dict(reserved=True, reservation_id=row['id'], provider=row['provider'], operation=row['operation'],
                    units=row['units'], unit=row['unit'], cycle_remaining=str(limits['cycle_limit']-observed-used['cycle']-units))


def status(directory=DIRECTORY, now=None):
    """Read-only: atomic ledger reads, no lock file creation or other writes."""
    now = (now or dt.datetime.now(ZONE)).astimezone(ZONE)
    policy, state = load(directory / 'policy.json'), load(directory / 'budget-state.json')
    validate_state(state)
    if not isinstance(policy.get('services'), dict):
        raise Denied('services policy missing')
    result = {}
    for name in policy['services']:
        try:
            cfg, limits, observed, start, end = service(policy, name, now)
            used = totals(state['reservations'], name, now, start, end)
            if any(r['unit'] != cfg['unit'] for r in state['reservations'] if r['provider'] == name):
                raise Denied('provider unit changed')
            result[name] = dict(status='current', unit=cfg['unit'], observed_spend=str(observed),
                                reserved_cycle=str(used['cycle']), reserved_day=str(used['day']),
                                cycle_limit=str(limits['cycle_limit']), cycle_remaining=str(limits['cycle_limit']-observed-used['cycle']))
        except Denied as exc:
            result[name] = dict(status='blocked', reason=str(exc))
    return {'intercepts_network': False, 'providers': result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['reserve', 'status'])
    parser.add_argument('--input', type=Path, help='JSON file; required only for reserve')
    args = parser.parse_args()
    try:
        if args.action == 'reserve':
            if args.input is None:
                raise Denied('--input JSON file required')
            result = reserve(load(args.input))
        else:
            if args.input is not None:
                raise Denied('status does not accept an input file')
            result = status()
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except (Denied, OSError) as exc:
        print(json.dumps({'reserved': False, 'error': str(exc)}, ensure_ascii=False))
        return 78


if __name__ == '__main__':
    raise SystemExit(main())
