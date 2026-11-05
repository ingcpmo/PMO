# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Liquidación del período: lo que se factura al cliente y lo que se paga a cada contratista por tipo de trabajo.

Cuenta las órdenes Completadas y las No completadas cuyo código de cierre es cobrable (p. ej. cliente ausente).
Los retrabajos en garantía no se pagan al contratista responsable.
"""

import frappe
from frappe import _
from frappe.utils import add_days, getdate, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	start = getdate(filters.from_date or add_days(nowdate(), -30))
	end = getdate(filters.to_date or nowdate())
	return columns(), data(start, end, filters)


def columns():
	return [
		{
			"fieldname": "contractor",
			"label": _("Contratista"),
			"fieldtype": "Link",
			"options": "QSG Contratista",
			"width": 180,
		},
		{
			"fieldname": "work_type",
			"label": _("Tipo de trabajo"),
			"fieldtype": "Link",
			"options": "QSG Tipo de Trabajo",
			"width": 160,
		},
		{"fieldname": "completed", "label": _("Completadas"), "fieldtype": "Int", "width": 100},
		{"fieldname": "billable_failed", "label": _("Visitas cobrables"), "fieldtype": "Int", "width": 110},
		{"fieldname": "rework", "label": _("Retrabajos (no se pagan)"), "fieldtype": "Int", "width": 120},
		{"fieldname": "rate", "label": _("Tarifa cliente"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "customer_total", "label": _("Total cliente"), "fieldtype": "Currency", "width": 120},
		{"fieldname": "contractor_rate", "label": _("Pago unitario"), "fieldtype": "Currency", "width": 110},
		{
			"fieldname": "contractor_total",
			"label": _("Total contratista"),
			"fieldtype": "Currency",
			"width": 120,
		},
		{"fieldname": "margin", "label": _("Margen"), "fieldtype": "Currency", "width": 110},
	]


def data(start, end, filters):
	conditions = {
		"status": ("in", ("Completada", "No completada")),
		"finished_on": ("between", (start, add_days(end, 1))),
		"contractor": ("is", "set"),
	}
	if filters.contractor:
		conditions["contractor"] = filters.contractor
	orders = frappe.get_all(
		"QSG Orden",
		filters=conditions,
		fields=["contractor", "work_type", "status", "closure_code", "is_rework", "rework_contractor"],
	)
	billable_codes = set(frappe.get_all("QSG Codigo de Cierre", filters={"billable": 1}, pluck="name"))
	groups = {}
	for o in orders:
		g = groups.setdefault(
			(o.contractor, o.work_type), {"completed": 0, "billable_failed": 0, "rework": 0}
		)
		own_rework = o.is_rework and o.rework_contractor == o.contractor
		if own_rework:
			g["rework"] += 1
			continue
		if o.status == "Completada":
			g["completed"] += 1
		elif o.closure_code in billable_codes:
			g["billable_failed"] += 1
	rows = []
	for (contractor, work_type), g in sorted(groups.items()):
		rate, c_rate = frappe.get_cached_value("QSG Tipo de Trabajo", work_type, ["rate", "contractor_rate"])
		units = g["completed"] + g["billable_failed"]
		customer_total = units * (rate or 0)
		contractor_total = units * (c_rate or 0)
		rows.append(
			{
				"contractor": contractor,
				"work_type": work_type,
				**g,
				"rate": rate,
				"customer_total": customer_total,
				"contractor_rate": c_rate,
				"contractor_total": contractor_total,
				"margin": customer_total - contractor_total,
			}
		)
	return rows
