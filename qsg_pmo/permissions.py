# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Un técnico (rol QSG Tecnico sin otro rol de gestión) solo ve las órdenes de sus cuadrillas.

Aplica en el escritorio, en la API REST (/api/resource) y en la app de campo.
"""

import frappe

MANAGEMENT_ROLES = {
	"System Manager",
	"QSG Gerente",
	"QSG Despachador",
	"QSG Supervisor Contratista",
	"QSG Bodega",
}


def _restricted(user: str) -> bool:
	if user == "Administrator":
		return False
	roles = set(frappe.get_roles(user))
	return "QSG Tecnico" in roles and not (roles & MANAGEMENT_ROLES)


def _crews(user: str) -> list[str]:
	from qsg_pmo.api import mis_cuadrillas

	return mis_cuadrillas(user)


def orden_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if not _restricted(user):
		return ""
	crews = _crews(user)
	if not crews:
		return "1=0"
	return "`tabQSG Orden`.`crew` in ({})".format(", ".join(frappe.db.escape(c) for c in crews))


def orden_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if not _restricted(user):
		return None
	return bool(doc.crew) and doc.crew in _crews(user)
