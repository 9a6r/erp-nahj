"""Build a new immutable Payments candidate; never replace published artifacts.

Only for a disposable GitHub runner. Test and publish this exact archive rather
than resolving dependencies a second time during release publication.
"""
import gzip
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
from urllib.request import urlretrieve

HERE = Path(__file__).resolve().parent
VERSION = '0.3.2-rc1'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    work = Path(os.environ['RUNNER_TEMP']) / 'nahj-candidate'
    work.mkdir(parents=True, exist_ok=False)
    base = json.loads((HERE / 'base-release-0.3.1.json').read_text())
    lock = json.loads((HERE / 'payments-lock.json').read_text())
    base_archive = work / base['archive']
    urlretrieve(base['url'], base_archive)
    assert digest(base_archive) == base['sha256'] and base_archive.stat().st_size == base['size']
    with tarfile.open(base_archive) as archive:
        expected = json.load(archive.extractfile(base['image_id'].removeprefix('sha256:') + '.json'))
    subprocess.run(['docker', 'load', '-i', str(base_archive)], check=True)
    base_archive.unlink()
    actual = json.loads(subprocess.check_output(['docker', 'image', 'inspect', 'nahj-server:0.3.1-rc1']))[0]
    assert actual['RootFS']['Layers'] == expected['rootfs']['diff_ids']
    for key in ('Entrypoint', 'Cmd', 'User', 'WorkingDir', 'Env', 'Labels'):
        assert actual['Config'].get(key) == expected['config'].get(key), key
    source = work / 'payments.tar.gz'
    urlretrieve(lock['url'], source)
    assert digest(source) == lock['sha256']
    with tarfile.open(source) as archive:
        archive.extractall(work, filter='data')
    (work / ('payments-' + lock['commit'])).rename(work / 'payments')
    source.unlink()
    restore_sources = {base['image_id']: {k: base[k] for k in ('erpnext_version', 'frappe_version')}}
    inventory = dict(install_order=['frappe', 'payments', 'erpnext'], payments=lock,
                     restore_sources=restore_sources)
    (work / 'apps.json').write_text(json.dumps(inventory, indent=2))
    for name in ('Payments.Dockerfile', 'payments-constraints.txt'):
        shutil.copyfile(HERE / name, work / name)
    tag = 'nahj-server:' + VERSION
    subprocess.run(['docker', 'build', '--pull=false', '-f', str(work / 'Payments.Dockerfile'),
                    '-t', tag, str(work)], check=True)
    destination = work / f'nahj-server-{VERSION}-amd64.tar.gz'
    with destination.open('wb') as output, gzip.GzipFile(fileobj=output, mode='wb', mtime=0,
                                                       filename='', compresslevel=1) as compressed:
        process = subprocess.Popen(['docker', 'save', tag], stdout=subprocess.PIPE)
        try:
            shutil.copyfileobj(process.stdout, compressed)
        finally:
            process.stdout.close()
        if process.wait():
            raise RuntimeError('Docker archive export failed')
    with tarfile.open(destination) as archive:
        manifest = json.load(archive.extractfile('manifest.json'))
        assert len(manifest) == 1 and manifest[0]['RepoTags'] == [tag]
        config_bytes = archive.extractfile(manifest[0]['Config']).read()
        config = json.loads(config_bytes)
        assert config['architecture'] == 'amd64' and config['os'] == 'linux'
    release = {**base, 'version': VERSION, 'archive': destination.name,
               'image_id': 'sha256:' + hashlib.sha256(config_bytes).hexdigest(),
               'sha256': digest(destination), 'size': destination.stat().st_size,
               'published': False, 'apps': inventory['install_order'], 'payments': lock,
               'restore_sources': restore_sources,
               'url': f'https://github.com/9a6r/erp-nahj/releases/download/desktop-v{VERSION}/{destination.name}',
               'candidate_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()}
    (work / 'server_release.json').write_text(json.dumps(release, indent=2) + '\n')
    print(json.dumps(release, indent=2))


if __name__ == '__main__':
    main()
