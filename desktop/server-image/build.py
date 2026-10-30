#!/usr/bin/env python3
"""Build a single-layer Docker archive from the digest-pinned official image.

Requires Google's open-source crane and a completed `yarn build` in banking/.
No Docker daemon, privileged process, registry push or application data is used.
"""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def add_bytes(archive, name, data):
    info = tarfile.TarInfo(name)
    info.size = len(data)
    info.mode = 0o644
    archive.addfile(info, io.BytesIO(data))


def package(rootfs, config, destination):
    """The inputs come from crane export/config of upstream.json's exact digest."""
    upstream = json.loads((HERE / 'upstream.json').read_text())
    overlays = {
        HERE / 'entrypoint.sh': ('home/frappe/entrypoint.sh', 0o755),
        HERE / 'check_database.py': ('home/frappe/nahj-check-database.py', 0o644),
        HERE / 'upstream.json': ('home/frappe/nahj-upstream.json', 0o644),
        REPO / 'erpnext/www/banking.py': ('home/frappe/frappe-bench/apps/erpnext/erpnext/www/banking.py', 0o644),
        REPO / 'erpnext/www/banking.html': ('home/frappe/frappe-bench/apps/erpnext/erpnext/www/banking.html', 0o644),
        REPO / 'erpnext/tests/test_banking_language.py': ('home/frappe/frappe-bench/apps/erpnext/erpnext/tests/test_banking_language.py', 0o644),
    }
    frontend = REPO / 'erpnext/public/banking'
    if not (frontend / 'index.html').is_file():
        raise RuntimeError('Build the banking frontend before building the server image.')
    for path in sorted(frontend.rglob('*')):
        if path.is_file():
            overlays[path] = ('home/frappe/frappe-bench/apps/erpnext/erpnext/public/banking/' + str(path.relative_to(frontend)), 0o644)
    # Docker rejects duplicate archive paths. Replace upstream files while
    # flattening instead of appending another copy of their tar entries.
    overlay_names = {name for name, _ in overlays.values()}
    clean_rootfs = rootfs.with_suffix('.clean.tar')
    with tarfile.open(rootfs, 'r') as original, tarfile.open(clean_rootfs, 'w') as archive:
        members = {member.name.removeprefix('./').rstrip('/'): member for member in original.getmembers()}
        for name, member in members.items():
            if name not in overlay_names:
                archive.addfile(member, original.extractfile(member) if member.isfile() else None)
        for path, (name, mode) in overlays.items():
            info = archive.gettarinfo(str(path), arcname=name)
            info.uid = info.gid = 1000
            info.uname = info.gname = 'frappe'
            info.mtime = 0
            info.mode = mode
            with path.open('rb') as stream:
                archive.addfile(info, stream)
    clean_rootfs.replace(rootfs)
    layer_hash = sha256(rootfs)
    config = dict(config)
    config['rootfs'] = {'type': 'layers', 'diff_ids': ['sha256:' + layer_hash]}
    config.pop('history', None)
    config['config']['Entrypoint'] = ['/home/frappe/entrypoint.sh']
    config['config']['Labels'] = {**config['config'].get('Labels', {}),
        'io.nahj.upstream': upstream['image'], 'io.nahj.erpnext.version': upstream['erpnext_version'],
        'org.opencontainers.image.source': 'https://github.com/9a6r/erp-nahj'}
    config_bytes = json.dumps(config, sort_keys=True, separators=(',', ':')).encode()
    image_id = hashlib.sha256(config_bytes).hexdigest()
    manifest = [{'Config': image_id + '.json', 'RepoTags': ['nahj-server:0.3.1-rc1'], 'Layers': ['layer.tar']}]
    with destination.open('wb') as output, gzip.GzipFile(fileobj=output, mode='wb', mtime=0, filename='', compresslevel=1) as compressed:
        with tarfile.open(fileobj=compressed, mode='w|') as archive:
            add_bytes(archive, image_id + '.json', config_bytes)
            add_bytes(archive, 'manifest.json', json.dumps(manifest).encode())
            info = tarfile.TarInfo('layer.tar')
            info.size = rootfs.stat().st_size
            with rootfs.open('rb') as stream:
                archive.addfile(info, stream)
    metadata = {**upstream, 'image_id': 'sha256:' + image_id,
                'archive': destination.name, 'sha256': sha256(destination), 'size': destination.stat().st_size}
    destination.with_suffix('.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--crane', default='crane')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--work-dir', type=Path, required=True)
    args = parser.parse_args()
    upstream = json.loads((HERE / 'upstream.json').read_text())
    args.work_dir.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=args.work_dir, prefix='nahj-image-') as directory:
        rootfs = Path(directory) / 'rootfs.tar'
        base = [args.crane, '--platform', upstream['platform']]
        config = json.loads(subprocess.check_output([*base, 'config', upstream['image']]))
        subprocess.run([*base, 'export', upstream['image'], str(rootfs)], check=True)
        print(json.dumps(package(rootfs, config, args.output), indent=2))


if __name__ == '__main__':
    main()
