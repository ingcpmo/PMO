# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Avisos de órdenes asignadas y su confirmación por el contratista.

Cuando el administrador asigna una orden a una cuadrilla, la app de campo del contratista la muestra
como «orden nueva» (con sonido y vibración) hasta que toca «Recibida». El tablero marca las que
pasan del tiempo configurado sin confirmar. Un contratista solo recibe avisos de sus cuadrillas.
"""

import frappe
from frappe import _
from frappe.utils import cint, get_datetime, getdate, now_datetime, nowdate

CAMPOS_ORDEN = [
	"name",
	"crew",
	"modified",
	"subscriber_name",
	"address",
	"municipality",
	"appointment_date",
	"window_start",
	"window_end",
	"work_type",
	"priority",
]


def minutos_para_confirmar() -> int:
	return cint(frappe.get_cached_doc("QSG Configuracion IA").get("ack_minutes")) or 10


def registrar(orden: str, cuadrilla: str) -> str:
	"""Deja el aviso de (orden, cuadrilla) como recién asignado y sin confirmar."""
	name = frappe.db.get_value("QSG Aviso", {"order": orden, "crew": cuadrilla})
	if name:
		frappe.db.set_value(
			"QSG Aviso",
			name,
			{"assigned_on": now_datetime(), "confirmed_on": None, "confirmed_by": None},
		)
		return name
	return (
		frappe.get_doc(
			{"doctype": "QSG Aviso", "order": orden, "crew": cuadrilla, "assigned_on": now_datetime()}
		)
		.insert(ignore_permissions=True)
		.name
	)


def _con_aviso(ordenes: list) -> list:
	"""Agrega a cada orden su aviso; lo crea si la asignación no pasó por ``registrar`` (plan aprobado,
	escritorio), tomando como hora de asignación el último cambio de la orden."""
	if not ordenes:
		return []
	avisos = {
		(a.order, a.crew): a
		for a in frappe.get_all(
			"QSG Aviso",
			filters={"order": ("in", [o.name for o in ordenes])},
			fields=["name", "order", "crew", "assigned_on", "confirmed_on"],
		)
	}
	for o in ordenes:
		a = avisos.get((o.name, o.crew))
		if not a:
			a = frappe.get_doc(
				{"doctype": "QSG Aviso", "order": o.name, "crew": o.crew, "assigned_on": o.modified}
			).insert(ignore_permissions=True)
		o.aviso = a
	return ordenes


def pendientes(cuadrillas: list[str]) -> list[dict]:
	"""Órdenes programadas de hoy en adelante que estas cuadrillas todavía no confirman."""
	if not cuadrillas:
		return []
	ordenes = frappe.get_all(
		"QSG Orden",
		filters={"crew": ("in", cuadrillas), "status": "Programada", "appointment_date": (">=", nowdate())},
		fields=CAMPOS_ORDEN,
		order_by="appointment_date asc, window_start asc",
		limit=50,
	)
	return [
		{
			"orden": o.name,
			"cuadrilla": o.crew,
			"suscriptor": o.subscriber_name,
			"direccion": o.address,
			"municipio": o.municipality,
			"fecha": o.appointment_date,
			"desde": o.window_start,
			"hasta": o.window_end,
			"tipo": o.work_type,
			"prioridad": o.priority,
			"asignada": o.aviso.assigned_on,
		}
		for o in _con_aviso(ordenes)
		if not o.aviso.confirmed_on
	]


def mis_avisos() -> list[dict]:
	from qsg_pmo.api import mis_cuadrillas

	return pendientes(mis_cuadrillas())


def confirmar(orden: str) -> dict:
	"""El contratista toca «Recibida». Solo vale para una orden de su cuadrilla."""
	from qsg_pmo.api import mis_cuadrillas

	crew = frappe.db.get_value("QSG Orden", orden, "crew") if orden else None
	if not crew or crew not in mis_cuadrillas():
		frappe.throw(_("Esta orden no está asignada a su cuadrilla."), frappe.PermissionError)
	name = frappe.db.get_value("QSG Aviso", {"order": orden, "crew": crew})
	if not name:
		name = registrar(orden, crew)
	ahora = now_datetime()
	frappe.db.set_value("QSG Aviso", name, {"confirmed_on": ahora, "confirmed_by": frappe.session.user})
	return {"orden": orden, "recibida": ahora}


def estado_del_dia(fecha=None, cuadrillas: list[str] | None = None) -> dict:
	"""Para el tablero: por orden programada del día, si ya fue recibida y hace cuánto se asignó."""
	filtros = {"appointment_date": getdate(fecha or nowdate()), "status": "Programada", "crew": ("is", "set")}
	if cuadrillas is not None:
		filtros["crew"] = ("in", cuadrillas or [""])
	ahora = now_datetime()
	limite = minutos_para_confirmar()
	estado, tarde = {}, []
	for o in _con_aviso(
		frappe.get_all("QSG Orden", filters=filtros, fields=["name", "crew", "modified"], limit=2000)
	):
		if o.aviso.confirmed_on:
			estado[o.name] = {"recibida": 1}
			continue
		minutos = int((ahora - get_datetime(o.aviso.assigned_on or o.modified)).total_seconds() // 60)
		estado[o.name] = {"recibida": 0, "minutos": minutos}
		if minutos >= limite:
			tarde.append({"orden": o.name, "cuadrilla": o.crew, "minutos": minutos})
	return {"ordenes": estado, "sin_confirmar": sorted(tarde, key=lambda x: -x["minutos"]), "limite": limite}
