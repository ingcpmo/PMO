# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""API de QSG PMO.

Dos grupos de métodos, todos bajo ``/api/method/qsg_pmo.api.<método>``:

* **Campo** (app del técnico en el celular): ``mis_ordenes``, ``orden``,
  ``cambiar_estado``, ``guardar_checklist``, ``cerrar``, ``codigos_cierre``.
  Un técnico solo ve y modifica las órdenes de sus cuadrillas.
* **Integración** (Liberty u otros sistemas): ``recibir_orden``,
  ``estado_orden`` y ``resumen``.

Autenticación: sesión (usuario y contraseña) o token
``Authorization: token <api_key>:<api_secret>``.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

# Roles que ven todas las cuadrillas desde la app de campo
SUPERVISOR_ROLES = {"System Manager", "QSG Gerente", "QSG Despachador", "QSG Supervisor Contratista"}
FIELD_STATUSES = ("Programada", "En ruta", "En sitio")
CLOSED = ("Completada", "No completada", "Cancelada")

LIST_FIELDS = [
	"name",
	"status",
	"priority",
	"sla_status",
	"sla_due",
	"work_type",
	"technology",
	"subscriber_name",
	"account_number",
	"phone",
	"address",
	"municipality",
	"latitude",
	"longitude",
	"appointment_date",
	"window_start",
	"window_end",
	"crew",
	"route_sequence",
	"estimated_arrival",
	"is_rework",
]


# ---------------------------------------------------------------------- utilidades
def _parse(value):
	if isinstance(value, str):
		try:
			return json.loads(value)
		except ValueError:
			return value
	return value


def _is_supervisor() -> bool:
	return bool(SUPERVISOR_ROLES & set(frappe.get_roles()))


def mis_cuadrillas(user: str | None = None) -> list[str]:
	"""Cuadrillas en las que el usuario figura como miembro."""
	user = user or frappe.session.user
	return frappe.get_all(
		"QSG Cuadrilla Miembro",
		filters={"user": user, "parenttype": "QSG Cuadrilla"},
		pluck="parent",
		distinct=True,
	)


def _get_order(name: str):
	doc = frappe.get_doc("QSG Orden", name)
	if not _is_supervisor() and doc.crew not in mis_cuadrillas():
		frappe.throw(_("Esta orden no está asignada a su cuadrilla."), frappe.PermissionError)
	return doc


def _order_payload(doc) -> dict:
	data = {f: doc.get(f) for f in LIST_FIELDS}
	data.update(
		{
			"customer": doc.customer,
			"external_order_id": doc.external_order_id,
			"contractor": doc.contractor,
			"network": {
				"hfc_node": doc.hfc_node,
				"tap": doc.tap,
				"olt": doc.olt,
				"pon_port": doc.pon_port,
				"splitter_cto": doc.splitter_cto,
				"equipment_serial": doc.equipment_serial,
			},
			"departed_on": doc.departed_on,
			"arrived_on": doc.arrived_on,
			"finished_on": doc.finished_on,
			"arrival_distance_m": doc.arrival_distance_m,
			"arrival_out_of_range": doc.arrival_out_of_range,
			"closure_code": doc.closure_code,
			"closure_notes": doc.closure_notes,
			"has_signature": bool(doc.customer_signature),
			"checklist": [
				{
					"name": r.name,
					"description": r.description,
					"item_type": r.item_type,
					"mandatory": r.mandatory,
					"unit": r.unit,
					"min_value": r.min_value,
					"max_value": r.max_value,
					"value": r.value,
					"photo": r.photo,
					"compliant": r.compliant,
				}
				for r in doc.checklist
			],
			"materials": [
				{"item": m.item, "qty": m.qty, "serial_no": m.serial_no} for m in doc.materials_used
			],
			"kit": frappe.get_all(
				"QSG Kit Material",
				filters={"parent": doc.work_type, "parenttype": "QSG Tipo de Trabajo"},
				fields=["item", "qty", "uom"],
				order_by="idx",
			)
			if doc.work_type
			else [],
			"events": [
				{
					"time": e.event_time,
					"type": e.event_type,
					"from": e.from_value,
					"to": e.to_value,
					"reason": e.reason,
					"user": e.user,
				}
				for e in doc.events
			],
		}
	)
	return data


# ---------------------------------------------------------------------- campo
@frappe.whitelist()
def yo() -> dict:
	"""Usuario conectado, sus cuadrillas y si puede ver todas."""
	user = frappe.session.user
	return {
		"user": user,
		"full_name": frappe.utils.get_fullname(user),
		"crews": mis_cuadrillas(user),
		"supervisor": _is_supervisor(),
		"hoy": nowdate(),
	}


