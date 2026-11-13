"""Verify promoted bytes and every installed file before publishing a release."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile

repo = Path(__file__).resolve().parents[2]
distribution = Path(sys.argv[1]).resolve()
release = json.loads((repo / 'desktop/nahj_desktop/server_release.json').read_text())
candidate = json.loads((distribution / 'server_release.json').read_text())
candidate['published'] = True
assert candidate == release, 'Repository manifest differs from the tested candidate'
assert release['published'] and release['version'] == '0.3.2-rc1'
archive = distribution / release['archive']
assert archive.stat().st_size == release['size']
with archive.open('rb') as stream:
    assert hashlib.file_digest(stream, 'sha256').hexdigest() == release['sha256']
with tarfile.open(archive) as image:
    manifests = json.load(image.extractfile('manifest.json'))
    assert len(manifests) == 1
    assert manifests[0]['RepoTags'] == ['nahj-server:' + release['version']]
    config = image.extractfile(manifests[0]['Config']).read()
    assert 'sha256:' + hashlib.sha256(config).hexdigest() == release['image_id']

packages = list(distribution.glob('*.pkg.tar.zst'))
assert len(packages) == 1
assert packages[0].name == 'nahj-desktop-0.3.2rc1-1-any.pkg.tar.zst'
desktop = repo / 'desktop'
expected = {
    'usr/bin/nahj-desktop': desktop / 'nahj-desktop',
    'usr/share/nahj-desktop/setup_rootless.py': desktop / 'setup_rootless.py',
    'usr/share/applications/io.nahj.Desktop.desktop': desktop / 'io.nahj.Desktop.desktop',
    'usr/share/icons/hicolor/scalable/apps/io.nahj.Desktop.svg': desktop / 'io.nahj.Desktop.svg',
    'usr/share/licenses/nahj-desktop/LICENSE': repo / 'license.txt',
}
for name in ('README.md', 'SERVER.md', 'DEVELOPMENT.md'):
    expected['usr/share/doc/nahj-desktop/' + name] = desktop / name
for path in sorted((desktop / 'nahj_desktop').glob('*.py')):
    expected['usr/share/nahj-desktop/nahj_desktop/' + path.name] = path
expected['usr/share/nahj-desktop/nahj_desktop/server_release.json'] = (
    desktop / 'nahj_desktop/server_release.json'
)
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    # The package is a retained artifact of our successful Arch installer run.
    subprocess.run(['tar', '--zstd', '-xf', str(packages[0]), '-C', directory], check=True)
    actual = {str(p.relative_to(root)) for p in (root / 'usr').rglob('*') if p.is_file()}
    assert actual == set(expected), (actual - set(expected), set(expected) - actual)
    for name, source in expected.items():
        assert not (root / name).is_symlink(), name
        assert (root / name).read_bytes() == source.read_bytes(), name
        assert (root / name).stat().st_mode & 0o777 == (0o755 if name == 'usr/bin/nahj-desktop' else 0o644), name
(distribution / 'server_release.json').write_text(json.dumps(release, indent=2) + '\n')
print('PASS: exact tested server archive, final manifest and every installed package file')
