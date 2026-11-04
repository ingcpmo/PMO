# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Cuántas cuadrillas tiene cada contratista, cuántas están disponibles, su ocupación y su calificación."""

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from qsg_pmo.qsg_pmo.report.ocupacion_de_cuadrillas.ocupacion_de_cuadrillas import data as crew_rows


def execute(filters=None):
	filters = frappe._dict(filters or {})
	day = getdate(filters.date or nowdate())
	return columns(), data(day)


def columns():
	return [
		{
			"fieldname": "contractor",
			"label": _("Contratista"),
			"fieldtype": "Link",
			"options": "QSG Contratista",
			"width": 190,
		},
		{"fieldname": "status", "label": _("Estado"), "fieldtype": "Data", "width": 90},
		{"fieldname": "crews", "label": _("Cuadrillas activas"), "fieldtype": "Int", "width": 110},
		{"fieldname": "available", "label": _("Disponibles hoy"), "fieldtype": "Int", "width": 110},
		{"fieldname": "capacity", "label": _("Capacidad (órdenes)"), "fieldtype": "Int", "width": 110},
		{"fieldname": "scheduled", "label": _("Programadas"), "fieldtype": "Int", "width": 100},
		{"fieldname": "free_slots", "label": _("Cupos libres"), "fieldtype": "Int", "width": 100},
		{"fieldname": "occupation", "label": _("Ocupación %"), "fieldtype": "Percent", "width": 100},
		{"fieldname": "open_orders", "label": _("Órdenes abiertas"), "fieldtype": "Int", "width": 110},
		{"fieldname": "score", "label": _("Puntaje"), "fieldtype": "Percent", "width": 90},
		{"fieldname": "grade", "label": _("Categoría"), "fieldtype": "Data", "width": 80},
		{"fieldname": "insurance_expiry", "label": _("Seguro vence"), "fieldtype": "Date", "width": 110},
	]


def data(day):
	by_contractor = {}
	for r in crew_rows(day, frappe._dict()):
		agg = by_contractor.setdefault(
			r["contractor"],
			{
				"crews": 0,
				"available": 0,
				"capacity": 0,
				"scheduled": 0,
				"free_slots": 0,
				"booked": 0.0,
				"shift": 0.0,
			},
		)
		agg["crews"] += 1
		agg["available"] += 1 if r["availability"] == _("Disponible") else 0
		agg["capacity"] += r["capacity"]
		agg["scheduled"] += r["scheduled"]
		agg["free_slots"] += r["free_slots"]
		if r["availability"] == _("Disponible"):
			agg["booked"] += r["booked_hours"]
			agg["shift"] += r["shift_hours"]
	rows = []
	for c in frappe.get_all(
		"QSG Contratista",
		fields=["name", "status", "current_score", "current_grade", "insurance_expiry"],
		order_by="name",
	):
		agg = by_contractor.get(c.name, {})
		open_orders = frappe.db.count(
			"QSG Orden",
			{
				"contractor": c.name,
				"status": (
					"in",
					("Asignada a contratista", "Programada", "En ruta", "En sitio", "Reprogramada"),
				),
			},
		)
		rows.append(
			{
				"contractor": c.name,
				"status": c.status,
				"crews": agg.get("crews", 0),
				"available": agg.get("available", 0),
				"capacity": agg.get("capacity", 0),
				"scheduled": agg.get("scheduled", 0),
				"free_slots": agg.get("free_slots", 0),
				"occupation": round(agg["booked"] / agg["shift"] * 100, 1) if agg.get("shift") else 0,
				"open_orders": open_orders,
				"score": c.current_score,
				"grade": c.current_grade,
				"insurance_expiry": c.insurance_expiry,
			}
		)
	return rows
