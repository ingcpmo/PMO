# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Reglas de asignación y de calificación, todas por código (sin modelo de lenguaje).

**Asignación.** Para cada petición sin cuadrilla se descartan las que no pueden (habilidad, cupo del
día, turno, ventana, ausencias, zona con incidencia) y las demás se ordenan por un costo en minutos:

    costo = minutos de viaje desde su último GPS (o su punto de salida)
          + atraso sobre el inicio de la ventana
          + órdenes que ya tiene hoy x penalización por carga
          - bonificación si es de la misma zona
          - afinidad con la zona (cómo le ha ido ahí)
          - bonificación si el contratista es categoría A  (+ penalización si es C)

El administrador ve las tres mejores con el desglose y decide; el sistema nunca asigna solo.

**Calificación.** Cada hora se recalcula el puntaje de cada contratista con sus cierres de los últimos
30 días (ventana, primera visita, SLA, evidencia, encuesta, retrabajo) y de ahí sale la categoría:
A desde 90, B desde 75, C por debajo.

**Tiempos.** Minutos para confirmar una orden asignada, para avisar SLA en riesgo, sin señal y detenida.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_days, cint, flt, getdate, nowdate
from frappe.utils.messages import clear_messages

from qsg_pmo.inteligencia import servicio as s

PRIORIDAD = {"Crítica": 0, "Alta": 1, "Normal": 2, "Baja": 3}
SIN_CUADRILLA = ("Recibida", "Asignada a contratista", "Reprogramada")
DIAS_CALIFICACION = 30

# campo: (DocType, etiqueta, unidad, mínimo, máximo, ayuda)
CONFIG, CONFIG_IA = "QSG Configuracion", "QSG Configuracion IA"
REGLAS = {
	"asignacion": {
		"average_speed_kmh": (
			CONFIG,
			"Velocidad media",
			"km/h",
			10,
			90,
			"Para estimar el viaje cuando no hay datos de la zona.",
		),
		"road_factor": (
			CONFIG,
			"Factor de carretera",
			"x",
			1,
			2.5,
			"Cuánto más larga es la carretera que la línea recta.",
		),
		"load_penalty_minutes": (
			CONFIG,
			"Penalización por carga",
			"min por orden",
			0,
			60,
			"Cada orden que ya tiene hoy lo aleja en la lista.",
		),
		"zone_bonus_minutes": (
			CONFIG,
			"Bonificación por misma zona",
			"min",
			0,
			60,
			"Ventaja para quien trabaja en la zona de la petición.",
		),
		"affinity_minutes": (
			CONFIG_IA,
			"Afinidad con la zona",
			"min",
			0,
			60,
			"Ventaja máxima para quien rinde bien en esa zona.",
		),
		"grade_a_bonus_minutes": (
			CONFIG,
			"Bonificación categoría A",
			"min",
			0,
			60,
			"Ventaja para los contratistas mejor calificados.",
		),
		"grade_c_penalty_minutes": (
			CONFIG,
			"Penalización categoría C",
			"min",
			0,
			60,
			"Desventaja para los contratistas con baja calificación.",
		),
	},
	"calificacion": {
		"w_window": (CONFIG, "Llega dentro de la ventana", "%", 0, 100, ""),
		"w_ftr": (CONFIG, "Primera visita exitosa", "%", 0, 100, ""),
		"w_sla": (CONFIG, "Cumple el SLA", "%", 0, 100, ""),
		"w_evidence": (CONFIG, "Evidencia completa", "%", 0, 100, ""),
		"w_rating": (CONFIG, "Encuesta del cliente", "%", 0, 100, ""),
		"w_rework": (CONFIG, "Sin retrabajo", "%", 0, 100, ""),
	},
	"tiempos": {
		"ack_minutes": (
			CONFIG_IA,
			"Confirmar una orden asignada",
			"min",
			1,
			240,
			"Pasado este tiempo sin «Recibida», el tablero avisa.",
		),
		"sla_risk_minutes": (CONFIG, "Avisar SLA en riesgo", "min antes", 10, 1440, ""),
		"no_signal_minutes": (CONFIG_IA, "Sin señal de GPS", "min", 5, 240, ""),
		"idle_minutes": (CONFIG_IA, "Detenida fuera de ruta", "min", 5, 240, ""),
		"geofence_meters": (
			CONFIG,
			"Perímetro de llegada",
			"m",
			50,
			2000,
			"Distancia máxima para marcar «En sitio».",
		),
	},
}


