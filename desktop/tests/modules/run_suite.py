"""Execute upstream tests in an explicitly disposable site with per-test evidence."""
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time
import traceback

assert os.environ.get('NAHJ_DISPOSABLE_MODULE_TESTS') == '1'
shard = int(sys.argv[1])
out = Path('/results')
plan = json.loads(Path('/checks/inventory.json').read_text())
smoke = os.environ.get('NAHJ_SMOKE_ONLY') == '1'
selected = [f for f in plan['files'] if
            (f['path'] == 'erpnext/stock/doctype/bin/test_bin.py' if smoke else f['shard'] == shard)]
assert selected

import coverage
cov = coverage.Coverage(data_file=str(out / '.coverage'), source=['erpnext'], branch=True,
                        omit=['*/test_*.py', '*/tests/*', '*/patches/*'])
cov.start()
import frappe
from frappe.parallel_test_runner import ParallelTestRunner
from frappe.testing.result import TestResult

os.chdir('/home/frappe/frappe-bench/sites')
frappe.init('test_site', sites_path='.')
assert frappe.conf.nahj_disposable_test_site and frappe.conf.allow_tests
frappe.connect()
assert frappe.__version__ == '16.54.0'
import erpnext
assert erpnext.__version__ == '16.53.0'
root = Path(frappe.get_app_path('erpnext')).parent
for entry in plan['files']:
    assert hashlib.sha256((root / entry['path']).read_bytes()).hexdigest() == entry['sha256'], entry['path']

stream = (out / 'events.jsonl').open('w', buffering=1)

def event(**data):
    stream.write(json.dumps(data, ensure_ascii=False) + '\n')


class RecordedResult(TestResult):
    def addSuccess(self, test):
        super().addSuccess(test)
        event(test=test.id(), status='passed')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        event(test=test.id(), status='failed', detail=self.failures[-1][1])

    def addError(self, test, err):
        super().addError(test, err)
        event(test=test.id(), status='error', detail=self.errors[-1][1])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        event(test=test.id(), status='skipped', reason=reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        event(test=test.id(), status='expected_failure', detail=self.expectedFailures[-1][1])

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        event(test=test.id(), status='unexpected_success')

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err:
            event(test=test.id(), subtest=str(subtest), status='subtest_failure',
                  detail=''.join(traceback.format_exception(*err)))


runner = ParallelTestRunner('erpnext', 'test_site', lightmode=True)
runner.setup_test_site()
frappe.set_user('Administrator')
# The same fixture bootstrap used by upstream CI; no synthetic replacement tests.
importlib.import_module('erpnext.tests.bootstrap_test_data')
frappe.db.commit()
result = RecordedResult(stream=sys.stderr, descriptions=True, verbosity=2)
runner.test_result = result
module_errors = []
completed = []
try:
    for entry in selected:
        name = entry['path']
        started = time.monotonic()
        before = result.testsRun
        print('MODULE_START ' + name, flush=True)
        event(module=name, status='started')
        try:
            frappe.set_user('Administrator')
            path = root / name
            runner.run_tests_for_file((str(path.parent), path.name))
        except Exception:
            detail = traceback.format_exc()
            module_errors.append(name)
            event(module=name, status='module_error', detail=detail)
            print(detail, flush=True)
            frappe.db.rollback()
        else:
            completed.append(name)
        event(module=name, status='finished', executed=result.testsRun-before,
              seconds=round(time.monotonic()-started, 3))
        print(f'MODULE_END {name}: {result.testsRun-before} tests', flush=True)
finally:
    cov.stop()
    cov.save()
    summary = dict(shard=shard, smoke=smoke, planned_files=len(selected), completed_files=len(completed),
                   module_errors=module_errors, tests_run=result.testsRun,
                   failures=len(result.failures), errors=len(result.errors),
                   skipped=len(result.skipped), expected_failures=len(result.expectedFailures),
                   unexpected_successes=len(result.unexpectedSuccesses),
                   successful=result.testsRun > 0 and result.wasSuccessful() and not module_errors)
    (out / 'summary.json').write_text(json.dumps(summary, indent=2))
    stream.close()
    frappe.destroy()
    print(json.dumps(summary), flush=True)
result.printErrors()
raise SystemExit(0 if summary['successful'] else 1)
