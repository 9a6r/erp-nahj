"""Verify existing disposable business records after restart or recovery."""
import hashlib
import json
import os
from pathlib import Path
import sys
import time

import frappe


def main():
    site = os.environ.get('NAHJ_ACCEPTANCE_SITE', '')
    if site != 'nahj-recovery.localhost' and not site.startswith('nahj-validation'):
        raise RuntimeError('A disposable validation site is required')
    expected = json.load(sys.stdin)
    frappe.init(site, sites_path='.')
    if not frappe.conf.get('nahj_disposable_test_site'):
        raise RuntimeError('Refusing to inspect a non-disposable site')
    frappe.connect()
    frappe.set_user('Administrator')
    assert set(frappe.get_installed_apps()) == {'frappe', 'erpnext'}
    records = expected['records']
    invoice = frappe.get_doc('Sales Invoice', records['sales_invoice'])
    assert invoice.docstatus == 1 and invoice.grand_total == 240 and invoice.outstanding_amount == 0
    purchase = frappe.get_doc('Purchase Invoice', records['purchase_invoice'])
    assert purchase.docstatus == 1 and purchase.grand_total == 120
    assert frappe.db.get_value('Payment Entry', records['payment'], 'docstatus') == 1
    debit, credit = frappe.db.sql(
        'select sum(debit), sum(credit) from `tabGL Entry` where voucher_type=%s and voucher_no=%s',
        ('Sales Invoice', invoice.name))[0]
    assert debit > 0 and abs(debit - credit) < 0.001
    assert frappe.db.get_value('Bin', {'item_code': records['stock_item'],
        'warehouse': records['warehouse']}, 'actual_qty') == records['stock_qty']
    for attachment in records['files']:
        file = frappe.get_doc('File', attachment['name'])
        assert hashlib.sha256(Path(file.get_full_path()).read_bytes()).hexdigest() == attachment['sha256']
    from frappe.utils.password import get_decrypted_password
    assert get_decrypted_password('User', 'Administrator', 'nahj_validation_canary') == expected['canary']
    pending = expected['pending']
    assert bool(frappe.conf.pause_scheduler) == pending
    assert bool(frappe.conf.mute_emails) == pending
    assert bool(frappe.db.get_single_value('System Settings', 'enable_scheduler')) != pending
    frappe.set_user('nahj-reader@example.invalid')
    assert not frappe.has_permission('Sales Invoice', 'read')
    frappe.set_user('Administrator')
    if not pending:
        job = frappe.enqueue('frappe.utils.now', queue='short')
        deadline = time.monotonic() + 90
        while not job.is_finished and time.monotonic() < deadline:
            time.sleep(1)
            job.refresh()
            assert not job.is_failed, 'Separate worker failed the real queued job'
        assert job.is_finished, 'Separate worker did not finish the real queued job'
    frappe.destroy()
    print('PASS: submitted transactions, balanced ledger, payment, stock, attachments, encrypted secret, permissions and recovery state')


if __name__ == '__main__':
    main()