# ---------------------------------------------------------------------- reglas configurables
def reglas() -> dict:
	docs = {CONFIG: frappe.get_cached_doc(CONFIG), CONFIG_IA: frappe.get_cached_doc(CONFIG_IA)}
	meta = {d: frappe.get_meta(d) for d in docs}
	grupos = {}
	for grupo, campos in REGLAS.items():
		grupos[grupo] = []
		for campo, (dt, etiqueta, unidad, minimo, maximo, ayuda) in campos.items():
			valor = docs[dt].get(campo)
			if valor in (None, ""):
				valor = (meta[dt].get_field(campo) or frappe._dict()).get("default")
			grupos[grupo].append(
				{
					"campo": campo,
					"etiqueta": etiqueta,
					"unidad": unidad,
					"min": minimo,
					"max": maximo,
					"ayuda": ayuda,
					"valor": flt(valor),
				}
			)
	return {
		**grupos,
		"categorias": {"A": 90, "B": 75},
		"dias_calificacion": DIAS_CALIFICACION,
		"editable": bool(set(frappe.get_roles()) & {"System Manager", "QSG Gerente"}),
	}


def guardar_reglas(valores) -> dict:
	frappe.only_for(("System Manager", "QSG Gerente"))
	if isinstance(valores, str):
		valores = json.loads(valores)
	permitidos = {campo: definicion for campos in REGLAS.values() for campo, definicion in campos.items()}
	cambios = {}
	for campo, valor in (valores or {}).items():
		if campo not in permitidos:
			frappe.throw(_("{0} no es una regla configurable.").format(campo))
		dt, etiqueta, _unidad, minimo, maximo, _ayuda = permitidos[campo]
		try:
			numero = float(valor)
		except TypeError, ValueError:
			frappe.throw(_("{0}: escriba un número.").format(etiqueta))
		if not minimo <= numero <= maximo:
			frappe.throw(_("{0}: debe estar entre {1} y {2}.").format(etiqueta, minimo, maximo))
		cambios.setdefault(dt, {})[campo] = numero
	for dt, campos in cambios.items():
		doc = frappe.get_single(dt)
		for campo, numero in campos.items():
			doc.set(campo, int(numero) if doc.meta.get_field(campo).fieldtype == "Int" else numero)
		doc.save(ignore_permissions=True)
	return reglas()


# ---------------------------------------------------------------------- peticiones por asignar
def nombres_por_asignar() -> list[str]:
	"""Peticiones abiertas sin cuadrilla, de hoy en adelante o sin fecha (para avisar de las nuevas)."""
	base = {"crew": ("is", "not set"), "status": ("in", SIN_CUADRILLA)}
	return frappe.get_all(
		"QSG Orden", filters={**base, "appointment_date": (">=", nowdate())}, pluck="name"
	) + (frappe.get_all("QSG Orden", filters={**base, "appointment_date": ("is", "not set")}, pluck="name"))


