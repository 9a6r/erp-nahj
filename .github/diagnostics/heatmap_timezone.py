"""Reproduce the original heatmap test around the India/UTC date boundary."""
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
from frappe.utils import nowdate

frappe.init('test_site', sites_path='.')
assert frappe.conf.nahj_disposable_test_site and frappe.conf.allow_tests
frappe.connect()
ParallelTestRunner('erpnext', 'test_site', lightmode=True).setup_test_site()
frappe.set_user('Administrator')
importlib.import_module('erpnext.tests.bootstrap_test_data')
frappe.db.commit()
from erpnext.stock.doctype.item.test_item import TestItem
from erpnext.stock.doctype.item.item import get_timeline_data
from erpnext.stock.doctype.stock_entry.test_stock_entry import make_stock_entry

outcomes = []
try:
    for clock in ('12:00:00', '18:29:00', '18:31:00', '23:59:00'):
        for zone in ('+00:00', '+05:30'):
            with freeze_time('2026-11-20 ' + clock):
                import time
                frappe.db.sql('SET time_zone = %s', (zone,))
                frappe.db.sql('SET timestamp = %s', (int(time.time()),))
                # An actual posted stock movement ensures this is not an empty
                # heatmap passing a for-loop without exercising its assertions.
                entry = make_stock_entry(item_code='_Test Item', qty=1,
                    to_warehouse='_Test Warehouse - _TC', posting_date=nowdate(),
                    posting_time='00:00:00', set_posting_time=1)
                assert entry.docstatus == 1 and get_timeline_data('Item', '_Test Item')
                result = unittest.TextTestRunner().run(unittest.TestSuite([TestItem('test_heatmap_data')]))
                outcomes.append(dict(clock_utc=clock, database_zone=zone,
                    passed=result.wasSuccessful(), failures=[s for _, s in result.failures],
                    errors=[s for _, s in result.errors]))
                frappe.db.rollback()
finally:
    Path('/results/heatmap-timezone.json').write_text(json.dumps(outcomes, indent=2))
    frappe.db.sql('SET timestamp = 0')
    frappe.destroy()
assert len(outcomes) == 8
assert all(not x['errors'] for x in outcomes)
assert all(x['passed'] for x in outcomes if x['database_zone'] == '+05:30')
assert all(x['passed'] == (x['clock_utc'] < '18:30:00') for x in outcomes if x['database_zone'] == '+00:00')
print('PASS: real stock movements reproduce the UTC mismatch; the unchanged heatmap test passes at all four boundary times with aligned test database timezone')
