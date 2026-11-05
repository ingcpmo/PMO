# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Jornada simulada para demostraciones.

Mueve las cuadrillas de la demostración por GPS, las hace salir, llegar y cerrar órdenes, y a
mitad de la jornada entra una avería urgente sin asignar, para ver en vivo el tablero, las
alertas, la mejor cuadrilla y la app de campo.

Solo funciona en un sitio de demostración: requiere ``"qsg_demo_vivo": 1`` en site_config.json
(lo pone el arranque de GitHub Codespaces). Nunca se activa en producción.
"""

import hashlib

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime, nowdate

from qsg_pmo.assignment.engine import haversine_km
from qsg_pmo.demo import CREWS, CUSTOMER

PASO_KM = 6.0
PASOS_EN_SITIO = 2
URGENTE = "DEMO-URGENTE"
EN_JORNADA = ("Programada", "En ruta", "En sitio")
# Firma de muestra (PNG de 1x1) para los cierres simulados
FIRMA = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
CLAVE = "qsg_demo_vivo"
CONTRASENA_DEMO = "Demo-QSG-2026!"
USUARIOS_DEMO = {
	"gerente@qsg.pr": ("Gerencia", "QSG Gerente"),
	"despacho@qsg.pr": ("Despacho", "QSG Despachador"),
	"supervisor@fibraboricua.pr": ("Supervisor Fibra Boricua", "QSG Supervisor Contratista"),
	"bodega@qsg.pr": ("Bodega", "QSG Bodega"),
}


def habilitado() -> bool:
	return bool(cint(frappe.conf.get("qsg_demo_vivo")))


def _exigir():
	if not habilitado():
		frappe.throw(
			_("La jornada simulada solo está disponible en un sitio de demostración."), frappe.PermissionError
		)


def _clave(nombre: str) -> str:
	return frappe.cache.make_key(f"{CLAVE}:{nombre}")


# ---------------------------------------------------------------------- preparar el sitio
def preparar_sitio() -> dict:
	"""Deja el sitio listo para mostrar: asistente de ERPNext dado por hecho, usuarios por rol y
	turnos de 24 horas en las cuadrillas de la demostración (para probar a cualquier hora)."""
	_exigir()
	frappe.db.sql("update `tabInstalled Application` set is_setup_complete = 1")
	for code, *_resto in CREWS:
		if frappe.db.exists("QSG Cuadrilla", code):
			frappe.db.set_value(
				"QSG Cuadrilla",
				code,
				{"shift_start": "00:00:00", "shift_end": "23:59:00"},
				update_modified=False,
			)
	for email, (nombre, rol) in USUARIOS_DEMO.items():
		if not frappe.db.exists("User", email):
			u = frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": nombre,
					"send_welcome_email": 0,
					"language": "es",
				}
			)
			u.append("roles", {"role": rol})
			u.insert(ignore_permissions=True)
		u = frappe.get_doc("User", email)
		u.new_password = CONTRASENA_DEMO
		u.save(ignore_permissions=True)
	sup = "supervisor@fibraboricua.pr"
	if not frappe.db.exists(
		"User Permission", {"user": sup, "allow": "QSG Contratista", "for_value": "Fibra Boricua LLC"}
	):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": sup,
				"allow": "QSG Contratista",
				"for_value": "Fibra Boricua LLC",
			}
		).insert(ignore_permissions=True)
	frappe.clear_cache()
	return {"usuarios": list(USUARIOS_DEMO), "contrasena": CONTRASENA_DEMO}


# ---------------------------------------------------------------------- jornada
def reiniciar() -> dict:
	"""Trae las órdenes de la demostración a hoy, sin empezar, y borra el GPS de la jornada anterior."""
	_exigir()
	hoy = nowdate()
	if urgente := frappe.db.get_value("QSG Orden", {"customer": CUSTOMER, "external_order_id": URGENTE}):
		frappe.delete_doc("QSG Orden", urgente, force=1, ignore_permissions=True)
	nombres = frappe.get_all(
		"QSG Orden", filters={"customer": CUSTOMER, "external_order_id": ("like", "LPR-%")}, pluck="name"
	)
	for name in nombres:
		crew = frappe.db.get_value("QSG Orden", name, "crew")
		frappe.db.set_value(
			"QSG Orden",
			name,
			{
				"appointment_date": hoy,
				"status": "Programada" if crew else "Recibida",
				"closure_code": None,
				"closure_notes": None,
				"customer_signature": None,
				"equipment_serial": None,
				"departed_on": None,
				"arrived_on": None,
				"started_on": None,
				"finished_on": None,
				"warranty_until": None,
				"arrival_latitude": 0,
				"arrival_longitude": 0,
				"arrival_distance_m": 0,
				"arrival_out_of_range": 0,
			},
			update_modified=False,
		)
		frappe.db.sql(
			"update `tabQSG Resultado Checklist` set value = null, photo = null, compliant = 0 where parent = %s",
			name,
		)
		doc = frappe.get_doc("QSG Orden", name)
		doc.set_sla()
		frappe.db.set_value(
			"QSG Orden", name, {"sla_due": doc.sla_due, "sla_status": doc.sla_status}, update_modified=False
		)
	crews = [c[0] for c in CREWS]
	frappe.db.delete("QSG Ubicacion", {"crew": ("in", crews)})
	frappe.db.delete("QSG Recomendacion", {"status": "Nueva"})
	frappe.cache.delete_keys(CLAVE)
	return {"fecha": hoy, "ordenes": len(nombres)}


def paso() -> dict:
	"""Avanza la jornada: cada cuadrilla sale, avanza por GPS, llega o cierra su orden."""
	_exigir()
	hoy = nowdate()
	n = cint(frappe.cache.incrby(_clave("paso"), 1))
	eventos = []
	# Solo las cuadrillas de la demostración; las demás no se tocan
	en_jornada = {
		"appointment_date": hoy,
		"crew": ("in", [c[0] for c in CREWS]),
		"status": ("in", EN_JORNADA),
	}
	for crew in sorted(set(frappe.get_all("QSG Orden", filters=en_jornada, pluck="crew"))):
		evento = _avanzar(crew, hoy)
		if evento:
			eventos.append(evento)
	if n == 3 and not frappe.db.exists("QSG Orden", {"customer": CUSTOMER, "external_order_id": URGENTE}):
		eventos.append(_averia_urgente(hoy))
	return {"paso": n, "eventos": eventos, "quedan": frappe.db.count("QSG Orden", en_jornada)}


def _avanzar(crew: str, hoy: str) -> str | None:
	ordenes = frappe.get_all(
		"QSG Orden",
		filters={"appointment_date": hoy, "crew": crew, "status": ("in", EN_JORNADA)},
		fields=["name", "status", "latitude", "longitude"],
		order_by="route_sequence asc, window_start asc, name asc",
	)
	if not ordenes:
		return None
	en_sitio = next((o for o in ordenes if o.status == "En sitio"), None)
	if en_sitio:
		if cint(frappe.cache.incrby(_clave(f"sitio:{en_sitio.name}"), 1)) < PASOS_EN_SITIO:
			return f"{crew} trabaja en {en_sitio.name}"
		return _cerrar(crew, en_sitio.name)
	en_ruta = next((o for o in ordenes if o.status == "En ruta"), None)
	destino = en_ruta or ordenes[0]
	if not (destino.latitude and destino.longitude):
		return None
	lat, lng = _posicion(crew)
	if not en_ruta:
		_estado(destino.name, "En ruta")
		_ping(crew, lat, lng, destino.name)
		return f"{crew} sale hacia {destino.name}"
	km = haversine_km(lat, lng, destino.latitude, destino.longitude)
	if km <= PASO_KM:
		_ping(crew, destino.latitude, destino.longitude, destino.name)
		_estado(destino.name, "En sitio", (destino.latitude, destino.longitude))
		return f"{crew} llegó a {destino.name}"
	f = PASO_KM / km
	_ping(crew, lat + (destino.latitude - lat) * f, lng + (destino.longitude - lng) * f, destino.name)
	return f"{crew} va hacia {destino.name}: faltan {km - PASO_KM:.1f} km"


def _posicion(crew: str) -> tuple[float, float]:
	ultimo = frappe.get_all(
		"QSG Ubicacion",
		filters={"crew": crew},
		fields=["latitude", "longitude"],
		order_by="ping_time desc, creation desc",
		limit=1,
	)
	if ultimo:
		return ultimo[0].latitude, ultimo[0].longitude
	return tuple(frappe.db.get_value("QSG Cuadrilla", crew, ["start_latitude", "start_longitude"]))


def _ping(crew: str, lat: float, lng: float, orden: str):
	from qsg_pmo.inteligencia.servicio import zona_de_punto

	usuario = frappe.get_all(
		"QSG Cuadrilla Miembro", filters={"parent": crew, "user": ("is", "set")}, pluck="user", limit=1
	)
	frappe.get_doc(
		{
			"doctype": "QSG Ubicacion",
			"crew": crew,
			"user": usuario[0] if usuario else frappe.session.user,
			"ping_time": now_datetime(),
			"latitude": lat,
			"longitude": lng,
			"accuracy_m": 8,
			"order": orden,
			"zone": zona_de_punto(lat, lng),
			"source": "App",
		}
	).insert(ignore_permissions=True)


def _estado(name: str, estado: str, llegada: tuple[float, float] | None = None):
	doc = frappe.get_doc("QSG Orden", name)
	doc.status = estado
	if llegada:
		doc.arrival_latitude, doc.arrival_longitude = llegada
	doc.save(ignore_permissions=True)


def _medicion(row) -> str:
	if row.min_value and row.max_value:
		return f"{(row.min_value + row.max_value) / 2:g}"
	if row.min_value:
		return f"{row.min_value + 5:g}"
	if row.max_value:
		return f"{row.max_value - 1:g}"
	return "100"


def _cerrar(crew: str, name: str) -> str:
	doc = frappe.get_doc("QSG Orden", name)
	# Una de cada seis visitas sale fallida por cliente ausente, siempre las mismas
	ausente = int(hashlib.sha1(name.encode(), usedforsecurity=False).hexdigest(), 16) % 6 == 0
	if ausente:
		doc.closure_code = "CLI-AUS"
		doc.closure_notes = "Cliente ausente (jornada simulada)."
		doc.status = "No completada"
	else:
		for row in doc.checklist:
			if row.item_type == "Foto":
				row.photo = "/files/qsg-demo-evidencia.jpg"
			elif row.item_type == "Medición":
				row.value = _medicion(row)
			elif row.item_type == "Sí/No":
				row.value = "Sí"
			else:
				row.value = "Trabajo realizado (jornada simulada)"
		if doc.category == "Instalación":
			doc.equipment_serial = f"DEMO-{name[-5:]}"
		doc.customer_signature = FIRMA
		doc.closure_code = "COMP-OK"
		doc.closure_notes = "Cierre de la jornada simulada."
		doc.status = "Completada"
	doc.save(ignore_permissions=True)
	return f"{crew} {'no pudo completar' if ausente else 'completó'} {name}"


def _averia_urgente(hoy: str) -> str:
	from qsg_pmo.inteligencia.servicio import recomendar

	ahora = now_datetime()
	inicio = ahora.replace(minute=0, second=0, microsecond=0)
	fin = min(add_to_date(inicio, hours=5), ahora.replace(hour=23, minute=59, second=0, microsecond=0))
	doc = frappe.get_doc(
		{
			"doctype": "QSG Orden",
			"customer": CUSTOMER,
			"external_order_id": URGENTE,
			"work_type": "FTTH-RECON",
			"priority": "Alta",
			"subscriber_name": "Clínica Familiar (demostración)",
			"address": "Ave. Universidad, Río Piedras",
			"municipality": "San Juan",
			"zone": "Metro",
			"latitude": 18.3994,
			"longitude": -66.0503,
			"appointment_date": hoy,
			"window_start": inicio.strftime("%H:%M:%S"),
			"window_end": fin.strftime("%H:%M:%S"),
			"source": "API",
		}
	).insert(ignore_permissions=True)
	recomendar(
		"Reasignación",
		f"{doc.name}: avería urgente sin asignar",
		"Entró una reconexión FTTH urgente en Río Piedras y no tiene cuadrilla.",
		"Use «Mejor cuadrilla» en la pestaña «Sin asignar» y asígnela.",
		"Alta",
		orden=doc.name,
		zona="Metro",
		clave=f"URG:{doc.name}",
	)
	return f"Entró una avería urgente sin asignar: {doc.name} (Río Piedras)"
