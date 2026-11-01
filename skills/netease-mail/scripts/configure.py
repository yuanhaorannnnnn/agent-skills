#!/usr/bin/env python3
"""Interactive local-only account setup. Run in a private host terminal."""
import getpass
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import keyring

SERVICE = 'codex-netease-mail'

def main():
    if not sys.stdin.isatty():
        raise SystemExit('Run interactively in a private local terminal; never pipe or provide credentials through an agent.')
    address = input('NetEase email address: ').strip()
    if not re.fullmatch(r'[^\s@<>]+@(163\.com|126\.com|yeah\.net)', address, re.I):
        raise SystemExit('Only 163.com, 126.com and yeah.net personal addresses are supported.')
    secret = getpass.getpass('NetEase client authorization code (not your account password): ')
    if not secret: raise SystemExit('No authorization code entered; nothing saved.')
    try:
        keyring.set_password(SERVICE, address, secret)
    except Exception:
        raise SystemExit('System keyring is unavailable or locked; nothing written to account config.') from None
    finally:
        secret = None
    directory = Path.home() / '.config/netease-mail'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix='.account-', dir=directory)
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump({'email': address}, f)
        os.replace(tmp, directory / 'account.json')
    finally:
        if os.path.exists(tmp): os.unlink(tmp)
    print('Account saved. Authorization code stored in system keyring. Connection is not yet verified.')

if __name__ == '__main__': main()
