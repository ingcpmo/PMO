# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Permisos por fila.

* Un técnico (rol QSG Tecnico sin otro rol de gestión) solo ve las órdenes de sus cuadrillas.
* Un supervisor de contratista (sin otro rol de gestión) solo ve lo de su contratista, según
  sus *User Permission* de QSG Contratista. Si no tiene ninguno asignado, no ve nada, en vez
  de verlo todo (que sería lo que hace Frappe por defecto).

Aplica en el escritorio, en la API REST (/api/resource) y en la app de campo.

Nota: un hook ``has_permission`` de Frappe que devuelve ``None`` niega el acceso, por eso
aquí se devuelve ``True`` cuando la regla no aplica.
"""

import frappe

MANAGEMENT_ROLES = {"System Manager", "QSG Gerente", "QSG Despachador", "QSG Bodega"}


def _roles(user):
	return set(frappe.get_roles(user))


def es_tecnico_restringido(user: str) -> bool:
	if user == "Administrator":
		return False
	roles = _roles(user)
	return "QSG Tecnico" in roles and not (roles & (MANAGEMENT_ROLES | {"QSG Supervisor Contratista"}))


def es_supervisor_restringido(user: str) -> bool:
	if user == "Administrator":
		return False
	roles = _roles(user)
	return "QSG Supervisor Contratista" in roles and not (roles & MANAGEMENT_ROLES)


def contratistas_del_supervisor(user: str) -> list[str]:
	return frappe.get_all(
		"User Permission", filters={"user": user, "allow": "QSG Contratista"}, pluck="for_value"
	)


def _crews(user: str) -> list[str]:
	from qsg_pmo.api import mis_cuadrillas

	return mis_cuadrillas(user)


def _in(column, values):
	return f"{column} in ({', '.join(frappe.db.escape(v) for v in values)})"


# ---------------------------------------------------------------------- QSG Orden
def orden_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if es_tecnico_restringido(user):
		crews = _crews(user)
		return _in("`tabQSG Orden`.`crew`", crews) if crews else "1=0"
	if es_supervisor_restringido(user):
		contractors = contratistas_del_supervisor(user)
		return _in("`tabQSG Orden`.`contractor`", contractors) if contractors else "1=0"
	return ""


def orden_has_permission(doc, ptype=None, user=None):
	user = user or frappe.session.user
	if es_tecnico_restringido(user):
		return bool(doc.crew) and doc.crew in _crews(user)
	if es_supervisor_restringido(user):
		return bool(doc.contractor) and doc.contractor in contratistas_del_supervisor(user)
	return True


# ---------------------------------------------------------------------- documentos con contratista
def _contractor_conditions(doctype, field):
	def conditions(user=None):
		user = user or frappe.session.user
		if not es_supervisor_restringido(user):
			return ""
		contractors = contratistas_del_supervisor(user)
		return _in(f"`tab{doctype}`.`{field}`", contractors) if contractors else "1=0"

	return conditions


def _contractor_permission(field):
	def has_permission(doc, ptype=None, user=None):
		user = user or frappe.session.user
		if not es_supervisor_restringido(user):
			return True
		return doc.get(field) in contratistas_del_supervisor(user)

	return has_permission


contratista_query_conditions = _contractor_conditions("QSG Contratista", "name")
contratista_has_permission = _contractor_permission("name")
cuadrilla_query_conditions = _contractor_conditions("QSG Cuadrilla", "contractor")
cuadrilla_has_permission = _contractor_permission("contractor")
disponibilidad_query_conditions = _contractor_conditions("QSG Disponibilidad", "contractor")
disponibilidad_has_permission = _contractor_permission("contractor")
encuesta_query_conditions = _contractor_conditions("QSG Encuesta", "contractor")
encuesta_has_permission = _contractor_permission("contractor")
evaluacion_query_conditions = _contractor_conditions("QSG Evaluacion Contratista", "contractor")
evaluacion_has_permission = _contractor_permission("contractor")
