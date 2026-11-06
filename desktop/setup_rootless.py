#!/usr/bin/env python3
"""Allocate unused subordinate IDs for a normal Arch user; never stop containers."""
import argparse
import fcntl
import grp
import os
from pathlib import Path
import pwd
import subprocess

COUNT = 65536


def read_ranges(path):
    result = []
    for line in path.read_text().splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        owner, start, count = line.split(':')
        start, count = int(start), int(count)
        if start < 0 or count < 1:
            raise ValueError(f'Invalid subordinate ID range in {path}')
        result.append((owner, start, count))
    return result


def available_range(used, minimum=100000, maximum=600100000):
    start = minimum
    for lower, count in sorted(used):
        if lower + count <= start:
            continue
        if start + COUNT <= lower:
            break
        start = lower + count
    if start + COUNT - 1 > maximum:
        raise ValueError('No free subordinate ID range is available')
    return f'{start}-{start + COUNT - 1}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('user')
    args = parser.parse_args()
    if os.geteuid() != 0:
        raise SystemExit('Run this preparation through sudo for your normal account.')
    account = pwd.getpwnam(args.user)
    if account.pw_uid == 0:
        raise SystemExit('Rootless setup requires a normal user, not root.')
    if os.environ.get('SUDO_UID') and int(os.environ['SUDO_UID']) != account.pw_uid:
        raise SystemExit('Prepare only the account that invoked sudo.')
    with open('/run/lock/nahj-subids.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for kind in ('subuid', 'subgid'):
            path = Path('/etc') / kind
            if not path.exists():
                path.touch(mode=0o644, exist_ok=False)
        tables = {kind: read_ranges(Path('/etc') / kind) for kind in ('subuid', 'subgid')}
        options = []
        used = [(start, count) for table in tables.values() for _, start, count in table]
        used += [(entry.pw_uid, 1) for entry in pwd.getpwall()]
        used += [(entry.gr_gid, 1) for entry in grp.getgrall()]
        chosen = available_range(used)
        for kind, table in tables.items():
            existing = [count for owner, _, count in table
                        if owner in (account.pw_name, str(account.pw_uid))]
            if existing and sum(existing) < COUNT:
                raise SystemExit(f'{kind}: existing ranges are too small; ask the system administrator to review them. No ranges were changed.')
            if not existing:
                options += ['--add-' + kind + 's', chosen]
        if options:
            subprocess.run(['/usr/bin/usermod', *options, '--', account.pw_name], check=True)
            print('تم إعداد نطاقات المستخدم لتشغيل Podman دون root. / Rootless ID ranges configured.')
        else:
            print('نطاقات المستخدم موجودة بالفعل. / Existing rootless ID ranges retained.')


if __name__ == '__main__':
    main()
