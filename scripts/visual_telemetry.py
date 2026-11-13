#!/usr/bin/env python3
"""Record self-reported visual workflow observations; never an attestation."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import stat

DEFAULT = Path.home()/'.agents'/'visual-telemetry'/'events.jsonl'
MEDIA = ('page','ui','image','presentation','document','chart','map','video','mixed','other','unknown')
STEPS = ('reported_done','not_done','unknown','not_applicable')
DELIVERY = ('reported_match','reported_mismatch','unknown','not_applicable')
COVERAGE = ('reported_complete','partial','unknown','not_applicable')
FIELDS = {'medium': MEDIA, 'content_idea': STEPS, 'reference': STEPS,
          'inspection': STEPS, 'delivery': DELIVERY, 'coverage': COVERAGE}


def valid(event):
    if not isinstance(event, dict) or set(event) != {'schema_version','timestamp',*FIELDS}:
        return False
    if type(event['schema_version']) is not int or event['schema_version'] != 1:
        return False
    try:
        if datetime.fromisoformat(event['timestamp']).utcoffset() is None: return False
    except (TypeError, ValueError):
        return False
    return all(isinstance(event[k], str) and event[k] in choices for k,choices in FIELDS.items())


def append(path, event):
    if not valid(event): raise ValueError('invalid event')
    path = Path(path)
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    parent = path.parent.lstat()
    if not stat.S_ISDIR(parent.st_mode) or parent.st_uid != os.getuid() or parent.st_mode & 0o077:
        raise PermissionError('telemetry directory must be private and owned by current user')
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise PermissionError('telemetry file must be private and owned by current user')
        fcntl.flock(fd, fcntl.LOCK_EX)
        data = (json.dumps(event, separators=(',',':'))+'\n').encode()
        if os.write(fd, data) != len(data): raise OSError('incomplete telemetry write')
    finally:
        os.close(fd)


def report(path):
    result = {'records': 0, 'invalid_lines': 0, 'counts': {k:{} for k in FIELDS},
              'limits': 'Self-reported records only; missing records are not failures or a total task count.'}
    counters = {k: Counter() for k in FIELDS}
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as stream:
            info = os.fstat(stream.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
                raise PermissionError('telemetry file must be private and owned by current user')
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            for line in stream:
                try: event = json.loads(line)
                except (ValueError, UnicodeError): result['invalid_lines'] += 1; continue
                if not valid(event): result['invalid_lines'] += 1; continue
                result['records'] += 1
                for k in FIELDS: counters[k][event[k]] += 1
    except FileNotFoundError:
        pass
    result['counts'] = {k:dict(v) for k,v in counters.items()}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--path', type=Path, default=DEFAULT)
    sub = p.add_subparsers(dest='command', required=True)
    record = sub.add_parser('record')
    for name,choices in FIELDS.items():
        record.add_argument('--'+name.replace('_','-'), choices=choices, default='unknown')
    sub.add_parser('report')
    a = p.parse_args()
    if a.command == 'report': print(json.dumps(report(a.path), indent=2)); return
    event = {'schema_version':1, 'timestamp':datetime.now(timezone.utc).isoformat(),
             **{k:getattr(a,k) for k in FIELDS}}
    append(a.path,event)


if __name__ == '__main__': main()
