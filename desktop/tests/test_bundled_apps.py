import json
from pathlib import Path
import tempfile
import unittest

from nahj_desktop.provision import bundled_apps


class BundledAppsTests(unittest.TestCase):
    def test_legacy_and_verified_payments_inventory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'apps.json'
            self.assertEqual(bundled_apps(path), ['frappe', 'erpnext'])
            path.write_text(json.dumps({'install_order': ['frappe', 'payments', 'erpnext']}))
            self.assertEqual(bundled_apps(path), ['frappe', 'payments', 'erpnext'])
            for apps in (['frappe', 'unknown', 'erpnext'], ['erpnext', 'payments'], ['frappe', 'erpnext', 'payments']):
                path.write_text(json.dumps({'install_order': apps}))
                with self.assertRaisesRegex(RuntimeError, 'Unsupported'):
                    bundled_apps(path)
