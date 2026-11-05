"""Real gettext/print-language regression against existing disposable records."""
import json
import os
import re
import sys

import frappe
from frappe.utils import money_in_words


def main():
    site = os.environ.get('NAHJ_ACCEPTANCE_SITE', '')
    if site != 'nahj-recovery.localhost' and not site.startswith('nahj-validation'):
        raise RuntimeError('A disposable validation site is required')
    records = json.load(sys.stdin)['records']
    frappe.init(site, sites_path='.')
    if not frappe.conf.get('nahj_disposable_test_site'):
        raise RuntimeError('Refusing to inspect a non-disposable site')
    frappe.connect()
    frappe.set_user('Administrator')
    frappe.local.lang = 'ar'
    for source, expected in {
        'Amount': 'المبلغ', 'Nos': 'عدد', 'In Words': 'المبلغ كتابة',
        'Save & Apply': 'حفظ وتطبيق', 'Search by label or field name': 'البحث حسب التسمية أو اسم الحقل',
        'Changed {0} by {1}': 'تم تغيير {0} بمقدار {1}',
    }.items():
        assert frappe._(source) == expected, (source, frappe._(source))
    assert frappe._('Example: {{ subject }}') == 'مثال: {{ subject }}'
    invoice_words = None
    for doctype, key in (('Sales Invoice', 'sales_invoice'), ('Purchase Invoice', 'purchase_invoice'),
                         ('Payment Entry', 'payment')):
        name = records[key]
        stored = frappe.get_doc(doctype, name).as_json()
        words = {}
        for language in ('ar', 'en', 'ar'):
            frappe.local.lang = language
            doc = frappe.get_doc(doctype, name)
            doc.before_print(frappe.get_cached_doc('Print Settings'))
            words[language] = doc.in_words
            assert doc.in_words
            if language == 'ar':
                assert re.search(r'[\u0600-\u06ff]', doc.in_words), doc.in_words
                assert not re.search(r'\b(two|hundred|forty|only)\b', doc.in_words, re.I), doc.in_words
            else:
                assert not re.search(r'[\u0600-\u06ff]', doc.in_words), doc.in_words
        assert words['ar'] != words['en']
        if doctype == 'Sales Invoice':
            invoice_words = words['ar']
        assert frappe.get_doc(doctype, name).as_json() == stored, 'Printing changed stored accounting data'
    frappe.local.lang = 'ar'
    # Check the real Standard renderer, not only the document method.
    html = frappe.get_print('Sales Invoice', records['sales_invoice'], print_format='Standard')
    for text in ('المبلغ', 'سعر الوحدة', 'المبلغ كتابة', invoice_words):
        assert text in html, f'Arabic text missing from actual print HTML: {text}'
    assert not re.search(r'>\s*Nos\s*<', html), 'Untranslated unit in the print table'
    assert '£ or' not in html, 'Upstream descriptive currency symbol leaked into Arabic print'
    for amount in (0, 0.25, 1, 2, 11, 240.25):
        assert re.search(r'[\u0600-\u06ff]', money_in_words(amount, 'EGP'))
    frappe.db.rollback()
    frappe.destroy()
    print('PASS: actual Arabic gettext, preserved template variables, Arabic/English invoice/purchase/payment words, unchanged posted data and Standard print HTML')


if __name__ == '__main__':
    main()
