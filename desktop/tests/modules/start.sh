#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/frappe-bench
# Install test dependencies only inside this disposable container's venv.
env/bin/python -m ensurepip
env/bin/python -m pip install 'coverage~=7.10.0' 'Faker~=18.10.1' 'hypothesis~=6.77.0' 'freezegun~=1.5.5' 'responses==0.23.1' 'unittest-xml-reporting~=3.2.0'
if [ "$NAHJ_TEST_PROFILE" = payments ]; then
    if [ ! -d apps/payments ]; then
        cp -R /checks/payments apps/payments
        env/bin/python -m pip install -e apps/payments
    fi
    env/bin/python - <<'PYSOURCE'
from pathlib import Path
import json, sys
sys.path.insert(0, '/checks')
from payments_localization import localize_checkout
inventory = Path('/home/frappe/nahj-apps.json')
localized = inventory.exists() and 'localization' in json.loads(inventory.read_text())
for source in Path('/checks/payments').rglob('*'):
    if source.is_file():
        relative = source.relative_to('/checks/payments')
        target = Path('apps/payments') / relative
        expected = source.read_bytes()
        if localized and str(relative) == 'payments/templates/pages/paytm_checkout.html':
            expected = localize_checkout(expected.decode()).encode()
        assert target.read_bytes() == expected, str(target)
print('PASS: every pinned Payments source file matches the official archive or the three reviewed Paytm translation wrappers')
PYSOURCE
fi
env/bin/python -m pip list --format=json > /results/python-packages.json
env/bin/python /checks/prepare.py
# Upstream's test server also serves /assets and /files. Bare gunicorn without
# the production nginx frontend cannot satisfy wkhtmltopdf's asset requests.
bench serve --port 8000 --noreload >/results/web.log 2>&1 &
web=$!
bench worker --queue short,default,long >/results/worker.log 2>&1 &
worker=$!
trap 'kill "$web" "$worker" 2>/dev/null || true' EXIT
env/bin/python - <<'PYREADY'
import json
from pathlib import Path
import time
from urllib.request import urlopen
for attempt in range(40):
    try:
        with urlopen('http://test_site:8000/api/method/ping', timeout=3) as response:
            assert response.status == 200
        break
    except Exception:
        if attempt == 39:
            raise
        time.sleep(1)
print('PASS: disposable Frappe HTTP service is reachable')
assets = json.loads(Path('sites/assets/assets.json').read_text())
for name in ('print_format.bundle.css', 'print.bundle.js'):
    with urlopen('http://test_site:8000' + assets[name], timeout=10) as response:
        assert response.status == 200 and response.read(), name
print('PASS: actual compiled print CSS and JavaScript are served')
PYREADY
kill -0 "$web" "$worker"
env/bin/python -u /checks/run_suite.py "$NAHJ_TEST_SHARD"
