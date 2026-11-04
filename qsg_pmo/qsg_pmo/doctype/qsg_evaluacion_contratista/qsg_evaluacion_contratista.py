# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

from datetime import datetime

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate

from qsg_pmo.qsg_pmo.doctype.qsg_orden.qsg_orden import to_time


def pct(part, total):
	return round(100.0 * part / total, 2) if total else 0.0


def grade_for(score):
	if score >= 90:
		return "A"
	if score >= 75:
		return "B"
	return "C"


class QSGEvaluacionContratista(Document):
	def validate(self):
		if getdate(self.period_end) < getdate(self.period_start):
			frappe.throw("La fecha final debe ser posterior a la inicial.")
		self.calculate()

	def on_update(self):
		frappe.db.set_value(
			"QSG Contratista",
			self.contractor,
			{"current_score": self.score, "current_grade": self.grade},
			update_modified=False,
		)

	def calculate(self):
		orders = frappe.get_all(
			"QSG Orden",
			filters={
				"contractor": self.contractor,
				"status": ("in", ("Completada", "No completada")),
				"finished_on": ("between", (self.period_start, add_days(self.period_end, 1))),
			},
			fields=[
				"name",
				"status",
				"closure_code",
				"sla_status",
				"appointment_date",
				"window_start",
				"window_end",
				"arrived_on",
			],
		)
		total = len(orders)
		self.orders_total = total

		in_window = sum(1 for o in orders if arrived_in_window(o))
		with_window = sum(1 for o in orders if o.appointment_date and o.window_end)
		self.window_compliance = pct(in_window, with_window)

		# Primera visita exitosa: no cuentan como falla los cierres atribuibles al cliente
		customer_cause = {
			c.name
			for c in frappe.get_all("QSG Codigo de Cierre", filters={"cause": "Cliente"}, fields=["name"])
		}
		eligible = [
			o for o in orders if not (o.status == "No completada" and o.closure_code in customer_cause)
		]
		self.first_time_right = pct(sum(1 for o in eligible if o.status == "Completada"), len(eligible))

		self.sla_compliance = pct(sum(1 for o in orders if o.sla_status == "Cumplido"), total)

		complete_evidence = 0
		for o in orders:
			rows = frappe.get_all(
				"QSG Resultado Checklist",
				filters={"parent": o.name, "parenttype": "QSG Orden", "mandatory": 1},
				fields=["compliant"],
			)
			if all(r.compliant for r in rows):
				complete_evidence += 1
		self.evidence_compliance = pct(complete_evidence, total)

		ratings = frappe.get_all(
			"QSG Encuesta",
			filters={"order": ("in", [o.name for o in orders] or [""]), "rating": (">", 0)},
			pluck="rating",
		)
		# El campo Rating guarda una fracción 0-1 en Frappe; se lleva a escala 1-5
		self.avg_rating = round(sum(ratings) / len(ratings) * 5, 2) if ratings else 0

		cfg = frappe.get_cached_doc("QSG Configuracion")
		weights = {
			"window_compliance": cfg.w_window or 25,
			"first_time_right": cfg.w_ftr or 25,
			"sla_compliance": cfg.w_sla or 20,
			"evidence_compliance": cfg.w_evidence or 15,
		}
		w_rating = cfg.w_rating or 15
		total_w = sum(weights.values()) + (w_rating if ratings else 0)
		score = sum((self.get(k) or 0) * w for k, w in weights.items())
		if ratings:
			score += (self.avg_rating / 5 * 100) * w_rating
		self.score = round(score / total_w, 2) if total and total_w else 0
		self.grade = grade_for(self.score) if total else None


def arrived_in_window(o):
	if not (o.appointment_date and o.window_end and o.arrived_on):
		return False
	d = getdate(o.appointment_date)
	start = datetime.combine(d, to_time(o.window_start) or to_time("00:00:00"))
	end = datetime.combine(d, to_time(o.window_end))
	return start <= get_datetime(o.arrived_on) <= end
