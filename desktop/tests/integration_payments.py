"""Verify bundled Payments storage and imports; no provider charge is simulated."""
import json
import os
from pathlib import Path

import frappe

site = os.environ['NAHJ_ACCEPTANCE_SITE']
assert site.startswith('nahj-validation')
frappe.init(site, sites_path='.')
assert frappe.conf.nahj_disposable_test_site
frappe.connect()
inventory = Path('/home/frappe/nahj-apps.json')
if inventory.exists():
    assert 'payments' in frappe.get_installed_apps()
    import payments, stripe, razorpay, braintree, gocardless_pro
    assert json.loads(inventory.read_text())['payments']['commit'] == '9e842a473a8f4ec70a9ff06a3e067d10f98d26ed'
    if 'localization' in json.loads(inventory.read_text()):
        for source, translated in (('Stripe Settings', 'إعدادات Stripe'),
                                   ('Paymob Settings', 'إعدادات Paymob'),
                                   ('Get Access Token', 'الحصول على رمز الوصول')):
            assert frappe._(source, lang='ar') == translated
            assert frappe._(source, lang='en') == source
        assert frappe._('Pay {0} {1}', lang='ar').format('12.50', 'EGP') == 'ادفع 12.50 EGP'
        old_lang = frappe.local.lang
        frappe.local.lang = 'ar'
        html = frappe.render_template('payments/templates/pages/paytm_checkout.html',
                                      {'url': 'https://example.invalid/unused', 'payment_details': {}})
        assert 'يُرجى عدم تحديث هذه الصفحة...' in html and 'صفحة الدفع لدى التاجر' in html
        frappe.local.lang = old_lang
        print('PASS: real Arabic/English Payments translations, preserved amount/currency and rendered Paytm checkout')
    # This is a saved configuration record, not an advertised provider adapter.
    name = 'Nahj Acceptance Gateway'
    if site == 'nahj-validation.localhost' and not frappe.db.exists('Payment Gateway', name):
        frappe.get_doc({'doctype': 'Payment Gateway', 'gateway': name}).insert()
        frappe.db.commit()
    assert frappe.get_doc('Payment Gateway', name).gateway == name
    print('PASS: bundled Payments imports and real gateway configuration survive restoration/reboot; live provider charging requires credentials')
else:
    assert 'payments' not in frappe.get_installed_apps()
    print('PASS: legacy image retains its original application inventory')
frappe.destroy()
