#!/usr/bin/env bash
# Build from pinned upstream sources on a disposable CI runner.
set -euo pipefail
repo=$(cd "$(dirname "$0")/../.." && pwd)
work=${RUNNER_TEMP:?Disposable CI runner required}/nahj-build
mkdir -p "$work"
cd "$work"
curl --fail --location --retry 3 -o crane.tar.gz https://github.com/google/go-containerregistry/releases/download/v0.22.1/go-containerregistry_Linux_x86_64.tar.gz
printf '%s  crane.tar.gz\n' 0ab7a1d6932a213aed964ce97666c3077fe691c8606413674a8b3e0b9ec4cda0 | sha256sum --check
tar -xzf crane.tar.gz crane
python3 "$repo/desktop/server-image/build.py" --crane "$work/crane" \
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
