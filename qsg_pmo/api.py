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

Seguridad (ver ``qsg_pmo/seguridad``): cada método valida permisos por fila, limpia el texto,
valida coordenadas, firma y fotos, tiene límite de peticiones por minuto y registra los
intentos rechazados en *QSG Evento Seguridad*.
"""

import json

import frappe
from frappe import _
from frappe.utils import cint, getdate, nowdate

from qsg_pmo.seguridad import validacion as v
from qsg_pmo.seguridad.archivos import validar_contenido
from qsg_pmo.seguridad.eventos import denegar
from qsg_pmo.seguridad.limites import limitar

# Pueden operar cualquier orden desde la app (despacho y gerencia)
DISPATCH_ROLES = {"System Manager", "QSG Gerente", "QSG Despachador"}
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


def _roles() -> set:
	return set(frappe.get_roles())


def mis_cuadrillas(user: str | None = None) -> list[str]:
	"""Cuadrillas en las que el usuario figura como miembro."""
	user = user or frappe.session.user
	return frappe.get_all(
		"QSG Cuadrilla Miembro",
		filters={"user": user, "parenttype": "QSG Cuadrilla"},
		pluck="parent",
		distinct=True,
	)


def _get_order(name: str, para_actuar: bool = False):
	"""Carga la orden si el usuario puede verla (y operarla, si ``para_actuar``)."""
	if not name or not frappe.db.exists("QSG Orden", name):
		frappe.throw(_("No existe la orden {0}.").format(name), frappe.DoesNotExistError)
	doc = frappe.get_doc("QSG Orden", name)
	if not frappe.has_permission("QSG Orden", "read", doc):
		denegar(_("Esta orden no está asignada a su cuadrilla."), f"lectura de {name}", "QSG Orden", name)
	if para_actuar and not (_roles() & DISPATCH_ROLES):
		from qsg_pmo.permissions import contratistas_del_supervisor, es_supervisor_restringido

		user = frappe.session.user
		allowed = doc.crew in mis_cuadrillas(user) or (
			es_supervisor_restringido(user) and doc.contractor in contratistas_del_supervisor(user)
		)
		if not allowed:
			denegar(_("No puede operar esta orden."), f"acción sobre {name}", "QSG Orden", name)
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
@limitar()
def yo() -> dict:
	"""Usuario conectado, sus cuadrillas y la fecha de operación del servidor."""
	user = frappe.session.user
	return {
		"user": user,
		"full_name": frappe.utils.get_fullname(user),
		"crews": mis_cuadrillas(user),
		"supervisor": bool(_roles() & (DISPATCH_ROLES | {"QSG Supervisor Contratista"})),
		"hoy": nowdate(),
	}


@frappe.whitelist()
@limitar()
def mis_ordenes(fecha: str | None = None, cuadrilla: str | None = None, incluir_cerradas: int = 1) -> list:
	"""Ruta del día, en el orden de visita. Cada usuario ve solo lo que sus permisos permiten."""
	fecha = getdate(fecha or nowdate())
	crews = mis_cuadrillas()
	filters = {"appointment_date": fecha}
	if cuadrilla:
		filters["crew"] = cuadrilla
	elif crews:
		filters["crew"] = ["in", crews]
	statuses = list(FIELD_STATUSES) + (list(CLOSED) if cint(incluir_cerradas) else [])
	filters["status"] = ["in", statuses]
	# get_list aplica los permisos por fila (técnico → su cuadrilla, supervisor → su contratista)
	return frappe.get_list(
		"QSG Orden",
		filters=filters,
		fields=LIST_FIELDS,
		order_by="crew asc, route_sequence asc, window_start asc",
		limit_page_length=500,
	)


@frappe.whitelist()
@limitar()
def orden(name: str) -> dict:
	"""Detalle completo de una orden: red, checklist, materiales e historial."""
	return _order_payload(_get_order(name))


@frappe.whitelist()
@limitar()
def codigos_cierre() -> list:
	return frappe.get_all(
		"QSG Codigo de Cierre",
		fields=["name", "description", "result", "cause"],
		order_by="result asc, name asc",
	)


@frappe.whitelist(methods=["POST"])
@limitar()
def cambiar_estado(name: str, estado: str, lat: float | None = None, lng: float | None = None) -> dict:
	"""Programada → En ruta → En sitio. En sitio guarda el GPS de llegada."""
	if estado not in ("En ruta", "En sitio"):
		frappe.throw(_("Use «cerrar» para completar o no completar la orden."))
	doc = _get_order(name, para_actuar=True)
	lat, lng = v.coordenadas(lat, lng, name)
	allowed = {"En ruta": ("Programada",), "En sitio": ("Programada", "En ruta")}
	if doc.status == estado:
		return _order_payload(doc)
	if doc.status not in allowed[estado]:
		frappe.throw(_("No se puede pasar de «{0}» a «{1}».").format(doc.status, estado))
	doc.status = estado
	if estado == "En sitio" and lat is not None:
		doc.arrival_latitude, doc.arrival_longitude = lat, lng
	doc.save(ignore_permissions=True)
	return _order_payload(doc)


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.5)
def subir_foto(name: str) -> dict:
	"""Sube una foto de evidencia a la orden. Solo imágenes reales (JPG, PNG, WEBP, HEIC).

	Se envía como formulario multipart con el campo ``file``. Devuelve ``file_url`` para
	usarlo en ``guardar_checklist``.
	"""
	doc = _get_order(name, para_actuar=True)
	if doc.status in CLOSED:
		frappe.throw(_("La orden ya está cerrada."))
	upload = frappe.request.files.get("file") if frappe.request else None
	if not upload:
		frappe.throw(_("Adjunte la foto en el campo «file»."))
	content = upload.stream.read()
	kind = validar_contenido(content, upload.filename or "foto", "QSG Orden", name)
	ext = "jpg" if kind == "jpg" else kind
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": f"{name}-{frappe.generate_hash(length=8)}.{ext}",
			"attached_to_doctype": "QSG Orden",
			"attached_to_name": name,
			"is_private": 1,
			"content": content,
		}
	)
	f.insert(ignore_permissions=True)
	return {"file_url": f.file_url, "name": f.name}


@frappe.whitelist(methods=["POST"])
@limitar()
def guardar_checklist(name: str, filas) -> dict:
	"""Guarda valores y fotos. ``filas``: [{name, value?, photo?}].

	La foto se sube antes con ``subir_foto`` y aquí se envía su ``file_url``; tiene que ser
	un archivo de esta misma orden.
	"""
	doc = _get_order(name, para_actuar=True)
	if doc.status in CLOSED:
		frappe.throw(_("La orden ya está cerrada."))
	filas = _parse(filas)
	if not isinstance(filas, list) or len(filas) > 200:
		frappe.throw(_("Formato de checklist no válido."))
	by_name = {r.name: r for r in doc.checklist}
	for fila in filas:
		if not isinstance(fila, dict):
			continue
		row = by_name.get(fila.get("name"))
		if not row:
			continue
		if "value" in fila:
			value = fila.get("value")
			row.value = v.numero(value, name) if row.item_type == "Medición" else v.texto(value, 140)
		if fila.get("photo"):
			row.photo = v.foto_de_la_orden(fila["photo"], name)
	doc.save(ignore_permissions=True)
	return _order_payload(doc)


@frappe.whitelist(methods=["POST"])
@limitar()
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
	doc = _get_order(name, para_actuar=True)
	if doc.status in CLOSED:
		frappe.throw(_("La orden ya está cerrada."))
	result = frappe.db.get_value("QSG Codigo de Cierre", codigo, "result")
	if not result:
		frappe.throw(_("Código de cierre desconocido: {0}").format(v.texto(codigo, 40)))
	lat, lng = v.coordenadas(lat, lng, name)
	firma = v.firma(firma, name)
	if doc.status == "Programada" and lat is not None:
		doc.arrival_latitude, doc.arrival_longitude = lat, lng
	doc.closure_code = codigo
	doc.closure_notes = v.texto(notas, 2000)
	if firma:
		doc.customer_signature = firma
	materiales = _parse(materiales)
	if isinstance(materiales, list) and materiales:
		doc.set("materials_used", [])
		for m in materiales[:100]:
			if not isinstance(m, dict) or not m.get("item"):
				continue
			qty = v.numero(m.get("qty"), name)
			if qty and float(qty) > 0:
				doc.append(
					"materials_used",
					{
						"item": v.texto(m["item"], 140),
						"qty": float(qty),
						"serial_no": v.texto(m.get("serial_no"), 140),
					},
				)
	doc.status = result
	doc.save(ignore_permissions=True)
	return _order_payload(doc)


# ---------------------------------------------------------------------- integración
# Campos que el cliente puede enviar; el resto (estado, asignación, cierre, SLA, firma…) es nuestro.
INTAKE_FIELDS = {
	"external_order_id",
	"source",
	"priority",
	"work_type",
	"subscriber_name",
	"account_number",
	"phone",
	"address",
	"municipality",
	"zone",
	"latitude",
	"longitude",
	"appointment_date",
	"window_start",
	"window_end",
	"hfc_node",
	"tap",
	"olt",
	"pon_port",
	"splitter_cto",
	"equipment_serial",
}
TEXT_LIMITS = {"address": 300, "subscriber_name": 140}


@frappe.whitelist(methods=["POST"])
@limitar(factor=5)
def recibir_orden(**data) -> dict:
	"""Crea o actualiza una orden enviada por el cliente (p. ej. Liberty).

	Se identifica por ``customer`` + ``external_order_id``: si ya existe se actualiza
	mientras no esté en campo ni cerrada. Solo se aceptan los campos de ``INTAKE_FIELDS``.
	"""
	frappe.only_for(("System Manager", "QSG Gerente", "QSG Despachador"))
	v.ip_permitida_para_integracion()
	customer = data.get("customer") or frappe.db.get_single_value("QSG Configuracion", "default_customer")
	external = v.texto(data.get("external_order_id"), 140)
	if not (customer and external):
		frappe.throw(_("Se requieren «customer» y «external_order_id»."))
	values = {}
	for k, val in data.items():
		if k not in INTAKE_FIELDS:
			continue
		if k in ("latitude", "longitude"):
			continue
		values[k] = v.texto(val, TEXT_LIMITS.get(k, 140)) if isinstance(val, str) else val
	lat, lng = v.coordenadas(data.get("latitude"), data.get("longitude"))
	if lat is not None:
		values["latitude"], values["longitude"] = lat, lng
	values["external_order_id"] = external
	if values.get("source") not in (None, "Manual", "Importación", "API"):
		values["source"] = "API"

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
		doc = frappe.get_doc(
			{
				"doctype": "QSG Orden",
				"customer": customer,
				"source": values.pop("source", None) or "API",
				**values,
			}
		)
		doc.insert()
		created = True
	return {"name": doc.name, "status": doc.status, "created": created, "sla_due": doc.sla_due}


@frappe.whitelist()
@limitar(factor=5)
def estado_orden(external_order_id: str, customer: str | None = None) -> dict:
	"""Estado de una orden consultada por el número del cliente."""
	customer = customer or frappe.db.get_single_value("QSG Configuracion", "default_customer")
	name = frappe.db.get_value("QSG Orden", {"customer": customer, "external_order_id": external_order_id})
	if not name:
		frappe.throw(
			_("No existe la orden {0}.").format(v.texto(external_order_id, 140)), frappe.DoesNotExistError
		)
	doc = _get_order(name)
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
@limitar()
def resumen(fecha: str | None = None) -> dict:
	"""Contadores del tablero para pantallas externas o BI (cada quien ve lo suyo)."""
	frappe.only_for(("System Manager", "QSG Gerente", "QSG Despachador", "QSG Supervisor Contratista"))
	fecha = getdate(fecha or nowdate())

	def count(**f):
		return len(frappe.get_list("QSG Orden", filters=f, pluck="name", limit_page_length=0))

	open_ = ["not in", CLOSED]
	return {
		"fecha": fecha,
		"abiertas": count(status=open_),
		"sla_en_riesgo": count(status=open_, sla_status="En riesgo"),
		"sla_vencido": count(status=open_, sla_status="Vencido"),
		"en_campo": count(status=["in", ("En ruta", "En sitio")]),
		"programadas_hoy": count(appointment_date=fecha),
		"completadas_hoy": count(status="Completada", finished_on=["between", [fecha, fecha]]),
		"retrabajos_abiertos": count(status=open_, is_rework=1),
	}
