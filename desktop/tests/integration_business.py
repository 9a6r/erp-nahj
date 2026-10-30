"""Real acceptance checks, run only inside an explicitly disposable Frappe site.

NAHJ_ACCEPTANCE_SITE must start with `nahj-validation` or equal `nahj.localhost`.
Creates real submitted transactions; never run against a company production site.
Run with the bench virtualenv Python, with sites/ as the current directory.
"""
import hashlib
import json
import os
from pathlib import Path
import time

import frappe


def main():
    site = os.environ.get('NAHJ_ACCEPTANCE_SITE', '')
    if not (site == 'nahj.localhost' or site.startswith('nahj-validation')):
        raise RuntimeError('An explicitly named disposable acceptance site is required.')
    frappe.init(site, sites_path='.')
    if not frappe.conf.get('nahj_disposable_test_site'):
        raise RuntimeError('Set nahj_disposable_test_site only on a disposable validation site before running this test.')
    frappe.connect()
    frappe.set_user('Administrator')
    assert frappe.__version__ == '16.54.0', frappe.__version__
    import erpnext
    assert erpnext.__version__ == '16.53.0', erpnext.__version__
    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
    if not frappe.is_setup_complete():
        setup_complete(dict(language='English', country='Egypt', currency='EGP',
                            timezone='Africa/Cairo', company_name='Nahj Validation',
                            company_abbr='NV', full_name='Validation Administrator',
                            email='Administrator', chart_of_accounts='Standard',
                            fy_start_date='2026-01-01', fy_end_date='2026-12-31',
                            domain='Services', enable_telemetry=0))
    company = frappe.get_doc('Company', 'Nahj Validation')
    assert frappe.is_setup_complete()
    today = frappe.utils.nowdate()
    customer = frappe.get_doc(dict(doctype='Customer', customer_name='عميل اختبار نهج',
                                   customer_type='Company', customer_group='Commercial', territory='Egypt')).insert()
    supplier = frappe.get_doc(dict(doctype='Supplier', supplier_name='مورد اختبار نهج',
                                   supplier_group='Services', supplier_type='Company')).insert()
    item = frappe.get_doc(dict(doctype='Item', item_code='NAHJ-VALIDATION-STOCK',
                               item_name='صنف اختبار حقيقي', item_group='Products',
                               stock_uom='Nos', is_stock_item=1)).insert()
    warehouse = frappe.db.get_value('Warehouse', {'company': company.name, 'is_group': 0, 'warehouse_type': 'Stores'}, 'name')
    if not warehouse:
        warehouse = frappe.db.get_value('Warehouse', {'company': company.name, 'is_group': 0}, 'name')
    receipt = frappe.get_doc(dict(doctype='Stock Entry', stock_entry_type='Material Receipt',
                                  company=company.name, posting_date=today,
                                  items=[dict(item_code=item.name, qty=10, basic_rate=50,
                                              t_warehouse=warehouse)])).insert()
    receipt.submit()
    invoice = frappe.get_doc(dict(doctype='Sales Invoice', company=company.name,
                                  customer=customer.name, posting_date=today, due_date=today,
                                  update_stock=1, items=[dict(item_code=item.name, qty=2,
                                                            rate=120, warehouse=warehouse)])).insert()
    invoice.submit()
    assert invoice.grand_total == 240
    assert frappe.db.get_value('Bin', {'item_code': item.name, 'warehouse': warehouse}, 'actual_qty') == 8
    ledger = frappe.db.sql('select sum(debit), sum(credit) from `tabGL Entry` where voucher_type=%s and voucher_no=%s',
                          ('Sales Invoice', invoice.name))[0]
    assert abs(ledger[0] - ledger[1]) < 0.001 and ledger[0] > 0
    from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
    payment = get_payment_entry('Sales Invoice', invoice.name, bank_account=company.default_cash_account)
    payment.insert()
    payment.submit()
    assert frappe.db.get_value('Sales Invoice', invoice.name, 'outstanding_amount') == 0
    purchase = frappe.get_doc(dict(doctype='Purchase Invoice', company=company.name,
                                   supplier=supplier.name, posting_date=today, due_date=today,
                                   update_stock=1, items=[dict(item_code=item.name, qty=3,
                                                             rate=40, warehouse=warehouse)])).insert()
    purchase.submit()
    assert purchase.grand_total == 120
    assert frappe.db.get_value('Bin', {'item_code': item.name, 'warehouse': warehouse}, 'actual_qty') == 11
    from frappe.utils.file_manager import save_file
    attachments = []
    for private in (0, 1):
        content = ('مرفق نهج عام' if not private else 'مرفق نهج خاص').encode()
        attached = save_file(f'nahj-{private}.txt', content, 'Customer', customer.name, is_private=private)
        assert Path(attached.get_full_path()).read_bytes() == content
        attachments.append({'name': attached.name, 'url': attached.file_url,
                            'sha256': hashlib.sha256(content).hexdigest(), 'private': private})
    from erpnext.www.banking import set_language
    assert set_language('ar')['direction'] == 'rtl'
    assert set_language('en')['direction'] == 'ltr'
    user = frappe.get_doc(dict(doctype='User', email='nahj-reader@example.invalid',
                               first_name='Restricted', user_type='System User', send_welcome_email=0)).insert()
    frappe.set_user(user.name)
    assert not frappe.has_permission('Sales Invoice', 'read')
    frappe.set_user('Administrator')
    frappe.db.commit()
    job = frappe.enqueue('frappe.utils.now', queue='short', job_id='nahj-validation-worker')
    deadline = time.monotonic() + 60
    while not job.is_finished and time.monotonic() < deadline:
        time.sleep(1)
        job.refresh()
        if job.is_failed:
            raise AssertionError(job.exc_info)
    assert job.is_finished, 'Background job did not finish'
    from frappe.utils.scheduler import is_scheduler_disabled
    assert not is_scheduler_disabled()
    result = dict(site=site, company=company.name, customer=customer.name,
                  sales_invoice=invoice.name, purchase_invoice=purchase.name, payment=payment.name,
                  stock_item=item.name, warehouse=warehouse, stock_qty=11, files=attachments,
                  checks=['company_setup', 'arabic_records', 'stock_receipt', 'sales_invoice',
                          'balanced_gl', 'payment', 'purchase_invoice', 'stock_ledger',
                          'public_private_attachments', 'language', 'permissions', 'worker', 'scheduler'])
    Path(site, 'private', 'nahj-acceptance.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    frappe.destroy()


if __name__ == '__main__':
    main()
