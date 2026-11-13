#!/usr/bin/env bash
# Build from pinned upstream sources on a disposable CI runner.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
work=${RUNNER_TEMP:?Disposable CI runner required}/nahj-build
mkdir -p "$work"
cd "$work"
version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["version"])' "$repo/desktop/nahj_desktop/server_release.json")
if [[ "$version" != 0.3.1-rc1 ]]; then
    # Payments releases promote one tested archive. Re-resolving dependencies
    # during acceptance would test a different build from the public download.
    python3 - "$repo" "$work" <<'PYPUBLISHED'
import hashlib,json,pathlib,sys,tarfile
from urllib.request import urlretrieve
repo,work=map(pathlib.Path,sys.argv[1:])
release=json.loads((repo/'desktop/nahj_desktop/server_release.json').read_text())
assert release['published'], 'Use the candidate workflow before publication'
archive=work/release['archive']
urlretrieve(release['url'],archive)
assert archive.stat().st_size==release['size']
with archive.open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==release['sha256']
with tarfile.open(archive) as t:
    manifests=json.load(t.extractfile('manifest.json'))
    assert len(manifests)==1 and manifests[0]['RepoTags']==['nahj-server:'+release['version']]
    config=t.extractfile(manifests[0]['Config']).read()
    assert 'sha256:'+hashlib.sha256(config).hexdigest()==release['image_id']
(work/'verified-published-image.json').write_text(json.dumps(release,indent=2)+'\n')
print('PASS: downloaded the exact published archive and verified its size, SHA256 and image config ID')
PYPUBLISHED
    exit 0
fi
python3 -m venv "$work/build-env"
"$work/build-env/bin/pip" install --require-hashes -r "$repo/desktop/server-image/requirements.txt"
curl --fail --location --retry 3 -o crane.tar.gz https://github.com/google/go-containerregistry/releases/download/v0.22.1/go-containerregistry_Linux_x86_64.tar.gz
printf '%s  crane.tar.gz\n' 0ab7a1d6932a213aed964ce97666c3077fe691c8606413674a8b3e0b9ec4cda0 | sha256sum --check
tar -xzf crane.tar.gz crane
"$work/build-env/bin/python" "$repo/desktop/server-image/build.py" --crane "$work/crane" \
    --work-dir "$work" --output "$work/nahj-server-0.3.1-rc1-amd64.tar.gz"
# Do not silently substitute a rebuilt image for the pinned release artifact.
python3 - "$repo" "$work" <<'PY'
import json, pathlib, sys
repo, work = map(pathlib.Path, sys.argv[1:])
expected = json.loads((repo / 'desktop/nahj_desktop/server_release.json').read_text())
actual = json.loads((work / 'nahj-server-0.3.1-rc1-amd64.tar.json').read_text())
for key in ('image_id', 'sha256', 'size'):
    if actual[key] != expected[key]:
        raise SystemExit(f'Rebuilt release mismatch for {key}: {actual[key]} != {expected[key]}')
print('PASS: rebuilt server image exactly matches the release image ID, archive SHA256 and size')
PY
