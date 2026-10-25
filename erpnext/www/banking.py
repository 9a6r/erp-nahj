import json
import re
from urllib.parse import urlencode

import frappe
import frappe.sessions
from frappe import _
from frappe.utils.jinja_globals import is_rtl
from frappe.utils.user import is_website_user

no_cache = 1

SCRIPT_TAG_PATTERN = re.compile(r"\<script[^<]*\</script\>", re.IGNORECASE)
CLOSING_SCRIPT_TAG_PATTERN = re.compile(r"</script\>", re.IGNORECASE)


def get_context(context):
	validate_desk_user()
	csrf_token = frappe.sessions.get_csrf_token()

	context = frappe._dict()
	context.boot = get_boot()
	context.csrf_token = csrf_token
	context.build_version = frappe.utils.get_build_version()
	context.app_name = (
		frappe.get_website_settings("app_name") or frappe.get_system_settings("app_name") or "ERPNext"
	)

	context.layout_direction = "rtl" if is_rtl() else "ltr"
	context.lang = frappe.local.lang

	return context


def validate_desk_user():
	if frappe.session.user == "Guest":
		frappe.response["status_code"] = 403
		frappe.msgprint(_("Log in to access this page."))
		frappe.redirect(f"/login?{urlencode({'redirect-to': frappe.request.path})}")

	elif is_website_user():
		frappe.throw(_("You are not permitted to access this page."), frappe.PermissionError)


@frappe.whitelist(methods=["POST"], allow_guest=True)
def get_context_for_dev():
	if not frappe.conf.developer_mode:
		frappe.throw(_("This method is only meant for developer mode"))
	validate_desk_user()
	return {
		"boot": json.loads(get_boot()),
		"layout_direction": "rtl" if is_rtl() else "ltr",
		"lang": frappe.local.lang,
	}


def get_boot():
	language = frappe.local.lang
	try:
		boot = frappe.sessions.get()
	except Exception as e:
		raise frappe.SessionBootFailed from e

	# Session boot may restore the account language; preserve this request choice.
	frappe.local.lang = language
	boot.lang = language
	boot.layout_direction = "rtl" if is_rtl() else "ltr"
	boot_json = frappe.as_json(boot, indent=None, separators=(",", ":"))
	boot_json = SCRIPT_TAG_PATTERN.sub("", boot_json)

	boot_json = CLOSING_SCRIPT_TAG_PATTERN.sub("", boot_json)
	boot_json = json.dumps(boot_json)

	return boot_json


@frappe.whitelist(methods=["POST"])
def set_language(language: str):
	"""Change only the authenticated user's language and refresh their boot cache."""
	if language not in ("ar", "en"):
		frappe.throw(_("Unsupported language"), frappe.ValidationError)
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login"), frappe.PermissionError)
	frappe.db.set_value("User", frappe.session.user, "language", language)
	frappe.clear_cache(user=frappe.session.user)
	return {"language": language, "direction": "rtl" if language == "ar" else "ltr"}
