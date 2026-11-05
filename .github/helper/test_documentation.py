import os
import unittest
from unittest.mock import Mock, patch

import documentation


class DocumentationTests(unittest.TestCase):
	def test_local_document_paths_keep_their_case(self):
		payload = {"title": "feat: recovery", "head": {"sha": "commit"}, "body": "Documentation: desktop/SERVER.md"}
		with patch.dict(os.environ, {"GITHUB_REPOSITORY": "9a6r/erp-nahj"}), patch.object(
			documentation.requests, "get", return_value=Mock(ok=True, json=lambda: payload)
		) as request:
			self.assertEqual(documentation.check_pull_request("3")[0], 0)
			self.assertEqual(request.call_args.args[0], "https://api.github.com/repos/9a6r/erp-nahj/pulls/3")

	def test_missing_and_traversing_paths_are_rejected(self):
		for path in ("desktop/DOES_NOT_EXIST.md", "desktop/../README.md"):
			self.assertFalse(documentation.is_documentation_link(path))

	def test_inline_code_and_upstream_links_are_accepted(self):
		self.assertTrue(documentation.contains_documentation_link("See `desktop/SERVER.md`"))
		self.assertTrue(documentation.is_documentation_link("https://docs.frappe.io/erpnext/user/manual/en"))
