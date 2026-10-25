import unittest
from unittest.mock import patch

import frappe
from erpnext.www.banking import get_boot, set_language


class TestBankingLanguage(unittest.TestCase):
    def setUp(self):
        self.user = frappe.session.user
        frappe.set_user("Administrator")
        self.language = frappe.db.get_value("User", "Administrator", "language")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.set_value("User", "Administrator", "language", self.language)
        frappe.clear_cache(user="Administrator")
        frappe.db.rollback()
        frappe.set_user(self.user)

    def test_language_persists_and_returns_direction(self):
        for language, direction in [("ar", "rtl"), ("en", "ltr")]:
            self.assertEqual(set_language(language), {"language": language, "direction": direction})
            self.assertEqual(frappe.db.get_value("User", "Administrator", "language"), language)

    def test_rejects_unsupported_language(self):
        with self.assertRaises(frappe.ValidationError):
            set_language("invalid")
        self.assertEqual(frappe.db.get_value("User", "Administrator", "language"), self.language)

    def test_guest_cannot_change_language(self):
        frappe.set_user("Guest")
        with self.assertRaises(frappe.PermissionError):
            set_language("ar")

    def test_boot_preserves_requested_language(self):
        previous = frappe.local.lang
        def session_boot():
            frappe.local.lang = "en"
            return frappe._dict(lang="en")
        try:
            frappe.local.lang = "ar"
            with patch("frappe.sessions.get", side_effect=session_boot):
                get_boot()
            self.assertEqual(frappe.local.lang, "ar")
        finally:
            frappe.local.lang = previous