@frappe.whitelist()
def mis_ordenes(fecha: str | None = None, cuadrilla: str | None = None, incluir_cerradas: int = 1) -> list:
	"""Ruta del día del técnico, en el orden en que debe visitarlas."""
	fecha = getdate(fecha or nowdate())
	crews = mis_cuadrillas()
	if cuadrilla:
		if not _is_supervisor() and cuadrilla not in crews:
			frappe.throw(_("No pertenece a la cuadrilla {0}.").format(cuadrilla), frappe.PermissionError)
		crews = [cuadrilla]
	elif _is_supervisor() and not crews:
		crews = None  # supervisor sin cuadrilla propia: ve todo el día

	filters = {"appointment_date": fecha}
	if crews is not None:
		if not crews:
			return []
		filters["crew"] = ["in", crews]
	statuses = list(FIELD_STATUSES) + (list(CLOSED) if cint(incluir_cerradas) else [])
	filters["status"] = ["in", statuses]
	return frappe.get_all(
		"QSG Orden",
		filters=filters,
		fields=LIST_FIELDS,
		order_by="crew asc, route_sequence asc, window_start asc",
		ignore_permissions=True,
	)


@frappe.whitelist()
def orden(name: str) -> dict:
	"""Detalle completo de una orden: red, checklist, materiales e historial."""
	return _order_payload(_get_order(name))


@frappe.whitelist()
def codigos_cierre() -> list:
	return frappe.get_all(
		"QSG Codigo de Cierre",
		fields=["name", "description", "result", "cause"],
		order_by="result asc, name asc",
	)


@frappe.whitelist(methods=["POST"])
def cambiar_estado(name: str, estado: str, lat: float | None = None, lng: float | None = None) -> dict:
	"""Programada → En ruta → En sitio. En sitio guarda el GPS de llegada."""
	if estado not in ("En ruta", "En sitio"):
		frappe.throw(_("Use «cerrar» para completar o no completar la orden."))
	doc = _get_order(name)
	allowed = {"En ruta": ("Programada",), "En sitio": ("Programada", "En ruta")}
	if doc.status == estado:
		return _order_payload(doc)
	if doc.status not in allowed[estado]:
		frappe.throw(_("No se puede pasar de «{0}» a «{1}».").format(doc.status, estado))
	doc.status = estado
	if estado == "En sitio" and lat and lng:
		doc.arrival_latitude = flt(lat)
		doc.arrival_longitude = flt(lng)
	doc.save(ignore_permissions=True)
	return _order_payload(doc)


@frappe.whitelist(methods=["POST"])
def guardar_checklist(name: str, filas) -> dict:
	"""Guarda valores y fotos. ``filas``: [{name, value?, photo?}].

	La foto se sube antes con ``/api/method/upload_file`` y aquí se envía su ``file_url``.
	"""
	doc = _get_order(name)
	if doc.status in CLOSED:
		frappe.throw(_("La orden ya está cerrada."))
	by_name = {r.name: r for r in doc.checklist}
	for fila in _parse(filas) or []:
		row = by_name.get(fila.get("name"))
		if not row:
			continue
		if "value" in fila:
			row.value = fila.get("value")
		if fila.get("photo"):
			row.photo = fila["photo"]
	doc.save(ignore_permissions=True)
	return _order_payload(doc)


@frappe.whitelist(methods=["POST"])
def cerrar(
	name: str,
	codigo: str,
	notas: str | None = None,
	firma: str | None = None,
	materiales=None,
	lat: float | None = None,
	lng: float | None = None,
) -> dict:
	"""Cierra la orden con un código de cierre. El código decide si queda Completada o No completada.

	Las mismas reglas del escritorio aplican: evidencia obligatoria, mediciones en rango y
	materiales si el tipo de trabajo tiene kit.
	"""
	doc = _get_order(name)
	if doc.status in CLOSED:
		frappe.throw(_("La orden ya está cerrada."))
	result = frappe.db.get_value("QSG Codigo de Cierre", codigo, "result")
	if not result:
		frappe.throw(_("Código de cierre desconocido: {0}").format(codigo))
	if doc.status == "Programada" and lat and lng:
		doc.arrival_latitude, doc.arrival_longitude = flt(lat), flt(lng)
	doc.closure_code = codigo
	doc.closure_notes = notas
	if firma:
		doc.customer_signature = firma
	materiales = _parse(materiales)
	if materiales:
		doc.set("materials_used", [])
		for m in materiales:
			if m.get("item") and flt(m.get("qty")):
				doc.append(
					"materials_used",
					{"item": m["item"], "qty": flt(m["qty"]), "serial_no": m.get("serial_no")},
				)
	doc.status = result
	doc.save(ignore_permissions=True)
	return _order_payload(doc)


