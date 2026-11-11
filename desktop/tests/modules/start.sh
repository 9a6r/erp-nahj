#!/usr/bin/env bash
set -euo pipefail
cd /home/frappe/frappe-bench
# Install only upstream's test helpers into this disposable container's venv.
env/bin/python -m ensurepip
env/bin/python -m pip install 'coverage~=7.10.0' 'Faker~=18.10.1' 'hypothesis~=6.77.0' 'freezegun~=1.5.5' 'responses==0.23.1' 'unittest-xml-reporting~=3.2.0'
env/bin/python /checks/prepare.py
env/bin/gunicorn --bind 0.0.0.0:8000 --threads 4 --timeout 120 frappe.app:application >/results/web.log 2>&1 &
web=$!
bench worker --queue short,default,long >/results/worker.log 2>&1 &
worker=$!
trap 'kill "$web" "$worker" 2>/dev/null || true' EXIT
env/bin/python -u /checks/run_suite.py "$NAHJ_TEST_SHARD"
