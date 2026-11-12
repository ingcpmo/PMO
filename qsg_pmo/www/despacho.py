# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Tablero de despacho: /despacho (mapa de cuadrillas y órdenes, alertas, recomendaciones y asistente)."""

import frappe
from frappe.sessions import get_csrf_token

no_cache = 1
VEN = {"System Manager", "QSG Gerente", "QSG Despachador", "QSG Supervisor Contratista"}
DESPACHAN = {"System Manager", "QSG Gerente", "QSG Despachador"}


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/despacho"
		raise frappe.Redirect
	roles = set(frappe.get_roles())
	if not roles & VEN:
		raise frappe.PermissionError
	context.no_cache = 1
	context.csrf_token = get_csrf_token()
	context.full_name = frappe.utils.get_fullname(frappe.session.user)
	context.version = frappe.get_attr("qsg_pmo.__version__")
	context.despacha = 1 if roles & DESPACHAN else 0
	context.gerencia = 1 if roles & {"System Manager", "QSG Gerente"} else 0
	return context
