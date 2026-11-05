# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

from collections import defaultdict
from datetime import datetime

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime, getdate

from qsg_pmo.assignment.engine import Crew, Job, Settings, plan
from qsg_pmo.qsg_pmo.doctype.qsg_orden.qsg_orden import OPEN_FOR_PLANNING, to_time


class QSGPlandeDespacho(Document):
	@frappe.whitelist()
	def generate_proposal(self):
		if self.status == "Aprobado":
			frappe.throw(_("El plan ya fue aprobado."))
		if self.engine != "Reglas":
			frappe.throw(
				_("El motor {0} se habilita en una próxima versión. Use «Reglas».").format(self.engine)
			)
		jobs = load_jobs(self.plan_date, self.zone)
		crews = load_crews(self.plan_date, self.zone)
		if not jobs:
			frappe.throw(_("No hay órdenes pendientes con cita para {0}.").format(self.plan_date))
		if not crews:
			frappe.throw(_("No hay cuadrillas activas con punto de salida configurado."))
		assigned, unassigned = plan(jobs, crews, load_settings())
		self.set("assignments", [])
		self.set("unassigned", [])
		for a in assigned:
			row = dict(a.__dict__)
			row.pop("contractor", None)
			self.append("assignments", row)
		for u in unassigned:
			self.append("unassigned", u.__dict__)
		self.total_assigned = len(assigned)
		self.total_unassigned = len(unassigned)
		self.status = "Propuesto"
		self.save()
		return {"assigned": len(assigned), "unassigned": len(unassigned)}

	@frappe.whitelist()
	def approve(self):
		if self.status != "Propuesto":
			frappe.throw(_("Genere la propuesta antes de aprobar."))
		for a in self.assignments:
			order = frappe.get_doc("QSG Orden", a.order)
			if order.status not in OPEN_FOR_PLANNING:
				continue
			order.crew = a.crew
			order.contractor = frappe.db.get_value("QSG Cuadrilla", a.crew, "contractor")
			order.dispatch_plan = self.name
			order.route_sequence = a.sequence
			order.estimated_arrival = a.estimated_arrival
			order.estimated_finish = a.estimated_finish
			order.status = "Programada"
			order.save()
		requests = create_material_requests(self)
		for a in self.assignments:
			if a.crew in requests:
				frappe.db.set_value(
					"QSG Orden", a.order, "material_request", requests[a.crew], update_modified=False
				)
		self.status = "Aprobado"
		self.save()
		return {"material_requests": list(requests.values())}


def load_settings() -> Settings:
	cfg = frappe.get_cached_doc("QSG Configuracion")
	s = Settings()
	for f in ("average_speed_kmh", "road_factor", "load_penalty_minutes", "zone_bonus_minutes"):
		if cfg.get(f):
			setattr(s, f, cfg.get(f))
	return s


def _skills(parenttype, parent):
	return {
		r.skill
		for r in frappe.get_all(
			"QSG Habilidad Item", filters={"parenttype": parenttype, "parent": parent}, fields=["skill"]
		)
	}


def load_jobs(plan_date, zone=None):
	filters = {"appointment_date": plan_date, "status": ("in", OPEN_FOR_PLANNING)}
	if zone:
		filters["zone"] = zone
	rows = frappe.get_all(
		"QSG Orden",
		filters=filters,
		fields=[
			"name",
			"latitude",
			"longitude",
			"window_start",
			"window_end",
			"work_type",
			"priority",
			"sla_due",
			"zone",
			"contractor",
		],
		order_by="name",
	)
	d = getdate(plan_date)
	jobs = []
	for r in rows:
		wt = frappe.get_cached_value("QSG Tipo de Trabajo", r.work_type, "duration_minutes") or 90
		ws = to_time(r.window_start) or to_time("07:00:00")
		we = to_time(r.window_end) or to_time("17:00:00")
		jobs.append(
			Job(
				order=r.name,
				latitude=r.latitude if r.latitude else None,
				longitude=r.longitude if r.longitude else None,
				window_start=datetime.combine(d, ws),
				window_end=datetime.combine(d, we),
				duration_minutes=wt,
				skills=_skills("QSG Tipo de Trabajo", r.work_type),
				priority=r.priority or "Normal",
				sla_due=get_datetime(r.sla_due) if r.sla_due else None,
				zone=r.zone,
				contractor=r.contractor,
			)
		)
	return jobs


