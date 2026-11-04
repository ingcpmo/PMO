# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, now_datetime

from qsg_pmo.assignment.sla import CLOSED_STATUSES, sla_status

OPEN_FOR_PLANNING = ("Recibida", "Programada", "Reprogramada")


class QSGOrden(Document):
	def validate(self):
		self.validate_unique_external_id()
		self.load_checklist()
		self.evaluate_checklist()
		self.set_timestamps()
		self.validate_closure()
		self.set_sla()

	def validate_unique_external_id(self):
		dup = frappe.db.get_value(
			"QSG Orden",
			{
				"customer": self.customer,
				"external_order_id": self.external_order_id,
				"name": ("!=", self.name),
			},
		)
		if dup:
			frappe.throw(
				_("La orden del cliente {0} ya existe como {1}").format(self.external_order_id, dup),
				frappe.DuplicateEntryError,
			)

	def load_checklist(self):
		"""Copia la plantilla del tipo de trabajo la primera vez."""
		if self.checklist or not self.work_type:
			return
		template = frappe.db.get_value("QSG Tipo de Trabajo", self.work_type, "checklist_template")
		if not template:
			return
		for item in frappe.get_doc("QSG Plantilla Checklist", template).items:
			self.append(
				"checklist",
				{
					"description": item.description,
					"item_type": item.item_type,
					"mandatory": item.mandatory,
					"unit": item.unit,
					"min_value": item.min_value,
					"max_value": item.max_value,
				},
			)

	def evaluate_checklist(self):
		for row in self.checklist:
			row.compliant = 1 if is_row_compliant(row) else 0

	def set_timestamps(self):
		now = now_datetime()
		if self.status == "En sitio" and not self.arrived_on:
			self.arrived_on = now
		if self.status in ("Completada", "No completada") and not self.finished_on:
			self.finished_on = now

	def validate_closure(self):
		if self.status not in ("Completada", "No completada"):
			return
		if not self.closure_code:
			frappe.throw(_("Indique el código de cierre para cerrar la orden."))
		result = frappe.db.get_value("QSG Codigo de Cierre", self.closure_code, "result")
		if result != self.status:
			frappe.throw(
				_("El código de cierre {0} es de resultado «{1}», no coincide con el estado «{2}».").format(
					self.closure_code, result, self.status
				)
			)
		if self.status == "Completada":
			missing = [r.description for r in self.checklist if r.mandatory and not r.compliant]
			if missing:
				frappe.throw(
					_("No se puede completar: faltan o están fuera de rango estos pasos obligatorios:")
					+ "<br>• "
					+ "<br>• ".join(missing)
				)
			has_kit = frappe.db.exists(
				"QSG Kit Material", {"parent": self.work_type, "parenttype": "QSG Tipo de Trabajo"}
			)
			if has_kit and not self.materials_used:
				frappe.throw(_("Registre los materiales o equipos instalados antes de completar."))

	def set_sla(self):
		self.sla_due = compute_sla_due(self)
		stops = False
		if self.closure_code:
			stops = bool(frappe.db.get_value("QSG Codigo de Cierre", self.closure_code, "stops_sla"))
		risk = frappe.db.get_single_value("QSG Configuracion", "sla_risk_minutes") or 120
		self.sla_status = sla_status(
			self.status,
			get_datetime(self.sla_due) if self.sla_due else None,
			now_datetime(),
			finished_on=get_datetime(self.finished_on) if self.finished_on else None,
			risk_minutes=risk,
			stops_sla=stops,
		)


def is_row_compliant(row) -> bool:
	if row.item_type == "Foto":
		return bool(row.photo)
	if row.item_type == "Sí/No":
		return (row.value or "").strip().lower() in ("sí", "si", "yes", "1", "ok")
	if row.item_type == "Texto":
		return bool((row.value or "").strip())
	if row.item_type == "Medición":
		try:
			v = float(str(row.value).replace(",", "."))
		except TypeError, ValueError:
			return False
		# Un límite en 0 se interpreta como «sin límite»
		if row.min_value and v < row.min_value:
			return False
		if row.max_value and v > row.max_value:
			return False
		return True
	return False


def to_time(value) -> time | None:
	if value is None or value == "":
		return None
	if isinstance(value, time):
		return value
	if isinstance(value, timedelta):
		return (datetime.min + value).time()
	return datetime.strptime(str(value).split(".")[0], "%H:%M:%S").time()


def compute_sla_due(doc):
	"""Fin de la ventana de cita; si no hay cita, recepción + horas de SLA del tipo de trabajo."""
	if doc.appointment_date and doc.window_end:
		d = get_datetime(doc.appointment_date).date()
		return datetime.combine(d, to_time(doc.window_end))
	hours = frappe.db.get_value("QSG Tipo de Trabajo", doc.work_type, "sla_hours") if doc.work_type else None
	if hours and doc.received_on:
		return get_datetime(doc.received_on) + timedelta(hours=hours)
	return None


def refresh_open_sla():
	"""Planificador: recalcula el estado SLA de las órdenes abiertas."""
	risk = frappe.db.get_single_value("QSG Configuracion", "sla_risk_minutes") or 120
	now = now_datetime()
	rows = frappe.get_all(
		"QSG Orden",
		filters={"status": ("not in", list(CLOSED_STATUSES)), "sla_due": ("is", "set")},
		fields=["name", "status", "sla_due", "sla_status"],
	)
	for r in rows:
		new = sla_status(r.status, get_datetime(r.sla_due), now, risk_minutes=risk)
		if new != r.sla_status:
			frappe.db.set_value("QSG Orden", r.name, "sla_status", new, update_modified=False)
