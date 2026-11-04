# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

from datetime import datetime, time, timedelta

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate, now_datetime

from qsg_pmo.assignment.engine import haversine_km
from qsg_pmo.assignment.sla import CLOSED_STATUSES, sla_status

# Órdenes que el motor puede planificar
OPEN_FOR_PLANNING = ("Recibida", "Asignada a contratista", "Reprogramada")
# Estados en los que todavía se puede reasignar
REASSIGNABLE = ("Recibida", "Asignada a contratista", "Programada", "En ruta", "Reprogramada")


class QSGOrden(Document):
	def before_insert(self):
		self.detect_rework()

	def validate(self):
		self.validate_unique_external_id()
		self.sync_contractor()
		self.load_checklist()
		self.evaluate_checklist()
		self.set_timestamps()
		self.check_arrival_geofence()
		self.validate_closure()
		self.set_sla()
		self.set_warranty()
		self.log_changes()

	def on_update(self):
		if self.has_value_changed("status") and self.status == "Completada":
			self.create_stock_issue()

	# ------------------------------------------------------------------ recepción
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

	def detect_rework(self):
		"""Si la misma cuenta tuvo una orden completada dentro de la garantía, es un retrabajo
		atribuible al contratista que la ejecutó."""
		if not self.account_number or self.rework_of:
			return
		original = frappe.get_all(
			"QSG Orden",
			filters={
				"customer": self.customer,
				"account_number": self.account_number,
				"status": "Completada",
				"warranty_until": (">=", getdate(self.received_on or now_datetime())),
			},
			fields=["name", "contractor"],
			order_by="finished_on desc",
			limit=1,
		)
		if original:
			self.is_rework = 1
			self.rework_of = original[0].name
			self.rework_contractor = original[0].contractor
			if self.priority in (None, "", "Baja", "Normal"):
				self.priority = "Alta"

	# ------------------------------------------------------------------ asignación
	def sync_contractor(self):
		if self.crew:
			crew_contractor = frappe.db.get_value("QSG Cuadrilla", self.crew, "contractor")
			if self.contractor and self.contractor != crew_contractor:
				frappe.throw(
					_("La cuadrilla {0} pertenece a {1}, no a {2}.").format(
						self.crew, crew_contractor, self.contractor
					)
				)
			self.contractor = crew_contractor
		if self.status == "Recibida" and self.contractor:
			self.status = "Programada" if self.crew else "Asignada a contratista"

	@frappe.whitelist()
	def reassign(self, contractor=None, crew=None, reason=None):
		"""Reasigna la orden a otro contratista y/o cuadrilla, dejando constancia del motivo."""
		if not reason:
			frappe.throw(_("Indique el motivo de la reasignación."))
		if self.status not in REASSIGNABLE:
			frappe.throw(_("No se puede reasignar una orden en estado {0}.").format(self.status))
		if crew:
			contractor = frappe.db.get_value("QSG Cuadrilla", crew, "contractor")
		if not contractor:
			frappe.throw(_("Indique el contratista o la cuadrilla."))
		before = f"{self.contractor or '-'} / {self.crew or '-'}"
		self.contractor = contractor
		self.crew = crew
		self.route_sequence = None
		self.estimated_arrival = None
		self.estimated_finish = None
		self.status = "Programada" if crew else "Asignada a contratista"
		self.add_event("Reasignación", before, f"{contractor} / {crew or '-'}", reason)
		self.flags.assignment_logged = True
		self.save()
		return self.status

	# ------------------------------------------------------------------ evidencia
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

	# ------------------------------------------------------------------ seguimiento
	def set_timestamps(self):
		now = now_datetime()
		if self.status == "En ruta" and not self.departed_on:
			self.departed_on = now
		if self.status == "En sitio":
			self.arrived_on = self.arrived_on or now
			self.started_on = self.started_on or now
		if self.status in ("Completada", "No completada") and not self.finished_on:
			self.finished_on = now

	def check_arrival_geofence(self):
		if not (self.arrival_latitude and self.latitude):
			return
		meters = (
			haversine_km(self.latitude, self.longitude, self.arrival_latitude, self.arrival_longitude) * 1000
		)
		limit = frappe.db.get_single_value("QSG Configuracion", "geofence_meters") or 300
		self.arrival_distance_m = round(meters)
		self.arrival_out_of_range = 1 if meters > limit else 0

	def log_changes(self):
		if self.is_new():
			self.add_event("Estado", None, self.status)
			if self.contractor:
				self.add_event("Asignación", None, f"{self.contractor} / {self.crew or '-'}")
			return
		if self.has_value_changed("status"):
			before = self.get_doc_before_save()
			self.add_event(
				"Estado",
				before.status if before else None,
				self.status,
				self.closure_code if self.status in ("Completada", "No completada") else None,
				self.arrival_latitude if self.status == "En sitio" else None,
				self.arrival_longitude if self.status == "En sitio" else None,
			)
		if not self.flags.assignment_logged and (
			self.has_value_changed("contractor") or self.has_value_changed("crew")
		):
			before = self.get_doc_before_save()
			prev = f"{before.contractor or '-'} / {before.crew or '-'}" if before else None
			self.add_event("Asignación", prev, f"{self.contractor or '-'} / {self.crew or '-'}")

	def add_event(self, event_type, from_value, to_value, reason=None, latitude=None, longitude=None):
		self.append(
			"events",
			{
				"event_time": now_datetime(),
				"event_type": event_type,
				"from_value": from_value,
				"to_value": to_value,
				"reason": reason,
				"user": frappe.session.user,
				"latitude": latitude,
				"longitude": longitude,
			},
		)

	# ------------------------------------------------------------------ cierre
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
		if not self.crew:
			frappe.throw(_("Indique la cuadrilla que ejecutó el trabajo."))
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

	def set_warranty(self):
		if self.status == "Completada" and self.finished_on and not self.warranty_until:
			days = frappe.db.get_single_value("QSG Configuracion", "warranty_days") or 30
			self.warranty_until = add_days(getdate(self.finished_on), days)

	def create_stock_issue(self):
		"""Descarga del almacén de la cuadrilla los materiales usados (borrador para que bodega lo valide)."""
		if self.stock_entry or not self.materials_used:
			return
		warehouse = frappe.db.get_value("QSG Cuadrilla", self.crew, "warehouse")
		if not warehouse:
			return
		company = frappe.db.get_value("Warehouse", warehouse, "company")
		serials = ", ".join(r.serial_no for r in self.materials_used if r.serial_no)
		try:
			se = frappe.get_doc(
				{
					"doctype": "Stock Entry",
					"stock_entry_type": "Material Issue",
					"purpose": "Material Issue",
					"company": company,
					"from_warehouse": warehouse,
					"remarks": _("Consumo de la orden {0} ({1}). Seriales: {2}").format(
						self.name, self.external_order_id, serials or "-"
					),
					"items": [
						{"item_code": r.item, "qty": r.qty, "s_warehouse": warehouse}
						for r in self.materials_used
					],
				}
			)
			se.insert(ignore_permissions=True)
			self.db_set("stock_entry", se.name, update_modified=False)
		except Exception as e:
			self.add_comment("Comment", _("No se pudo crear la salida de inventario: {0}").format(e))


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


@frappe.whitelist()
def assign_contractor(names, contractor, reason=None):
	"""Asignación masiva de órdenes a un contratista (desde la lista)."""
	names = frappe.parse_json(names) if isinstance(names, str) else names
	done = []
	for name in names:
		doc = frappe.get_doc("QSG Orden", name)
		if doc.status not in REASSIGNABLE:
			continue
		if doc.contractor and doc.contractor != contractor:
			doc.reassign(contractor=contractor, reason=reason or _("Asignación masiva"))
		else:
			doc.contractor = contractor
			doc.save()
		done.append(name)
	return done


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
