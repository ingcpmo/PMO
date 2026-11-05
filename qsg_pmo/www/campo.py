# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""App de campo para técnicos: /campo (pensada para celular, instalable en la pantalla de inicio)."""

import frappe
from frappe.sessions import get_csrf_token

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/campo"
		raise frappe.Redirect
	context.no_cache = 1
	context.csrf_token = get_csrf_token()
	context.full_name = frappe.utils.get_fullname(frappe.session.user)
	context.version = frappe.get_attr("qsg_pmo.__version__")
	return context