# ---------------------------------------------------------------------- integración
@frappe.whitelist(methods=["POST"])
def recibir_orden(**data) -> dict:
	"""Crea o actualiza una orden enviada por el cliente (p. ej. Liberty).

	Se identifica por ``customer`` + ``external_order_id``: si ya existe se actualiza
	mientras no esté en campo ni cerrada. Campos aceptados: los de ``QSG Orden``.
	"""
	frappe.only_for(("System Manager", "QSG Gerente", "QSG Despachador"))
	data.pop("cmd", None)
	customer = data.get("customer") or frappe.db.get_single_value("QSG Configuracion", "default_customer")
	external = data.get("external_order_id")
	if not (customer and external):
		frappe.throw(_("Se requieren «customer» y «external_order_id»."))
	data["customer"] = customer
	allowed = {
		f.fieldname
		for f in frappe.get_meta("QSG Orden").fields
		if f.fieldtype not in ("Table", "Section Break", "Column Break", "Tab Break")
	} - {"status", "crew", "contractor", "dispatch_plan", "closure_code", "is_rework", "rework_of"}
	values = {k: v for k, v in data.items() if k in allowed}

	name = frappe.db.get_value("QSG Orden", {"customer": customer, "external_order_id": external})
	if name:
		doc = frappe.get_doc("QSG Orden", name)
		if doc.status not in ("Recibida", "Asignada a contratista", "Reprogramada"):
			frappe.throw(
				_("La orden {0} ya está en estado {1} y no se puede modificar.").format(name, doc.status)
			)
		doc.update(values)
		doc.save()
		created = False
	else:
		doc = frappe.get_doc({"doctype": "QSG Orden", "source": values.get("source") or "API", **values})
		doc.insert()
		created = True
	return {"name": doc.name, "status": doc.status, "created": created, "sla_due": doc.sla_due}


@frappe.whitelist()
def estado_orden(external_order_id: str, customer: str | None = None) -> dict:
	"""Estado de una orden consultada por el número del cliente."""
	customer = customer or frappe.db.get_single_value("QSG Configuracion", "default_customer")
	name = frappe.db.get_value("QSG Orden", {"customer": customer, "external_order_id": external_order_id})
	if not name:
		frappe.throw(_("No existe la orden {0}.").format(external_order_id), frappe.DoesNotExistError)
	doc = frappe.get_doc("QSG Orden", name)
	doc.check_permission("read")
	return {
		"name": doc.name,
		"external_order_id": doc.external_order_id,
		"status": doc.status,
		"sla_status": doc.sla_status,
		"sla_due": doc.sla_due,
		"appointment_date": doc.appointment_date,
		"window": [str(doc.window_start or ""), str(doc.window_end or "")],
		"contractor": doc.contractor,
		"crew": doc.crew,
		"estimated_arrival": doc.estimated_arrival,
		"finished_on": doc.finished_on,
		"closure_code": doc.closure_code,
		"is_rework": doc.is_rework,
	}


@frappe.whitelist()
def resumen(fecha: str | None = None) -> dict:
	"""Contadores del tablero para pantallas externas o BI."""
	frappe.only_for(("System Manager", "QSG Gerente", "QSG Despachador", "QSG Supervisor Contratista"))
	fecha = getdate(fecha or nowdate())
	count = lambda **f: frappe.db.count("QSG Orden", f)  # noqa: E731
	open_ = ["not in", CLOSED]
	return {
		"fecha": fecha,
		"abiertas": count(status=open_),
		"sla_en_riesgo": count(status=open_, sla_status="En riesgo"),
		"sla_vencido": count(status=open_, sla_status="Vencido"),
		"en_campo": count(status=["in", ("En ruta", "En sitio")]),
		"programadas_hoy": count(appointment_date=fecha),
		"completadas_hoy": frappe.db.count(
			"QSG Orden", {"status": "Completada", "finished_on": ["between", [fecha, fecha]]}
		),
		"retrabajos_abiertos": count(status=open_, is_rework=1),
	}
