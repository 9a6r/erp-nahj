#!/usr/bin/env bash
# Run exclusively on a disposable GitHub runner, never on a company server.
set -euo pipefail
: "${RUNNER_TEMP:?Disposable CI runner required}"
: "${NAHJ_TEST_SHARD:?Select a test shard}"
repo=$(pwd)
work="$RUNNER_TEMP/nahj-modules"
mkdir -p "$work/results" "$work/checks"
chmod 777 "$work/results"
cp desktop/tests/modules/{prepare.py,run_suite.py,start.sh} "$work/checks/"
python3 desktop/tests/modules/inventory.py "$repo" > "$work/checks/inventory.json"
cp "$work/checks/inventory.json" "$work/results/inventory.json"
python3 - "$work" <<'PY'
import json, pathlib, sys, tarfile
from urllib.request import urlretrieve
work=pathlib.Path(sys.argv[1]);r=json.load(open('desktop/nahj_desktop/server_release.json'))
urlretrieve(r['url'], work/'server.tar.gz')
import hashlib
with (work/'server.tar.gz').open('rb') as f: assert hashlib.file_digest(f,'sha256').hexdigest()==r['sha256']
assert (work/'server.tar.gz').stat().st_size==r['size']
with tarfile.open(work/'server.tar.gz', 'r|gz') as archive:
    first=next(iter(archive))
    assert first.name==r['image_id'].removeprefix('sha256:')+'.json'
    config=archive.extractfile(first).read()
    assert 'sha256:'+hashlib.sha256(config).hexdigest()==r['image_id']
    (work/'expected-image-config.json').write_bytes(config)
PY
docker load -i "$work/server.tar.gz"
rm "$work/server.tar.gz"
python3 - "$work" <<'PY'
import json,pathlib,sys,os,subprocess
sys.path.insert(0,'desktop')
from nahj_desktop.server import IMAGE_ID,MARIADB_IMAGE,REDIS_IMAGE
work=pathlib.Path(sys.argv[1])
# Docker's containerd image store may expose a manifest ID instead of the
# archived config ID. Verify the loaded tag's actual rootfs and runtime config.
expected=json.loads((work/'expected-image-config.json').read_text())
actual=json.loads(subprocess.check_output(['docker','image','inspect','nahj-server:0.3.1-rc1'],text=True))[0]
assert actual['RootFS']['Layers']==expected['rootfs']['diff_ids']
for key in ('Entrypoint','Cmd','User','WorkingDir','Env','Labels'):
    assert actual['Config'].get(key)==expected['config'].get(key), key
assert actual['Architecture']==expected['architecture'] and actual['Os']==expected['os']
print('PASS: verified archive config digest, loaded rootfs layers and runtime configuration')
subprocess.run(['docker','tag','nahj-server:0.3.1-rc1','nahj-module-test:verified'],check=True)
spec={'services':{
 'db':{'image':MARIADB_IMAGE,'environment':{'MARIADB_ROOT_PASSWORD':'disposable-ci-only'},'command':['--character-set-server=utf8mb4','--collation-server=utf8mb4_unicode_ci']},
 'redis':{'image':REDIS_IMAGE},
 'tests':{'image':'nahj-module-test:verified','pull_policy':'never','working_dir':'/home/frappe/frappe-bench',
          'environment':{'CI':'1','TZ':'Asia/Kolkata','NAHJ_DISPOSABLE_MODULE_TESTS':'1','NAHJ_TEST_SHARD':os.environ['NAHJ_TEST_SHARD'],'NAHJ_SMOKE_ONLY':os.environ.get('NAHJ_SMOKE_ONLY','0')},
          'networks':{'default':{'aliases':['test_site']}},
          'volumes':[str(work/'checks')+':/checks:ro',str(work/'results')+':/results'],
          'command':['bash','/checks/start.sh']}}}
(work/'compose.json').write_text(json.dumps(spec))
PY
compose=(docker compose -p "nahj-module-$NAHJ_TEST_SHARD" -f "$work/compose.json")
cleanup() {
    status=$?
    "${compose[@]}" down --volumes || true
    # The image runs as uid 1000 with a private umask; the artifact uploader
    # runs as the host runner. Transfer only this disposable result directory.
    sudo chown -R "$(id -u):$(id -g)" "$work/results"
    exit "$status"
}
trap cleanup EXIT
"${compose[@]}" up -d db redis
# Preserve the real test exit status through tee; failed shards still upload evidence.
"${compose[@]}" run --rm --use-aliases tests 2>&1 | tee "$work/results/tests.log"
