"""Diagnose upstream calendar-sensitive fixtures on an isolated real ERP database.

Keep the original test failures visible. The additional boundary cases measure
the actual monthly budget instead of assuming a calendar-dependent threshold.
"""
import hashlib
import importlib
import json
import os
from pathlib import Path
import unittest

assert os.environ.get('NAHJ_DISPOSABLE_MODULE_TESTS') == '1'
os.chdir('/home/frappe/frappe-bench/sites')
import frappe
from frappe.parallel_test_runner import ParallelTestRunner
from freezegun import freeze_time

frappe.init('test_site', sites_path='.')
assert frappe.conf.nahj_disposable_test_site and frappe.conf.allow_tests
frappe.connect()
import erpnext
assert (frappe.__version__, erpnext.__version__) == ('16.54.0', '16.53.0')
root = Path(frappe.get_app_path('erpnext')).parent
plan = json.loads(Path('/checks/inventory.json').read_text())
for entry in plan['files']:
    assert hashlib.sha256((root / entry['path']).read_bytes()).hexdigest() == entry['sha256']
runner = ParallelTestRunner('erpnext', 'test_site', lightmode=True)
runner.setup_test_site()
frappe.set_user('Administrator')
importlib.import_module('erpnext.tests.bootstrap_test_data')
frappe.db.commit()

from erpnext.accounts.doctype.budget.test_budget import (
    TestBudget, make_budget, make_journal_entry, set_total_expense_zero,
)
from erpnext.accounts.doctype.budget.budget import BudgetError, get_accumulated_monthly_budget
from erpnext.tests.utils import ERPNextTestSuite
from frappe.utils import nowdate

evidence = {'original': [], 'boundaries': [], 'changes_to_erpnext_source': False}


class BudgetBoundary(ERPNextTestSuite):
    def __init__(self, against, over):
        super().__init__('runTest')
        self.against, self.over = against, over
        self.observation = {}

    def runTest(self):
        frappe.db.set_single_value('Accounts Settings', 'use_legacy_budget_controller', False)
        field = 'project' if self.against == 'Project' else 'cost_center'
        set_total_expense_zero(nowdate(), field)
        budget = make_budget(budget_against=self.against, do_not_save=False, submit_budget=True)
        # Isolate the monthly rule: allow the initial over-budget fixture even
        # in December, when the accumulated monthly and annual limits coincide.
        frappe.db.set_value('Budget', budget.name, 'action_if_annual_budget_exceeded', 'Ignore')
        limit = get_accumulated_monthly_budget(budget.name, nowdate())
        remaining = limit + (1 if self.over else -1)
        project = frappe.get_value('Project', {'project_name': '_Test Project'}) if field == 'project' else None
        entries = [make_journal_entry(
            '_Test Account Cost for Goods Sold - _TC', '_Test Bank - _TC', amount,
            '_Test Cost Center - _TC', posting_date=nowdate(), submit=True, project=project,
        ) for amount in (remaining, 10)]
        frappe.db.set_value('Budget', budget.name, 'action_if_accumulated_monthly_budget_exceeded', 'Stop')
        self.observation = dict(date=nowdate(), against=self.against, limit=limit,
                                remaining_after_cancel=remaining, should_block=self.over)
        if self.over:
            frappe.db.savepoint('before_cancel')
            with self.assertRaises(BudgetError):
                entries[-1].cancel()
            frappe.db.rollback(save_point='before_cancel')
            entries[-1].reload()
            self.assertEqual(entries[-1].docstatus, 1)
        else:
            entries[-1].cancel()
            entries[-1].reload()
            self.assertEqual(entries[-1].docstatus, 2)


try:
    # Preserve a separate outcome for every unchanged original test/month.
    for month in range(1, 13):
        with freeze_time(f'2026-{month:02d}-12 12:00:00'):
            for name in ('test_monthly_budget_on_cancellation1', 'test_monthly_budget_on_cancellation2'):
                result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite([TestBudget(name)]))
                evidence['original'].append(dict(month=month, test=name, tests=result.testsRun,
                    failures=[detail for _, detail in result.failures],
                    errors=[detail for _, detail in result.errors], successful=result.wasSuccessful()))
            for against in ('Cost Center', 'Project'):
                for over in (False, True):
                    case = BudgetBoundary(against, over)
                    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite([case]))
                    evidence['boundaries'].append(dict(
                        {'month': month, 'against': against, 'over': over, **case.observation},
                        successful=result.wasSuccessful(),
                        failures=[detail for _, detail in result.failures],
                        errors=[detail for _, detail in result.errors]))
finally:
    Path('/results/budget-diagnostic.json').write_text(json.dumps(evidence, indent=2, default=str))
    frappe.destroy()

original_pattern = all(not x['errors'] and x['tests'] == 1 and
                       len(x['failures']) == (1 if x['month'] in (11, 12) else 0)
                       for x in evidence['original']) and len(evidence['original']) == 24
boundaries_pass = len(evidence['boundaries']) == 48 and all(x['successful'] for x in evidence['boundaries'])
print(json.dumps(dict(original_runs=len(evidence['original']),
    original_failures=sum(len(x['failures']) for x in evidence['original']),
    calendar_pattern_confirmed=original_pattern, boundary_cases=len(evidence['boundaries']),
    boundary_cases_passed=sum(x['successful'] for x in evidence['boundaries']))))
raise SystemExit(0 if original_pattern and boundaries_pass else 1)
