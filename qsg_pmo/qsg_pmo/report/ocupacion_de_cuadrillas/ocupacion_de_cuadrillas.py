# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Agenda, ocupación y disponibilidad de cada cuadrilla en un día."""

from datetime import datetime

import frappe
from frappe import _
from frappe.utils import getdate, nowdate

from qsg_pmo.qsg_pmo.doctype.qsg_orden.qsg_orden import to_time

BUSY = ("Programada", "En ruta", "En sitio", "Completada", "No completada")


def execute(filters=None):
	filters = frappe._dict(filters or {})
	day = getdate(filters.date or nowdate())
	return columns(), data(day, filters)


def columns():
	return [
		{
			"fieldname": "contractor",
			"label": _("Contratista"),
			"fieldtype": "Link",
			"options": "QSG Contratista",
			"width": 170,
		},
		{
			"fieldname": "crew",
			"label": _("Cuadrilla"),
			"fieldtype": "Link",
			"options": "QSG Cuadrilla",
			"width": 130,
		},
		{"fieldname": "zone", "label": _("Zona"), "fieldtype": "Link", "options": "QSG Zona", "width": 90},
		{"fieldname": "skills", "label": _("Habilidades"), "fieldtype": "Data", "width": 200},
		{"fieldname": "availability", "label": _("Disponibilidad"), "fieldtype": "Data", "width": 160},
		{"fieldname": "capacity", "label": _("Capacidad (órdenes)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "scheduled", "label": _("Programadas"), "fieldtype": "Int", "width": 100},
		{"fieldname": "completed", "label": _("Completadas"), "fieldtype": "Int", "width": 100},
		{"fieldname": "free_slots", "label": _("Cupos libres"), "fieldtype": "Int", "width": 90},
		{"fieldname": "shift_hours", "label": _("Horas de turno"), "fieldtype": "Float", "width": 90},
		{"fieldname": "booked_hours", "label": _("Horas agendadas"), "fieldtype": "Float", "width": 100},
		{"fieldname": "occupation", "label": _("Ocupación %"), "fieldtype": "Percent", "width": 100},
		{"fieldname": "agenda", "label": _("Agenda"), "fieldtype": "Data", "width": 320},
	]


def data(day, filters):
	crew_filters = {"active": 1}
	if filters.contractor:
		crew_filters["contractor"] = filters.contractor
	if filters.zone:
		crew_filters["base_zone"] = filters.zone
	crews = frappe.get_all(
		"QSG Cuadrilla",
		filters=crew_filters,
		fields=["name", "contractor", "base_zone", "max_orders_per_day", "shift_start", "shift_end"],
		order_by="contractor, name",
	)
	absences = {
		r.crew: r.reason
		for r in frappe.get_all(
			"QSG Disponibilidad",
			filters={"from_date": ("<=", day), "to_date": (">=", day)},
			fields=["crew", "reason"],
		)
	}
	rows = []
	for c in crews:
		orders = frappe.get_all(
			"QSG Orden",
			filters={"crew": c.name, "appointment_date": day, "status": ("in", BUSY)},
			fields=["name", "status", "work_type", "estimated_arrival", "window_start", "subscriber_name"],
			order_by="route_sequence, estimated_arrival",
		)
		booked_min = sum(
			frappe.get_cached_value("QSG Tipo de Trabajo", o.work_type, "duration_minutes") or 0
			for o in orders
		)
		start = datetime.combine(day, to_time(c.shift_start) or to_time("07:00:00"))
		end = datetime.combine(day, to_time(c.shift_end) or to_time("17:00:00"))
		shift_h = max((end - start).total_seconds() / 3600, 0)
		capacity = c.max_orders_per_day or 0
		skills = frappe.get_all(
			"QSG Habilidad Item", filters={"parenttype": "QSG Cuadrilla", "parent": c.name}, pluck="skill"
		)
		absent = absences.get(c.name)
		agenda = " · ".join(
			f"{(o.estimated_arrival or '').strftime('%H:%M') if o.estimated_arrival else str(o.window_start or '')[:5]} {o.subscriber_name} ({o.status})"
			for o in orders
		)
		rows.append(
			{
				"contractor": c.contractor,
				"crew": c.name,
				"zone": c.base_zone,
				"skills": ", ".join(skills),
				"availability": _("No disponible: {0}").format(absent) if absent else _("Disponible"),
				"capacity": 0 if absent else capacity,
				"scheduled": len(orders),
				"completed": sum(1 for o in orders if o.status == "Completada"),
				"free_slots": 0 if absent else max(capacity - len(orders), 0),
				"shift_hours": round(shift_h, 1),
				"booked_hours": round(booked_min / 60, 1),
				"occupation": 100.0
				if absent
				else (round(booked_min / 60 / shift_h * 100, 1) if shift_h else 0),
				"agenda": agenda,
			}
		)
	return rows
