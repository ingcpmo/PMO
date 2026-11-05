# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Capa de datos de la inteligencia operativa.

Lee de la base de datos, llama a las funciones puras de ``qsg_pmo.inteligencia`` y guarda los
resultados. Reutiliza lo que ya existe en la app: la carga de órdenes y cuadrillas del plan de
despacho, la recepción de órdenes de la API (con sus validaciones) y la reasignación de la orden.
"""

import base64
import dataclasses
import hashlib
import json
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import add_days, cint, escape_html, flt, get_datetime, getdate, now_datetime, nowdate

from qsg_pmo.inteligencia import (
	clima,
	ia,
	materiales,
	pendientes,
	rutas,
	solicitudes,
	territorio,
	tracking,
	zonas,
)
from qsg_pmo.inteligencia.optimizacion import Cuadrilla, Opciones, Trabajo, optimizar

EN_CAMPO = ("Programada", "En ruta", "En sitio")
CERRADAS = ("Completada", "No completada", "Cancelada")
DESPACHO = ("System Manager", "QSG Gerente", "QSG Despachador")
SUPERVISION = (*DESPACHO, "QSG Supervisor Contratista")
BODEGA = (*DESPACHO, "QSG Bodega")


# ---------------------------------------------------------------------- configuración
def cfg():
	return frappe.get_cached_doc("QSG Configuracion IA")


def lista(texto) -> list[str]:
	return [x.strip() for x in re.split(r"[\n,;]+", texto or "") if x.strip()]


def config_ia() -> ia.ConfigIA:
	c = frappe.get_single("QSG Configuracion IA")
	return ia.ConfigIA(
		proveedor=c.ai_provider or ia.NINGUNO,
		modelo=c.ai_model or None,
		api_key=c.get_password("ai_api_key", raise_exception=False),
		base_url=c.ai_base_url or None,
		timeout_s=cint(c.ai_timeout) or 60,
		permitir_datos_personales=bool(cint(c.allow_personal_data)),
	)


def proveedor_ia() -> ia.Proveedor:
	try:
		return ia.proveedor(config_ia())
	except ia.ErrorIA as e:
		frappe.log_error(title="QSG IA: proveedor no disponible", message=str(e))
		return ia.Proveedor()


def modelo_viaje(puntos_osrm=None) -> rutas.ModeloViaje:
	q = frappe.get_cached_doc("QSG Configuracion")
	c = cfg()
	m = rutas.ModeloViaje(
		velocidad_kmh=flt(q.average_speed_kmh) or 35.0, factor_vial=flt(q.road_factor) or 1.4
	)
	if cint(c.use_terrain):
		m.factor_montana = flt(c.mountain_factor) or 0.65
		m.minutos_ferry = cint(c.ferry_minutes) or 150
	else:
		m.factor_montana = 1.0
	if cint(c.use_learned_speed):
		m.velocidad_zona = frappe.cache.get_value("qsg_velocidad_zona") or {}
	if puntos_osrm and q.osrm_url:
		try:
			m.matriz = rutas.matriz_osrm(q.osrm_url, puntos_osrm)
		except Exception:
			frappe.log_error(title="QSG: OSRM no respondió; se usa la estimación de viaje")
	return m


def municipio_a_zona() -> dict[str, str]:
	cache = frappe.cache.get_value("qsg_municipio_zona")
	if cache is not None:
		return cache
	salida: dict[str, str] = {}
	for f in frappe.get_all(
		"QSG Zona Municipio", filters={"parenttype": "QSG Zona"}, fields=["municipality", "parent"]
	):
		m = territorio.municipio(f.municipality)
		if m:
			salida.setdefault(m, f.parent)
	frappe.cache.set_value("qsg_municipio_zona", salida, expires_in_sec=3600)
	return salida


def zona_de_punto(lat, lng) -> str | None:
	m = territorio.municipio_cercano(lat, lng)
	return (municipio_a_zona().get(m) or territorio.zona_sugerida(m)) if m else None


def _hora_local(dt):
	"""Fecha con zona horaria -> hora local del sitio sin zona (como guarda Frappe)."""
	if dt is None or dt.tzinfo is None:
		return dt
	return dt.astimezone(ZoneInfo(frappe.utils.get_system_timezone())).replace(tzinfo=None)


def incidencias(desde, hasta) -> dict[str, list[dict]]:
	"""Incidencias activas que se cruzan con el intervalo, por zona."""
	salida = defaultdict(list)
	for f in frappe.get_all(
		"QSG Incidencia Zona",
		filters={"active": 1, "from_datetime": ("<=", hasta)},
		fields=["name", "zone", "impact", "incident_type", "to_datetime", "notes"],
	):
		if f.to_datetime and get_datetime(f.to_datetime) < desde:
			continue
		salida[f.zone].append(f)
	return salida


def _copiar(obj, cls, **extra):
	datos = {f.name: getattr(obj, f.name) for f in dataclasses.fields(obj) if f.init}
	datos.update(extra)
	return cls(**datos)


def _cuadrillas_islas() -> set[str]:
	return set(lista(cfg().island_crews))


def afinidad() -> dict:
	cache = frappe.cache.get_value("qsg_afinidad")
	if cache is None:
		cache = zonas.afinidad(historial(120))
		frappe.cache.set_value("qsg_afinidad", cache, expires_in_sec=6 * 3600)
	return cache


def a_cuadrillas(crews) -> list[Cuadrilla]:
	islas = _cuadrillas_islas()
	af = afinidad()
	salida = []
	for c in crews:
		muni = territorio.municipio_cercano(c.latitude, c.longitude)
		salida.append(
			_copiar(
				c,
				Cuadrilla,
				terreno=territorio.terreno(muni),
				afinidad=af.get(c.crew, {}),
				opera_islas=c.crew in islas or c.zone == "Islas",
			)
		)
	return salida


# ---------------------------------------------------------------------- plan de despacho
def trabajos_y_cuadrillas(plan_doc):
	"""Órdenes y cuadrillas del plan con los datos que usa el optimizador."""
	from qsg_pmo.qsg_pmo.doctype.qsg_plan_de_despacho.qsg_plan_de_despacho import (
		load_crews,
		load_jobs,
		load_settings,
	)

	jobs = load_jobs(plan_doc.plan_date, plan_doc.zone)
	crews = load_crews(plan_doc.plan_date, plan_doc.zone)
	extra = {
		o.name: o
		for o in frappe.get_all(
			"QSG Orden",
			filters={"name": ("in", [j.order for j in jobs] or [""])},
			fields=["name", "municipality", "segment"],
		)
	}
	dia = getdate(plan_doc.plan_date)
	inicio, fin = datetime.combine(dia, time.min), datetime.combine(dia, time.max)
	por_zona = incidencias(inicio, fin)
	trabajos, aproximadas = [], []
	for j in jobs:
		o = extra.get(j.order)
		muni = territorio.municipio(o.municipality) if o else None
		lat, lng = j.latitude, j.longitude
		if (lat is None or lng is None) and muni:
			lat, lng = territorio.ubicacion(muni)
			aproximadas.append(j.order)
		bloqueo = None
		for inc in por_zona.get(j.zone or "", []):
			if inc.impact == "Suspender":
				bloqueo = inc.incident_type
			elif inc.impact == "Sin altura" and "ALTURA" in j.skills and not bloqueo:
				bloqueo = f"{inc.incident_type} (sin trabajo en altura)"
		trabajos.append(
			_copiar(
				j,
				Trabajo,
				latitude=lat,
				longitude=lng,
				segmento=(o.segment if o else None) or "Residencial",
				terreno=territorio.terreno(muni) if muni else territorio.LLANO,
				bloqueo=bloqueo,
			)
		)
	return trabajos, a_cuadrillas(crews), load_settings(), aproximadas


def optimizar_plan(nombre: str) -> dict:
	plan = frappe.get_doc("QSG Plan de Despacho", nombre)
	plan.check_permission("write")
	if plan.status == "Aprobado":
		frappe.throw(_("El plan ya fue aprobado."))
	jobs, crews, settings, aproximadas = trabajos_y_cuadrillas(plan)
	if not jobs:
		frappe.throw(_("No hay órdenes pendientes con cita para {0}.").format(plan.plan_date))
	if not crews:
		frappe.throw(_("No hay cuadrillas activas con punto de salida configurado."))
	c = cfg()
	puntos = [(j.latitude, j.longitude) for j in jobs if j.latitude is not None]
	puntos += [(k.latitude, k.longitude) for k in crews]
	opciones = Opciones(
		factor_empresarial=flt(c.b2b_delay_factor) or 2.0,
		afinidad_minutos=flt(c.affinity_minutes),
		tiempo_max_s=cint(c.optimizer_seconds) or 5,
	)
	r = optimizar(jobs, crews, settings, modelo_viaje(puntos), opciones)

	plan.set("assignments", [])
	plan.set("unassigned", [])
	for a in r.asignaciones:
		fila = dict(vars(a))
		fila.pop("contractor", None)
		plan.append("assignments", fila)
	for u in r.no_asignadas:
		plan.append("unassigned", {"order": u.order, "reason": u.reason[:140]})
	plan.total_assigned = len(r.asignaciones)
	plan.total_unassigned = len(r.no_asignadas)
	plan.status = "Propuesto"
	plan.save()

	notas = list(r.notas)
	if aproximadas:
		notas.append(
			f"{len(aproximadas)} órdenes sin GPS se ubicaron en el centro de su municipio: confirme la dirección."
		)
	carga = defaultdict(int)
	for a in r.asignaciones:
		carga[a.crew] += 1
	maximo = {k.crew: k.max_orders - k.preassigned for k in crews}
	motivos = defaultdict(int)
	for u in r.no_asignadas:
		motivos[u.reason] += 1
	datos = {
		"resumen": r.resumen(),
		"asignadas": r.metricas.asignadas,
		"sin_asignar_por_motivo": dict(motivos),
		"km_por_orden": r.km_por_orden(r.metricas),
		"km_por_orden_motor_reglas": r.km_por_orden(r.referencia),
		"minutos_de_atraso_total": r.metricas.minutos_atraso,
		"cuadrillas_cargadas": sorted(k for k, n in carga.items() if n >= maximo.get(k, 99)),
		"empresariales": sum(1 for j in jobs if j.segmento == "Empresarial"),
		"incidencias": sorted({j.zone for j in jobs if j.bloqueo and j.zone}),
		"notas": notas,
	}
	explicacion = ia.explicar_plan(datos, proveedor_ia())
	plan.add_comment(
		"Comment",
		"<b>Plan optimizado</b><br>"
		+ escape_html(r.resumen())
		+ "<br><br>"
		+ escape_html(explicacion).replace("\n", "<br>"),
	)
	return {
		"assigned": len(r.asignaciones),
		"unassigned": len(r.no_asignadas),
		"resumen": r.resumen(),
		"explicacion": explicacion,
		"usa_reglas": r.usa_reglas,
	}


def al_actualizar_plan(doc, method=None):
	"""Hook de QSG Plan de Despacho: al aprobar, ajusta las solicitudes de materiales al stock del camión.

	Solo si «Descontar el stock del camión» está encendido en QSG Configuracion IA; si no, el plan se
	comporta como siempre.
	"""
	if doc.status != "Aprobado" or not doc.has_value_changed("status"):
		return
	if not cint(cfg().net_material_requests):
		return
	ajustar_solicitudes(doc)


def ajustar_solicitudes(plan) -> list[str]:
	c = cfg()
	serial = set(lista(c.serialized_items))
	mensajes = []
	nombres = set(
		frappe.get_all(
			"QSG Orden",
			filters={"dispatch_plan": plan.name, "material_request": ("is", "set")},
			pluck="material_request",
		)
	)
	for nombre in sorted(nombres):
		mr = frappe.get_doc("Material Request", nombre)
		if mr.docstatus != 0:
			continue
		necesidad: dict[str, float] = defaultdict(float)
		for it in mr.items:
			necesidad[it.item_code] += flt(it.qty)
		camion = _stock(mr.set_warehouse)
		recoger = materiales.plan_bodega(
			{"c": dict(necesidad)},
			{"c": camion},
			margen_pct=flt(c.safety_margin_pct),
			serializados=serial,
			repuesto_serializados=cint(c.spare_serialized),
		)["c"]["recoger"]
		filas = []
		for it in mr.items:
			qty = recoger.pop(it.item_code, 0)
			if qty > 0:
				it.qty = qty
				filas.append(it)
		if filas:
			mr.set("items", filas)
			mr.save(ignore_permissions=True)
			mr.add_comment("Comment", _("Cantidades ajustadas al stock del camión por QSG PMO."))
			mensajes.append(_("{0}: ajustada al stock del camión.").format(nombre))
		else:
			for orden in frappe.get_all("QSG Orden", filters={"material_request": nombre}, pluck="name"):
				frappe.db.set_value("QSG Orden", orden, "material_request", None, update_modified=False)
			frappe.delete_doc("Material Request", nombre, ignore_permissions=True)
			mensajes.append(
				_("{0}: el camión ya tenía todo el material; no hace falta recoger.").format(nombre)
			)
	if mensajes:
		plan.add_comment("Comment", "<br>".join(escape_html(m) for m in mensajes))
	return mensajes


def _stock(almacen) -> dict[str, float]:
	if not almacen:
		return {}
	return {
		b.item_code: flt(b.actual_qty)
		for b in frappe.get_all("Bin", filters={"warehouse": almacen}, fields=["item_code", "actual_qty"])
	}


# ---------------------------------------------------------------------- GPS y estado de cuadrillas
def _momento(valor) -> datetime:
	"""Hora de la lectura enviada por el teléfono (lecturas guardadas sin señal). Se acepta si es de las
	últimas 12 horas y no del futuro; si no, se usa la hora del servidor."""
	ahora = now_datetime()
	if not valor:
		return ahora
	try:
		t = _hora_local(datetime.fromisoformat(str(valor).replace("Z", "+00:00")))
	except ValueError:
		return ahora
	return t if ahora - timedelta(hours=12) <= t <= ahora + timedelta(minutes=2) else ahora


def registrar_ubicacion(
	lat, lng, precision=None, velocidad=None, bateria=None, orden=None, momento=None
) -> dict:
	from qsg_pmo.api import mis_cuadrillas
	from qsg_pmo.seguridad import validacion as v

	c = cfg()
	if not cint(c.gps_enabled):
		return {"ok": False, "motivo": _("El seguimiento GPS está desactivado.")}
	crews = mis_cuadrillas()
	if not crews:
		return {"ok": False, "motivo": _("El usuario no es miembro de una cuadrilla.")}
	lat, lng = v.coordenadas(lat, lng, orden)
	if lat is None:
		frappe.throw(_("Faltan las coordenadas."))
	crew, zona = crews[0], None
	if orden:
		o = frappe.db.get_value("QSG Orden", orden, ["crew", "zone"], as_dict=True)
		if o and o.crew in crews:
			crew, zona = o.crew, o.zone
		else:
			orden = None
	if not orden:
		# La orden en curso de la cuadrilla: primero la que está en sitio, luego la que va en ruta
		for estado in ("En sitio", "En ruta"):
			o = frappe.db.get_value(
				"QSG Orden",
				{"crew": ("in", crews), "status": estado, "appointment_date": nowdate()},
				["name", "crew", "zone"],
				as_dict=True,
			)
			if o:
				orden, crew, zona = o.name, o.crew, o.zone
				break
	frappe.get_doc(
		{
			"doctype": "QSG Ubicacion",
			"crew": crew,
			"user": frappe.session.user,
			"ping_time": _momento(momento),
			"latitude": lat,
			"longitude": lng,
			"accuracy_m": flt(precision) or None,
			"speed_kmh": flt(velocidad) or None,
			"battery": cint(bateria) or None,
			"order": orden,
			"zone": zona or zona_de_punto(lat, lng),
			"source": "App",
		}
	).insert(ignore_permissions=True)
	return {"ok": True, "intervalo": cint(c.gps_interval_s) or 120}


def cuadrillas_visibles() -> list[str] | None:
	"""None = todas; una lista = solo esas (supervisor de contratista)."""
	from qsg_pmo.permissions import contratistas_del_supervisor, es_supervisor_restringido

	user = frappe.session.user
	if not es_supervisor_restringido(user):
		return None
	contratistas = contratistas_del_supervisor(user)
	return frappe.get_all("QSG Cuadrilla", filters={"contractor": ("in", contratistas or [""])}, pluck="name")


def _ventana(dia, valor, defecto):
	from qsg_pmo.qsg_pmo.doctype.qsg_orden.qsg_orden import to_time

	return datetime.combine(dia, to_time(valor) or to_time(defecto))


def estado_cuadrillas(fecha=None, solo: list[str] | None = None) -> list[dict]:
	dia = getdate(fecha or nowdate())
	ahora = now_datetime()
	c = cfg()
	modelo = modelo_viaje()
	filtros = {"active": 1}
	if solo is not None:
		filtros["name"] = ("in", solo or [""])
	crews = frappe.get_all(
		"QSG Cuadrilla",
		filters=filtros,
		fields=["name", "contractor", "base_zone", "start_latitude", "start_longitude", "max_orders_per_day"],
		order_by="name",
	)
	nombres = [x.name for x in crews] or [""]
	pings = defaultdict(list)
	for p in frappe.get_all(
		"QSG Ubicacion",
		filters={"crew": ("in", nombres), "ping_time": (">=", datetime.combine(dia, time.min))},
		fields=["crew", "ping_time", "latitude", "longitude", "accuracy_m", "zone"],
		order_by="ping_time asc",
	):
		pings[p.crew].append(
			tracking.Ping(p.crew, get_datetime(p.ping_time), p.latitude, p.longitude, p.accuracy_m, p.zone)
		)
	visitas, conteo = defaultdict(list), defaultdict(lambda: defaultdict(int))
	for o in frappe.get_all(
		"QSG Orden",
		filters={"appointment_date": dia, "crew": ("in", nombres)},
		fields=["name", "crew", "status", "latitude", "longitude", "window_end", "zone", "route_sequence"],
		order_by="route_sequence asc, window_start asc",
	):
		conteo[o.crew][o.status] += 1
		if o.latitude and o.longitude:
			visitas[o.crew].append(
				tracking.Visita(
					o.name, o.latitude, o.longitude, o.status, _ventana(dia, o.window_end, "17:00:00"), o.zone
				)
			)
	salida = []
	for k in crews:
		base = (k.start_latitude, k.start_longitude) if k.start_latitude else None
		e = tracking.estado(
			k.name,
			pings[k.name],
			visitas[k.name],
			ahora,
			modelo,
			sin_senal_min=cint(c.no_signal_minutes) or 20,
			detenida_min=cint(c.idle_minutes) or 30,
			base=base,
		)
		n = conteo[k.name]
		salida.append(
			{
				"cuadrilla": k.name,
				"contratista": k.contractor,
				"zona": k.base_zone,
				"lat": e.lat,
				"lng": e.lng,
				"base_lat": k.start_latitude or None,
				"base_lng": k.start_longitude or None,
				"ultimo_ping": e.ultimo_ping,
				# Calculado en el servidor: el navegador puede estar en otra zona horaria
				"minutos_sin_gps": round((ahora - e.ultimo_ping).total_seconds() / 60)
				if e.ultimo_ping
				else None,
				"km_hoy": e.km_hoy,
				"minutos_en_movimiento": e.minutos_en_movimiento,
				"siguiente_orden": e.siguiente_orden,
				"llegada_estimada": e.llegada_estimada,
				"ordenes": {
					"total": sum(n.values()),
					"completadas": n["Completada"],
					"no_completadas": n["No completada"],
					"pendientes": sum(n[s] for s in EN_CAMPO),
					"capacidad": k.max_orders_per_day or 6,
				},
				"alertas": [dataclasses.asdict(a) for a in e.alertas],
			}
		)
	return salida


# ---------------------------------------------------------------------- historial y zonas
def historial(dias: int = 90) -> list[zonas.OrdenHistorica]:
	desde = add_days(nowdate(), -int(dias))
	causas = {x.name: x.cause for x in frappe.get_all("QSG Codigo de Cierre", fields=["name", "cause"])}
	duracion = {
		x.name: x.duration_minutes
		for x in frappe.get_all("QSG Tipo de Trabajo", fields=["name", "duration_minutes"])
	}

	def minutos(a, b):
		return (get_datetime(b) - get_datetime(a)).total_seconds() / 60 if a and b else None

	salida = []
	for o in frappe.get_all(
		"QSG Orden",
		filters={"appointment_date": (">=", desde)},
		fields=[
			"name",
			"zone",
			"crew",
			"status",
			"appointment_date",
			"is_rework",
			"sla_status",
			"closure_code",
			"work_type",
			"started_on",
			"finished_on",
			"departed_on",
			"arrived_on",
			"segment",
		],
	):
		salida.append(
			zonas.OrdenHistorica(
				orden=o.name,
				zona=o.zone,
				cuadrilla=o.crew,
				estado=o.status,
				fecha=getdate(o.appointment_date) if o.appointment_date else None,
				es_retrabajo=bool(o.is_rework),
				sla=o.sla_status,
				causa_cierre=causas.get(o.closure_code),
				minutos_estimados=duracion.get(o.work_type),
				minutos_servicio=minutos(o.started_on, o.finished_on),
				minutos_viaje=minutos(o.departed_on, o.arrived_on),
				segmento=o.segment,
			)
		)
	return salida


def ranking_zonas(dias: int = 30) -> dict:
	return zonas.metricas_zona(historial(dias))


def balance_zonas(fecha=None) -> dict:
	from qsg_pmo.qsg_pmo.doctype.qsg_plan_de_despacho.qsg_plan_de_despacho import load_crews

	dia = getdate(fecha or add_days(nowdate(), 1))
	duracion = {
		x.name: x.duration_minutes or 90
		for x in frappe.get_all("QSG Tipo de Trabajo", fields=["name", "duration_minutes"])
	}
	demanda: dict[str, float] = defaultdict(float)
	for o in frappe.get_all(
		"QSG Orden",
		filters={"appointment_date": dia, "status": ("not in", CERRADAS)},
		fields=["zone", "work_type"],
	):
		# Servicio más 25 minutos de viaje promedio por orden
		demanda[o.zone or "Sin zona"] += duracion.get(o.work_type, 90) + 25
	capacidad: dict[str, float] = defaultdict(float)
	por_zona: dict[str, list] = defaultdict(list)
	for k in load_crews(dia):
		minutos = (k.shift_end - k.shift_start).total_seconds() / 60
		capacidad[k.zone or "Sin zona"] += minutos
		por_zona[k.zone or "Sin zona"].append((k.crew, minutos))
	r = zonas.demanda_capacidad(dict(demanda), dict(capacidad), dict(por_zona))
	r["fecha"] = dia
	return r


def mejor_cuadrilla(orden: str, excluir: str | None = None, ignorar_contratista: bool = False) -> dict:
	from qsg_pmo.qsg_pmo.doctype.qsg_plan_de_despacho.qsg_plan_de_despacho import (
		_skills,
		load_crews,
		load_settings,
	)

	o = frappe.get_doc("QSG Orden", orden)
	o.check_permission("read")
	ahora = now_datetime()
	dia = getdate(o.appointment_date) if o.appointment_date else ahora.date()
	muni = territorio.municipio(o.municipality)
	lat, lng, aprox = o.latitude, o.longitude, False
	if not (lat and lng):
		if not muni:
			frappe.throw(_("La orden no tiene coordenadas ni un municipio reconocible."))
		(lat, lng), aprox = territorio.ubicacion(muni), True
	duracion = frappe.db.get_value("QSG Tipo de Trabajo", o.work_type, "duration_minutes") or 90
	job = Trabajo(
		order=o.name,
		latitude=lat,
		longitude=lng,
		window_start=_ventana(dia, o.window_start, "07:00:00"),
		window_end=_ventana(dia, o.window_end, "17:00:00"),
		duration_minutes=duracion,
		skills=_skills("QSG Tipo de Trabajo", o.work_type) if o.work_type else set(),
		priority=o.priority or "Normal",
		zone=o.zone,
		contractor=None if ignorar_contratista else o.contractor,
		segmento=o.segment or "Residencial",
		terreno=territorio.terreno(muni),
	)
	crews = [k for k in a_cuadrillas(load_crews(dia)) if k.crew != excluir]
	nombres = [k.crew for k in crews] or [""]
	hoy = dia == ahora.date()
	ultimo = {}
	if hoy:
		for p in frappe.get_all(
			"QSG Ubicacion",
			filters={"crew": ("in", nombres), "ping_time": (">=", ahora - timedelta(minutes=90))},
			fields=["crew", "ping_time", "latitude", "longitude"],
			order_by="ping_time desc",
		):
			ultimo.setdefault(p.crew, p)
	ocupacion = defaultdict(int)
	en_sitio = {}
	for x in frappe.get_all(
		"QSG Orden",
		filters={
			"appointment_date": dia,
			"crew": ("in", nombres),
			"status": ("!=", "Cancelada"),
			"name": ("!=", o.name),
		},
		fields=["crew", "status", "arrived_on", "work_type"],
	):
		ocupacion[x.crew] += 1
		if x.status == "En sitio" and x.arrived_on:
			fin = get_datetime(x.arrived_on) + timedelta(
				minutes=frappe.get_cached_value("QSG Tipo de Trabajo", x.work_type, "duration_minutes") or 90
			)
			en_sitio[x.crew] = max(fin, en_sitio.get(x.crew, fin))
	en_campo = []
	for k in crews:
		p = ultimo.get(k.crew)
		if p:
			fuente = "GPS"
			plat, plng = p.latitude, p.longitude
			hace = (ahora - get_datetime(p.ping_time)).total_seconds() / 60
		else:
			fuente, plat, plng, hace = "Punto de salida", k.latitude, k.longitude, None
		libre = en_sitio.get(k.crew, ahora if hoy else k.shift_start)
		k.preassigned = 0
		en_campo.append(
			zonas.CuadrillaEnCampo(
				k,
				plat,
				plng,
				libre,
				ordenes_hoy=ocupacion[k.crew],
				fuente_ubicacion=fuente,
				minutos_desde_ubicacion=hace,
			)
		)
	c = cfg()
	opciones = zonas.mejor_cuadrilla(
		job,
		en_campo,
		ahora if hoy else datetime.combine(dia, time(6, 0)),
		load_settings(),
		modelo_viaje(),
		afinidad_minutos=flt(c.affinity_minutes),
	)
	return {"orden": o.name, "ubicacion_aproximada": aprox, "opciones": opciones}


# ---------------------------------------------------------------------- materiales
def plan_materiales(fecha=None) -> dict:
	dia = getdate(fecha or add_days(nowdate(), 1))
	c = cfg()
	ordenes = frappe.get_all(
		"QSG Orden",
		filters={"appointment_date": dia, "crew": ("is", "set"), "status": ("in", EN_CAMPO)},
		fields=["crew", "work_type"],
	)
	kits = {}
	for tipo in {o.work_type for o in ordenes if o.work_type}:
		kits[tipo] = [
			(k.item, k.qty)
			for k in frappe.get_all(
				"QSG Kit Material",
				filters={"parenttype": "QSG Tipo de Trabajo", "parent": tipo},
				fields=["item", "qty"],
			)
		]
	necesidad = materiales.necesidades([(o.crew, o.work_type) for o in ordenes], kits)
	almacenes = {
		k.name: k.warehouse
		for k in frappe.get_all(
			"QSG Cuadrilla", filters={"name": ("in", list(necesidad) or [""])}, fields=["name", "warehouse"]
		)
	}
	camion = {crew: _stock(almacenes.get(crew)) for crew in necesidad}
	central = frappe.db.get_single_value("QSG Configuracion", "central_warehouse")
	plan = materiales.plan_bodega(
		necesidad,
		camion,
		_stock(central) if central else None,
		margen_pct=flt(c.safety_margin_pct),
		serializados=set(lista(c.serialized_items)),
		repuesto_serializados=cint(c.spare_serialized),
	)
	return {
		"fecha": dia,
		"cuadrillas": plan,
		"sin_almacen": sorted(k for k in necesidad if not almacenes.get(k)),
	}


def equipos_estancados() -> list[dict]:
	c = cfg()
	serial = lista(c.serialized_items)
	if not serial:
		return []
	almacenes = {
		k.warehouse: k.name
		for k in frappe.get_all(
			"QSG Cuadrilla", filters={"active": 1, "warehouse": ("is", "set")}, fields=["name", "warehouse"]
		)
	}
	if not almacenes:
		return []
	# Fecha del último movimiento del serial (al entrar al almacén del camión)
	filas = frappe.get_all(
		"Serial No",
		filters={"warehouse": ("in", list(almacenes)), "item_code": ("in", serial)},
		fields=["name", "item_code", "warehouse", "modified"],
	)
	return materiales.equipos_estancados(
		[(f.name, f.item_code, almacenes[f.warehouse], getdate(f.modified)) for f in filas],
		getdate(nowdate()),
		cint(c.stuck_equipment_days) or 7,
	)


# ---------------------------------------------------------------------- pendientes
def pendientes_del_dia(fecha=None, solo: list[str] | None = None) -> dict:
	from qsg_pmo.qsg_pmo.doctype.qsg_orden.qsg_orden import to_time

	dia = getdate(fecha or nowdate())
	ahora = now_datetime()
	hace_7 = ahora - timedelta(days=7)
	codigos = {
		x.name: x for x in frappe.get_all("QSG Codigo de Cierre", fields=["name", "requires_reschedule"])
	}
	tipos = {
		x.name: x
		for x in frappe.get_all("QSG Tipo de Trabajo", fields=["name", "category", "duration_minutes"])
	}
	con_kit = set(
		frappe.get_all(
			"QSG Kit Material", filters={"parenttype": "QSG Tipo de Trabajo"}, pluck="parent", distinct=True
		)
	)
	campos = [
		"name",
		"status",
		"crew",
		"segment",
		"work_type",
		"appointment_date",
		"window_start",
		"window_end",
		"departed_on",
		"arrived_on",
		"finished_on",
		"equipment_serial",
		"customer_signature",
		"closure_code",
		"stock_entry",
		"material_request",
	]
	filtros = {} if solo is None else {"crew": ("in", solo or [""])}
	ordenes = {
		o.name: o
		for o in frappe.get_all("QSG Orden", filters={**filtros, "appointment_date": dia}, fields=campos)
	}
	for o in frappe.get_all(
		"QSG Orden",
		filters={**filtros, "status": ("in", ("Completada", "No completada")), "finished_on": (">=", hace_7)},
		fields=campos,
	):
		ordenes.setdefault(o.name, o)
	nombres = list(ordenes) or [""]
	checklist = defaultdict(list)
	for r in frappe.get_all(
		"QSG Resultado Checklist",
		filters={"parenttype": "QSG Orden", "parent": ("in", nombres)},
		fields=["parent", "description", "item_type", "mandatory", "value", "photo", "compliant"],
		order_by="idx",
	):
		checklist[r.parent].append(
			pendientes.FilaChecklist(
				r.description, r.item_type, bool(r.mandatory), r.value, r.photo, bool(r.compliant)
			)
		)
	materiales_por = defaultdict(int)
	for r in frappe.get_all(
		"QSG Material Consumido",
		filters={"parenttype": "QSG Orden", "parent": ("in", nombres)},
		fields=["parent"],
	):
		materiales_por[r.parent] += 1
	solicitudes_mr = {o.material_request for o in ordenes.values() if o.material_request}
	entregadas = set(
		frappe.get_all(
			"Material Request",
			filters={
				"name": ("in", list(solicitudes_mr) or [""]),
				"status": ("in", ("Transferred", "Issued", "Received")),
			},
			pluck="name",
		)
	)
	almacen = {
		k.name: bool(k.warehouse) for k in frappe.get_all("QSG Cuadrilla", fields=["name", "warehouse"])
	}
	lista_p = []
	for o in ordenes.values():
		d = getdate(o.appointment_date) if o.appointment_date else dia
		t = tipos.get(o.work_type)
		ab = pendientes.OrdenAbierta(
			orden=o.name,
			estado=o.status,
			cuadrilla=o.crew,
			categoria=t.category if t else None,
			segmento=o.segment,
			inicio_ventana=datetime.combine(d, to_time(o.window_start)) if o.window_start else None,
			fin_ventana=datetime.combine(d, to_time(o.window_end)) if o.window_end else None,
			duracion_min=t.duration_minutes if t else None,
			salio=get_datetime(o.departed_on) if o.departed_on else None,
			llego=get_datetime(o.arrived_on) if o.arrived_on else None,
			termino=get_datetime(o.finished_on) if o.finished_on else None,
			checklist=checklist[o.name],
			tiene_kit=o.work_type in con_kit,
			materiales=materiales_por[o.name],
			serial_equipo=o.equipment_serial,
			firma=bool(o.customer_signature),
			codigo_cierre=o.closure_code,
			requiere_reprogramar=bool(
				codigos.get(o.closure_code) and codigos[o.closure_code].requires_reschedule
			),
			almacen_cuadrilla=almacen.get(o.crew, False),
			salida_inventario=o.stock_entry,
			solicitud_materiales=o.material_request,
			solicitud_entregada=o.material_request in entregadas,
		)
		lista_p.extend(pendientes.pendientes(ab, ahora))
	orden_sev = {"Alta": 0, "Media": 1, "Baja": 2}
	lista_p.sort(key=lambda p: (orden_sev.get(p["severidad"], 3), p["orden"]))
	return {"fecha": dia, "pendientes": lista_p, "resumen": pendientes.resumen(lista_p)}


# ---------------------------------------------------------------------- recomendaciones
def recomendar(
	tipo,
	titulo,
	detalle="",
	accion="",
	prioridad="Media",
	orden=None,
	cuadrilla=None,
	zona=None,
	clave=None,
	fuente="Reglas",
):
	"""Crea la recomendación o actualiza la que ya está abierta con la misma clave."""
	clave = (clave or f"{tipo}:{orden or cuadrilla or zona}:{titulo}")[:140]
	ahora = now_datetime()
	abierta = frappe.db.get_value("QSG Recomendacion", {"dedupe_key": clave, "status": "Nueva"})
	if abierta:
		frappe.db.set_value(
			"QSG Recomendacion",
			abierta,
			{"rec_time": ahora, "detail": detalle, "priority": prioridad, "title": titulo[:140]},
			update_modified=False,
		)
		return abierta
	# Lo que alguien ya atendió en las últimas 12 horas no se vuelve a proponer
	if frappe.db.exists(
		"QSG Recomendacion",
		{"dedupe_key": clave, "status": ("!=", "Nueva"), "resolved_on": (">=", ahora - timedelta(hours=12))},
	):
		return None
	doc = frappe.get_doc(
		{
			"doctype": "QSG Recomendacion",
			"rec_time": ahora,
			"rec_type": tipo,
			"priority": prioridad,
			"status": "Nueva",
			"title": titulo[:140],
			"detail": detalle,
			"action": accion,
			"order": orden,
			"crew": cuadrilla,
			"zone": zona,
			"source": fuente,
			"dedupe_key": clave,
		}
	)
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)
	return doc.name


def generar_recomendaciones():
	"""Tracking y pendientes de hoy (cada 15 minutos)."""
	if not cint(cfg().recommendations_enabled):
		return
	hoy = getdate(nowdate())
	for e in estado_cuadrillas(hoy):
		for a in e["alertas"]:
			if a["tipo"] == tracking.TARDE and a["orden"]:
				try:
					alternativas = mejor_cuadrilla(a["orden"], excluir=e["cuadrilla"])["opciones"]
				except Exception:
					alternativas = []
				detalle = a["mensaje"]
				accion = "Avise al cliente."
				if alternativas:
					mejor = alternativas[0]
					detalle += (
						"\nAlternativa: " + mejor["cuadrilla"] + " (" + "; ".join(mejor["razones"]) + ")."
					)
					accion = f"Reasignar a {mejor['cuadrilla']} o avisar al cliente del atraso."
				recomendar(
					"Reasignación",
					f"{a['orden']}: {e['cuadrilla']} llegaría tarde",
					detalle,
					accion,
					"Alta",
					orden=a["orden"],
					cuadrilla=e["cuadrilla"],
					clave=f"TARDE:{a['orden']}:{hoy}",
				)
			else:
				recomendar(
					"Tracking",
					f"{e['cuadrilla']}: {a['tipo']}",
					a["mensaje"],
					prioridad=a["severidad"],
					orden=a.get("orden"),
					cuadrilla=e["cuadrilla"],
					clave=f"{a['tipo']}:{e['cuadrilla']}:{hoy}",
				)
	for p in pendientes_del_dia(hoy)["pendientes"]:
		if p["severidad"] == "Alta":
			recomendar(
				"Pendiente",
				f"{p['orden']}: {p['mensaje'][:110]}",
				p["mensaje"],
				p["accion"],
				"Alta",
				orden=p["orden"],
				clave=f"PEND:{p['codigo']}:{p['orden']}",
			)


def recomendaciones_de_manana():
	"""Zonas, materiales y equipos para el día siguiente (cada hora)."""
	if not cint(cfg().recommendations_enabled):
		return
	manana = getdate(add_days(nowdate(), 1))
	balance = balance_zonas(manana)
	for m in balance["movimientos"]:
		recomendar(
			"Movimiento de cuadrilla",
			f"Mover {m['cuadrilla']} de {m['de']} a {m['a']} el {manana}",
			m["motivo"],
			"Ajuste la zona de la cuadrilla en el plan de mañana o reasigne órdenes.",
			"Media",
			cuadrilla=m["cuadrilla"],
			zona=m["a"],
			clave=f"MOV:{m['cuadrilla']}:{manana}",
		)
	for zona, minutos in balance["sin_cubrir_min"].items():
		recomendar(
			"Zona",
			f"{zona}: faltan {minutos} min de capacidad el {manana}",
			"Ni moviendo cuadrillas vecinas alcanza la capacidad para la demanda de mañana.",
			"Pida una cuadrilla adicional al contratista o reprograme órdenes de baja prioridad.",
			"Alta",
			zona=zona if frappe.db.exists("QSG Zona", zona) else None,
			clave=f"CAP:{zona}:{manana}",
		)
	plan = plan_materiales(manana)
	for crew, p in plan["cuadrillas"].items():
		if p["faltante_central"]:
			faltan = ", ".join(f"{q:g} {i}" for i, q in p["faltante_central"].items())
			recomendar(
				"Materiales",
				f"{crew}: falta material en bodega para mañana",
				f"La bodega central no tiene suficiente: {faltan}.",
				"Reponga inventario o reprograme las órdenes que lo requieren.",
				"Alta",
				cuadrilla=crew,
				clave=f"MATF:{crew}:{manana}",
			)
		if p["devolver"]:
			sobra = ", ".join(f"{q:g} {i}" for i, q in p["devolver"].items())
			recomendar(
				"Materiales",
				f"{crew}: devolver sobrante a bodega",
				f"El camión tiene más de lo que necesita: {sobra}.",
				"Bodega: reciba la devolución al cierre del turno.",
				"Baja",
				cuadrilla=crew,
				clave=f"MATD:{crew}:{manana}",
			)
	for eq in equipos_estancados():
		recomendar(
			"Materiales",
			eq["mensaje"][:140],
			eq["mensaje"],
			"Instalar o devolver a bodega.",
			"Media",
			cuadrilla=eq["cuadrilla"],
			clave=f"EQ:{eq['serial']}",
		)


# ---------------------------------------------------------------------- clima y Traccar
def actualizar_clima():
	c = cfg()
	if not cint(c.nws_enabled):
		return
	try:
		datos = clima.descargar_alertas(c.nws_user_agent or "QSG PMO")
	except Exception:
		frappe.log_error(title="QSG: no se pudo consultar el NWS")
		return
	existentes = set(frappe.get_all("QSG Zona", pluck="name"))
	for inc in clima.incidencias_desde_nws(datos, municipio_a_zona()):
		for zona in inc["zonas"]:
			if zona not in existentes:
				continue
			clave = f"NWS:{inc['id']}:{zona}"[:140]
			if cint(c.nws_auto_incidents) and inc["impacto"] in (clima.SUSPENDER, clima.SIN_ALTURA):
				if not frappe.db.exists("QSG Incidencia Zona", {"external_id": clave}):
					frappe.get_doc(
						{
							"doctype": "QSG Incidencia Zona",
							"zone": zona,
							"incident_type": "Alerta de clima",
							"impact": inc["impacto"],
							"active": 1,
							"from_datetime": now_datetime(),
							"to_datetime": _hora_local(inc["hasta"]),
							"source": "NWS",
							"external_id": clave,
							"notes": inc["titulo"],
						}
					).insert(ignore_permissions=True)
			recomendar(
				"Clima",
				f"{inc['evento']} en {zona}: {inc['impacto']}",
				f"{inc['titulo']}\nMunicipios: {', '.join(inc['municipios']) or 'región'}",
				{
					clima.SUSPENDER: "Suspenda el trabajo de campo en la zona y reprograme.",
					clima.SIN_ALTURA: "No programe trabajo en postes ni escaleras en la zona.",
				}.get(inc["impacto"], "Avise a las cuadrillas y ajuste rutas."),
				"Alta" if inc["impacto"] == clima.SUSPENDER else "Media",
				zona=zona,
				clave=clave,
			)


def sincronizar_traccar():
	c = frappe.get_single("QSG Configuracion IA")
	if not c.traccar_url:
		return
	dispositivos = {}
	for linea in lista(c.traccar_devices):
		if "=" in linea:
			dev, crew = (x.strip() for x in linea.split("=", 1))
			if dev.isdigit() and frappe.db.exists("QSG Cuadrilla", crew):
				dispositivos[int(dev)] = crew
	if not dispositivos:
		return
	credencial = base64.b64encode(
		f"{c.traccar_user or ''}:{c.get_password('traccar_password', raise_exception=False) or ''}".encode()
	).decode()
	req = urllib.request.Request(
		f"{c.traccar_url.rstrip('/')}/api/positions",
		headers={"Authorization": f"Basic {credencial}", "Accept": "application/json"},
	)
	try:
		with urllib.request.urlopen(req, timeout=15) as r:  # nosec B310 - URL configurada por el administrador
			posiciones = json.load(r)
	except Exception:
		frappe.log_error(title="QSG: no se pudo leer Traccar")
		return
	for p in tracking.desde_traccar(posiciones, dispositivos, frappe.utils.get_system_timezone()):
		if frappe.db.exists("QSG Ubicacion", {"crew": p.cuadrilla, "ping_time": p.momento}):
			continue
		frappe.get_doc(
			{
				"doctype": "QSG Ubicacion",
				"crew": p.cuadrilla,
				"ping_time": p.momento,
				"latitude": p.lat,
				"longitude": p.lng,
				"accuracy_m": p.precision_m,
				"zone": zona_de_punto(p.lat, p.lng),
				"source": "Traccar",
			}
		).insert(ignore_permissions=True)


# ---------------------------------------------------------------------- aprendizaje diario
def aprender():
	"""Velocidad real por zona (últimos 30 días de GPS) y afinidad cuadrilla-zona."""
	pings = [
		tracking.Ping(p.crew, get_datetime(p.ping_time), p.latitude, p.longitude, p.accuracy_m, p.zone)
		for p in frappe.get_all(
			"QSG Ubicacion",
			filters={"ping_time": (">=", now_datetime() - timedelta(days=30))},
			fields=["crew", "ping_time", "latitude", "longitude", "accuracy_m", "zone"],
			order_by="crew asc, ping_time asc",
		)
	]
	frappe.cache.set_value("qsg_velocidad_zona", tracking.velocidad_por_zona(pings))
	frappe.cache.delete_value("qsg_afinidad")
	afinidad()


def limpiar_ubicaciones():
	dias = cint(cfg().ping_retention_days) or 90
	frappe.db.delete("QSG Ubicacion", {"ping_time": ("<", now_datetime() - timedelta(days=dias))})


# ---------------------------------------------------------------------- resumen, asistente y solicitudes
def datos_briefing(fecha=None) -> dict:
	from qsg_pmo.api import resumen

	dia = getdate(fecha or nowdate())
	k = resumen(dia)
	estados = estado_cuadrillas(dia)
	alertas = [
		f"{e['cuadrilla']}: {a['mensaje']}"
		for e in estados
		for a in e["alertas"]
		if a["severidad"] in ("Alta", "Media")
	]
	pend = pendientes_del_dia(dia)
	bal = balance_zonas(add_days(dia, 1))
	mat = plan_materiales(add_days(dia, 1))
	inicio = datetime.combine(dia, time.min)
	inc = incidencias(inicio, datetime.combine(dia, time.max))
	return {
		"fecha": dia,
		"kpis": {clave: valor for clave, valor in k.items() if clave != "fecha"},
		"cuadrillas_con_gps": sum(1 for e in estados if e["ultimo_ping"]),
		"km_recorridos_hoy": round(sum(e["km_hoy"] for e in estados), 1),
		"alertas": alertas[:12],
		"pendientes_altos": pend["resumen"]["por_severidad"].get("Alta", 0),
		"pendientes_por_codigo": pend["resumen"]["por_codigo"],
		"movimientos": bal["movimientos"],
		"zonas_manana": {z: v["estado"] for z, v in bal["zonas"].items()},
		"materiales_faltantes": sum(1 for p in mat["cuadrillas"].values() if p["faltante_central"]),
		"incidencias": [f"{z}: {i.incident_type} ({i.impact})" for z, lst in inc.items() for i in lst],
	}


def briefing(fecha=None) -> dict:
	datos = datos_briefing(fecha)
	prov = proveedor_ia()
	return {"texto": ia.briefing(datos, prov), "datos": datos, "proveedor": prov.nombre}


def herramientas() -> list[ia.Herramienta]:
	"""Herramientas de solo lectura para el asistente. Devuelven datos agregados, sin datos personales."""
	from qsg_pmo.api import resumen

	def fecha(nombre="fecha"):
		return {
			"type": "object",
			"properties": {
				nombre: {"anyOf": [{"type": "string", "description": "AAAA-MM-DD"}, {"type": "null"}]}
			},
			"required": [nombre],
			"additionalProperties": False,
		}

	def estado_compacto(p):
		return [
			{k: v for k, v in e.items() if k not in ("lat", "lng")} for e in estado_cuadrillas(p.get("fecha"))
		]

	return [
		ia.Herramienta(
			"resumen_operacion",
			"Contadores de una fecha: órdenes abiertas, SLA en riesgo y vencido, cuadrillas en campo, "
			"programadas, completadas y retrabajos abiertos.",
			lambda p: resumen(p.get("fecha")),
			fecha(),
		),
		ia.Herramienta(
			"estado_cuadrillas",
			"Cada cuadrilla hoy: zona, órdenes (total, completadas, pendientes), km recorridos, siguiente "
			"orden, llegada estimada y alertas (sin señal, detenida, llegará tarde).",
			estado_compacto,
			fecha(),
		),
		ia.Herramienta(
			"pendientes",
			"Pendientes de las órdenes de una fecha y de los cierres de los últimos 7 días: evidencia, "
			"mediciones fuera de rango, materiales, firmas, reprogramaciones, salidas de inventario.",
			lambda p: pendientes_del_dia(p.get("fecha")),
			fecha(),
		),
		ia.Herramienta(
			"ranking_zonas",
			"Rendimiento por zona en los últimos N días: primera visita exitosa, retrabajo, SLA, visitas "
			"fallidas, desvío de duración, productividad, puntaje y observaciones.",
			lambda p: ranking_zonas(int(p.get("dias") or 30)),
			{
				"type": "object",
				"properties": {
					"dias": {"type": "integer", "description": "Días hacia atrás (30 por defecto)"}
				},
				"required": ["dias"],
				"additionalProperties": False,
			},
		),
		ia.Herramienta(
			"balance_zonas",
			"Demanda contra capacidad por zona para una fecha (mañana si es null) y cuadrillas que conviene "
			"mover entre zonas vecinas.",
			lambda p: balance_zonas(p.get("fecha")),
			fecha(),
		),
		ia.Herramienta(
			"plan_materiales",
			"Por cuadrilla, para una fecha (mañana si es null): qué recoger en bodega (neto del camión), qué "
			"devolver y qué falta en la bodega central.",
			lambda p: plan_materiales(p.get("fecha")),
			fecha(),
		),
		ia.Herramienta(
			"mejor_cuadrilla",
			"Cuadrillas que pueden atender una orden (código QSG-ORD-…), de mejor a peor, con minutos de "
			"viaje desde su ubicación actual y las razones.",
			lambda p: mejor_cuadrilla(p["orden"]),
			{
				"type": "object",
				"properties": {"orden": {"type": "string", "description": "Código de la orden"}},
				"required": ["orden"],
				"additionalProperties": False,
			},
		),
		ia.Herramienta(
			"incidencias",
			"Incidencias activas hoy por zona: apagones de LUMA, inundaciones, vías cerradas, alertas del clima.",
			lambda p: {
				z: [{"tipo": i.incident_type, "impacto": i.impact, "notas": i.notes} for i in lst]
				for z, lst in incidencias(now_datetime(), now_datetime()).items()
			},
		),
	]


def preguntar(pregunta: str) -> dict:
	pregunta = (pregunta or "").strip()
	if not pregunta:
		frappe.throw(_("Escriba una pregunta."))
	if len(pregunta) > 2000:
		frappe.throw(_("La pregunta es demasiado larga."))
	prov = proveedor_ia()
	contexto = f"Fecha y hora actual: {now_datetime():%Y-%m-%d %H:%M}.\n\n{pregunta}"
	try:
		respuesta = ia.asistente(contexto, herramientas(), prov)
	except ia.ErrorIA as e:
		respuesta = str(e)
	return {"respuesta": respuesta, "proveedor": prov.nombre}


def catalogo() -> solicitudes.Catalogo:
	return solicitudes.Catalogo(
		tipos=[
			solicitudes.TipoTrabajo(t.name, t.work_type_name, t.technology, t.segment, t.category)
			for t in frappe.get_all(
				"QSG Tipo de Trabajo", fields=["name", "work_type_name", "technology", "segment", "category"]
			)
		],
		municipio_a_zona=municipio_a_zona(),
	)


def interpretar(texto: str) -> dict:
	texto = (texto or "").strip()
	if not texto:
		frappe.throw(_("Pegue el texto de la solicitud."))
	if len(texto) > 20000:
		frappe.throw(_("El texto es demasiado largo."))
	c = config_ia()
	return ia.interpretar_solicitud(
		texto, catalogo(), proveedor_ia(), getdate(nowdate()), c.permitir_datos_personales
	)


def crear_orden_desde_texto(texto: str, customer: str | None = None) -> dict:
	"""Interpreta el texto y crea la orden con la misma recepción que usa Liberty (``recibir_orden``)."""
	from qsg_pmo.api import recibir_orden

	d = interpretar(texto)
	if not d.get("work_type"):
		frappe.throw(_("No se pudo identificar el tipo de trabajo. Complete la orden a mano."))
	campos = {
		k: d[k]
		for k in (
			"external_order_id",
			"priority",
			"work_type",
			"subscriber_name",
			"account_number",
			"phone",
			"address",
			"municipality",
			"zone",
			"appointment_date",
			"window_start",
			"window_end",
		)
		if d.get(k)
	}
	# Sin número del cliente se usa una huella del texto: pegar dos veces el mismo texto no duplica la orden
	campos.setdefault(
		"external_order_id",
		"TXT-" + hashlib.sha1(texto.strip().encode(), usedforsecurity=False).hexdigest()[:10].upper(),
	)
	campos["source"] = "API"
	if customer:
		campos["customer"] = customer
	elif not frappe.db.get_single_value("QSG Configuracion", "default_customer"):
		frappe.throw(
			_(
				"Indique el cliente o configure el «Cliente por defecto» en QSG Configuracion (p. ej. Liberty)."
			)
		)
	r = recibir_orden(**campos)
	r["interpretacion"] = d
	return r


# ---------------------------------------------------------------------- tablero de despacho
def tablero(fecha=None) -> dict:
	dia = getdate(fecha or nowdate())
	solo = cuadrillas_visibles()
	filtros = {"appointment_date": dia}
	ordenes = frappe.get_list(
		"QSG Orden",
		filters=filtros,
		fields=[
			"name",
			"status",
			"priority",
			"sla_status",
			"work_type",
			"segment",
			"municipality",
			"zone",
			"latitude",
			"longitude",
			"window_start",
			"window_end",
			"crew",
			"route_sequence",
		],
		order_by="crew asc, route_sequence asc",
		limit=2000,
	)
	for o in ordenes:
		if not (o.latitude and o.longitude):
			ubic = territorio.ubicacion(o.municipality)
			if ubic:
				o.latitude, o.longitude = ubic
				o.aproximada = 1
	recs = (
		frappe.get_list(
			"QSG Recomendacion",
			filters={"status": "Nueva"},
			fields=[
				"name",
				"rec_time",
				"rec_type",
				"priority",
				"title",
				"detail",
				"action",
				"order",
				"crew",
				"zone",
			],
			order_by="rec_time desc",
			limit=100,
		)
		if frappe.has_permission("QSG Recomendacion", "read")
		else []
	)
	ahora = now_datetime()
	return {
		"fecha": dia,
		"cuadrillas": estado_cuadrillas(dia, solo),
		"ordenes": ordenes,
		"recomendaciones": recs,
		"incidencias": {
			z: [{"tipo": i.incident_type, "impacto": i.impact, "notas": i.notes} for i in lst]
			for z, lst in incidencias(ahora, ahora).items()
		},
		"zonas": {
			z.name: {"lat": z.latitude, "lng": z.longitude}
			for z in frappe.get_all("QSG Zona", fields=["name", "latitude", "longitude"])
		},
		"ia": cfg().ai_provider or ia.NINGUNO,
		"demo": bool(cint(frappe.conf.get("qsg_demo_vivo"))),
	}