def load_crews(plan_date, zone=None):
	filters = {"active": 1, "start_latitude": ("!=", 0)}
	if zone:
		filters["base_zone"] = zone
	rows = frappe.get_all(
		"QSG Cuadrilla",
		filters=filters,
		fields=[
			"name",
			"start_latitude",
			"start_longitude",
			"shift_start",
			"shift_end",
			"max_orders_per_day",
			"base_zone",
			"contractor",
		],
		order_by="name",
	)
	d = getdate(plan_date)
	unavailable = crews_unavailable(d)
	cfg = frappe.get_cached_doc("QSG Configuracion")
	crews = []
	for r in rows:
		contractor = frappe.get_doc("QSG Contratista", r.contractor)
		if contractor.status != "Activo":
			continue
		if contractor.insurance_expiry and getdate(contractor.insurance_expiry) < d:
			continue
		if r.name in unavailable:
			continue
		bonus = 0.0
		if contractor.current_grade == "A":
			bonus = cfg.grade_a_bonus_minutes or 0
		elif contractor.current_grade == "C":
			bonus = -(cfg.grade_c_penalty_minutes or 0)
		crews.append(
			Crew(
				crew=r.name,
				latitude=r.start_latitude,
				longitude=r.start_longitude,
				shift_start=datetime.combine(d, to_time(r.shift_start) or to_time("07:00:00")),
				shift_end=datetime.combine(d, to_time(r.shift_end) or to_time("17:00:00")),
				skills=_skills("QSG Cuadrilla", r.name),
				max_orders=r.max_orders_per_day or 6,
				zone=r.base_zone,
				contractor=r.contractor,
				quality_bonus_minutes=bonus,
				preassigned=already_scheduled(r.name, d),
			)
		)
	return crews


def crews_unavailable(day):
	"""Cuadrillas con una ausencia registrada que cubre el día."""
	return set(
		frappe.get_all(
			"QSG Disponibilidad",
			filters={"from_date": ("<=", day), "to_date": (">=", day)},
			pluck="crew",
		)
	)


def already_scheduled(crew, day):
	"""Órdenes ya programadas para la cuadrilla ese día (de planes anteriores o asignación manual)."""
	return frappe.db.count(
		"QSG Orden",
		{"crew": crew, "appointment_date": day, "status": ("in", ("Programada", "En ruta", "En sitio"))},
	)


def create_material_requests(plan_doc):
	"""Crea una solicitud de transferencia de materiales por cuadrilla, desde la bodega central
	hacia el almacén de la cuadrilla, sumando los kits de los tipos de trabajo asignados."""
	central = frappe.db.get_single_value("QSG Configuracion", "central_warehouse")
	if not central:
		return {}
	needs = defaultdict(lambda: defaultdict(float))
	for a in plan_doc.assignments:
		work_type = frappe.db.get_value("QSG Orden", a.order, "work_type")
		for k in frappe.get_all(
			"QSG Kit Material",
			filters={"parenttype": "QSG Tipo de Trabajo", "parent": work_type},
			fields=["item", "qty"],
		):
			needs[a.crew][k.item] += k.qty
	created = {}
	company = frappe.db.get_value("Warehouse", central, "company")
	for crew, items in needs.items():
		target = frappe.db.get_value("QSG Cuadrilla", crew, "warehouse")
		if not target or not items:
			continue
		mr = frappe.get_doc(
			{
				"doctype": "Material Request",
				"material_request_type": "Material Transfer",
				"company": company,
				"transaction_date": plan_doc.plan_date,
				"schedule_date": plan_doc.plan_date,
				"set_from_warehouse": central,
				"set_warehouse": target,
				"items": [
					{
						"item_code": item,
						"qty": qty,
						"schedule_date": plan_doc.plan_date,
						"from_warehouse": central,
						"warehouse": target,
					}
					for item, qty in items.items()
				],
			}
		)
		mr.insert()
		mr.add_comment(
			"Comment",
			_("Generada por el plan de despacho {0} para la cuadrilla {1}").format(plan_doc.name, crew),
		)
		created[crew] = mr.name
	return created