def por_asignar(limite: int = 20) -> dict:
	"""Cada petición sin cuadrilla con sus mejores opciones ya calculadas, la más urgente primero."""
	nombres = nombres_por_asignar()
	ordenes = frappe.get_all(
		"QSG Orden",
		filters={"name": ("in", nombres or [""])},
		fields=[
			"name",
			"external_order_id",
			"priority",
			"status",
			"sla_status",
			"sla_due",
			"work_type",
			"segment",
			"subscriber_name",
			"address",
			"municipality",
			"zone",
			"appointment_date",
			"window_start",
			"window_end",
			"contractor",
			"received_on",
		],
	)
	ordenes.sort(
		key=lambda o: (
			PRIORIDAD.get(o.priority, 2),
			str(o.appointment_date or "9999"),
			str(o.window_start or ""),
			o.name,
		)
	)
	for o in ordenes[: cint(limite) or 20]:
		try:
			r = s.mejor_cuadrilla(o.name, ignorar_contratista=True)
			o.opciones, o.aproximada = r["opciones"], r["ubicacion_aproximada"]
			if not o.opciones:
				o.motivo = _("Nadie con la habilidad puede llegar dentro de la ventana y del turno.")
		except frappe.ValidationError as e:
			o.opciones, o.motivo = [], frappe.utils.strip_html(str(e))
			clear_messages()
	return {"ordenes": ordenes[: cint(limite) or 20], "total": len(ordenes)}


# ---------------------------------------------------------------------- calificación automática
def calificar_contratistas(dias: int = DIAS_CALIFICACION) -> list[dict]:
	"""Recalcula puntaje y categoría de cada contratista con sus cierres de los últimos ``dias`` días.

	Usa la evaluación existente (QSG Evaluacion Contratista) y guarda una por contratista y mes, con
	nombre AUTO-<contratista>-<año>-<mes>; las evaluaciones hechas a mano no se tocan. Un contratista
	sin cierres en el período conserva la calificación que tenía.
	"""
	hoy = getdate(nowdate())
	inicio = add_days(hoy, -(cint(dias) or DIAS_CALIFICACION) + 1)
	resultado = []
	for contratista in frappe.get_all(
		"QSG Contratista", filters={"status": ("!=", "Inactivo")}, pluck="name"
	):
		cierres = frappe.db.count(
			"QSG Orden",
			{
				"contractor": contratista,
				"status": ("in", ("Completada", "No completada")),
				"finished_on": ("between", (inicio, add_days(hoy, 1))),
			},
		)
		if not cierres:
			continue
		nombre = f"AUTO-{contratista}-{hoy:%Y-%m}"[:140]
		if frappe.db.exists("QSG Evaluacion Contratista", nombre):
			doc = frappe.get_doc("QSG Evaluacion Contratista", nombre)
			doc.period_start, doc.period_end = inicio, hoy
			doc.save(ignore_permissions=True)
		else:
			doc = frappe.get_doc(
				{
					"doctype": "QSG Evaluacion Contratista",
					"contractor": contratista,
					"period_start": inicio,
					"period_end": hoy,
				}
			).insert(ignore_permissions=True, set_name=nombre)
		resultado.append(
			{
				"contratista": contratista,
				"puntaje": doc.score,
				"categoria": doc.grade,
				"ordenes": doc.orders_total,
			}
		)
	return resultado


def perfil_contratista(contratista: str) -> dict:
	"""Lo que el administrador revisa antes de asignar: categoría, puntaje y de dónde sale."""
	c = frappe.get_doc("QSG Contratista", contratista)
	c.check_permission("read")
	evaluaciones = frappe.get_all(
		"QSG Evaluacion Contratista",
		filters={"contractor": contratista},
		fields=[
			"name",
			"period_start",
			"period_end",
			"score",
			"grade",
			"orders_total",
			"window_compliance",
			"first_time_right",
			"sla_compliance",
			"evidence_compliance",
			"avg_rating",
			"rework_count",
			"rework_rate",
		],
		order_by="period_end desc, modified desc",
		limit=6,
	)
	return {
		"contratista": c.name,
		"estado": c.status,
		"categoria": c.current_grade,
		"puntaje": c.current_score,
		"contacto": c.contact_name,
		"telefono": c.phone,
		"cuadrillas": frappe.get_all(
			"QSG Cuadrilla",
			filters={"contractor": contratista},
			fields=["name", "base_zone", "active", "max_orders_per_day"],
		),
		"evaluacion": evaluaciones[0] if evaluaciones else None,
		"historial": evaluaciones[1:],
	}
