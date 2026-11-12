# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""App de campo para técnicos: /campo (pensada para celular, instalable en la pantalla de inicio)."""

import frappe
from frappe.sessions import get_csrf_token

no_cache = 1


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/campo"
		if frappe.form_dict.get(
			"app"
		):  # el APK conserva su entrada para volver por perfil tras iniciar sesión
			frappe.local.flags.redirect_location += "%3Fapp%3D1"
		raise frappe.Redirect
	# Desde el APK (?app=1), administradores, despachadores y supervisores abren su tablero;
	# el contratista sigue en su ruta. Sin el parámetro, /campo funciona igual para todos.
	if frappe.form_dict.get("app") and set(frappe.get_roles()) & {
		"System Manager",
		"QSG Gerente",
		"QSG Despachador",
		"QSG Supervisor Contratista",
	}:
		frappe.local.flags.redirect_location = "/despacho"
		raise frappe.Redirect
	context.no_cache = 1
	context.csrf_token = get_csrf_token()
	context.full_name = frappe.utils.get_fullname(frappe.session.user)
	context.version = frappe.get_attr("qsg_pmo.__version__")
	return context
