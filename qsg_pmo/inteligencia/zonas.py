"""Rendimiento por zona y decisiones de reasignación.

* ``metricas_zona``: primera visita exitosa, retrabajo, SLA, visitas fallidas, desvío de duración y
  productividad de cada zona, con un puntaje 0-100 y observaciones accionables.
* ``afinidad``: qué tan bien rinde cada cuadrilla en cada zona (0 a 1), con suavizado para que
  pocas órdenes no den conclusiones fuertes.
* ``demanda_capacidad``: minutos de trabajo pedidos contra minutos disponibles por zona, y qué
  cuadrillas mover desde zonas vecinas holgadas.
* ``mejor_cuadrilla``: para una orden nueva (una avería urgente), las cuadrillas que pueden llegar,
  ordenadas por costo, usando su ubicación GPS actual.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from qsg_pmo.assignment.engine import Settings, haversine_km
from qsg_pmo.inteligencia.optimizacion import elegible
from qsg_pmo.inteligencia.rutas import ModeloViaje
from qsg_pmo.inteligencia.territorio import LLANO, ZONAS_VECINAS

CERRADAS = ("Completada", "No completada", "Cancelada")


@dataclass
class OrdenHistorica:
	"""Lo mínimo de una orden pasada para medir. No lleva datos personales del suscriptor."""

	orden: str
	zona: str | None
	cuadrilla: str | None
	estado: str
	fecha: date | None = None
	es_retrabajo: bool = False
	sla: str | None = None
	causa_cierre: str | None = None
	minutos_estimados: float | None = None
	minutos_servicio: float | None = None
	minutos_viaje: float | None = None
	segmento: str | None = None


def _pct(a: float, b: float) -> float | None:
	return round(a / b * 100, 1) if b else None


def metricas_zona(ordenes: list[OrdenHistorica]) -> dict[str, dict]:
	por_zona: dict[str, list[OrdenHistorica]] = {}
	for o in ordenes:
		por_zona.setdefault(o.zona or "Sin zona", []).append(o)

	resultado = {}
	for zona, lista in por_zona.items():
		cerradas = [o for o in lista if o.estado in ("Completada", "No completada")]
		completadas = [o for o in cerradas if o.estado == "Completada"]
		retrabajos = [o for o in lista if o.es_retrabajo]
		primera = [o for o in completadas if not o.es_retrabajo]
		con_sla = [o for o in cerradas if o.sla in ("Cumplido", "Incumplido")]
		fallidas_cliente = [
			o for o in cerradas if o.estado == "No completada" and o.causa_cierre == "Cliente"
		]
		fallidas_red = [o for o in cerradas if o.estado == "No completada" and o.causa_cierre == "Red"]
		desvios = [
			o.minutos_servicio / o.minutos_estimados
			for o in completadas
			if o.minutos_servicio and o.minutos_estimados
		]
		viajes = [o.minutos_viaje for o in cerradas if o.minutos_viaje]
		dias_cuadrilla = {(o.cuadrilla, o.fecha) for o in completadas if o.cuadrilla and o.fecha}
		resultado[zona] = {
			"ordenes": len(lista),
			"cerradas": len(cerradas),
			"completadas": len(completadas),
			"primera_visita_pct": _pct(len(primera), len(cerradas)),
			"retrabajo_pct": _pct(len(retrabajos), len(lista)),
			"sla_cumplido_pct": _pct(sum(1 for o in con_sla if o.sla == "Cumplido"), len(con_sla)),
			"fallidas_cliente_pct": _pct(len(fallidas_cliente), len(cerradas)),
			"fallidas_red_pct": _pct(len(fallidas_red), len(cerradas)),
			"duracion_real_vs_estimada": round(statistics.median(desvios), 2) if desvios else None,
			"viaje_promedio_min": round(statistics.mean(viajes), 1) if viajes else None,
			"completadas_por_cuadrilla_dia": round(len(completadas) / len(dias_cuadrilla), 2)
			if dias_cuadrilla
			else None,
		}

	productividad_max = max((m["completadas_por_cuadrilla_dia"] or 0 for m in resultado.values()), default=0)
	for m in resultado.values():
		m["puntaje"] = _puntaje(m, productividad_max)
		m["observaciones"] = _observaciones(m)
	return dict(sorted(resultado.items(), key=lambda kv: -(kv[1]["puntaje"] or 0)))


def _puntaje(m: dict, productividad_max: float) -> float | None:
	if not m["cerradas"]:
		return None
	partes = [
		(30, (m["primera_visita_pct"] or 0) / 100),
		(25, (m["sla_cumplido_pct"] if m["sla_cumplido_pct"] is not None else 100) / 100),
		(20, (m["completadas_por_cuadrilla_dia"] or 0) / productividad_max if productividad_max else 0),
		(15, 1 - (m["retrabajo_pct"] or 0) / 100),
		(10, 1 - (m["fallidas_cliente_pct"] or 0) / 100),
	]
	return round(sum(peso * valor for peso, valor in partes), 1)


def _observaciones(m: dict) -> list[str]:
	obs = []
	if (m["fallidas_cliente_pct"] or 0) >= 10:
		obs.append(
			f"{m['fallidas_cliente_pct']} % de visitas fallidas por el cliente: confirme la cita el día "
			"antes (llamada o WhatsApp) y avise cuando la cuadrilla salga."
		)
	if (m["fallidas_red_pct"] or 0) >= 8:
		obs.append(
			f"{m['fallidas_red_pct']} % de visitas fallidas por la red: escale a Liberty los puntos de "
			"acceso sin puertos o sin señal antes de programar."
		)
	if (m["retrabajo_pct"] or 0) >= 5:
		obs.append(
			f"Retrabajo de {m['retrabajo_pct']} %: revise la evidencia de cierre y las mediciones de "
			"las cuadrillas de esta zona."
		)
	ratio = m["duracion_real_vs_estimada"]
	if ratio and ratio >= 1.2:
		obs.append(
			f"El trabajo tarda {round((ratio - 1) * 100)} % más de lo estimado: suba la duración de los "
			"tipos de trabajo para esta zona o asigne menos órdenes por cuadrilla."
		)
	elif ratio and ratio <= 0.8:
		obs.append("El trabajo tarda menos de lo estimado: hay espacio para una orden más por cuadrilla.")
	if (m["sla_cumplido_pct"] or 100) < 85:
		obs.append(f"SLA cumplido en {m['sla_cumplido_pct']} %: priorice esta zona en el plan de mañana.")
	return obs


def afinidad(ordenes: list[OrdenHistorica], experiencia_media: int = 10) -> dict[str, dict[str, float]]:
	"""cuadrilla -> zona -> 0..1. Éxito = completada en primera visita, sin retrabajo y con SLA cumplido.

	La tasa se suaviza hacia la media general y se multiplica por la experiencia (n / (n + k)), así una
	cuadrilla con 2 órdenes buenas en una zona no supera a una con 40 órdenes buenas.
	"""
	cerradas = [o for o in ordenes if o.cuadrilla and o.zona and o.estado in ("Completada", "No completada")]
	if not cerradas:
		return {}

	def exito(o):
		return o.estado == "Completada" and not o.es_retrabajo and o.sla != "Incumplido"

	media = sum(1 for o in cerradas if exito(o)) / len(cerradas)
	conteo: dict[tuple[str, str], list[int]] = {}
	for o in cerradas:
		c = conteo.setdefault((o.cuadrilla, o.zona), [0, 0])
		c[0] += 1 if exito(o) else 0
		c[1] += 1
	resultado: dict[str, dict[str, float]] = {}
	prior = 5
	for (crew, zona), (buenos, n) in conteo.items():
		tasa = (buenos + prior * media) / (n + prior)
		resultado.setdefault(crew, {})[zona] = round(tasa * n / (n + experiencia_media), 3)
	return resultado


def demanda_capacidad(
	demanda_min: dict[str, float],
	capacidad_min: dict[str, float],
	cuadrillas_por_zona: dict[str, list[tuple[str, float]]],
	vecinas: dict[str, set[str]] | None = None,
) -> dict:
	"""Compara demanda y capacidad (minutos) por zona y propone mover cuadrillas entre zonas vecinas.

	``cuadrillas_por_zona``: zona -> [(cuadrilla, minutos que aporta)].
	"""
	vecinas = vecinas or ZONAS_VECINAS
	zonas = sorted(set(demanda_min) | set(capacidad_min))
	cap = {z: float(capacidad_min.get(z, 0)) for z in zonas}
	dem = {z: float(demanda_min.get(z, 0)) for z in zonas}
	disponibles = {z: sorted(cuadrillas_por_zona.get(z, []), key=lambda c: c[1]) for z in zonas}

	def estado_zona(z, capacidad):
		if not capacidad.get(z):
			return "Sin cuadrillas" if dem[z] else "Sin demanda"
		r = dem[z] / capacidad[z]
		return "Déficit" if r > 1.0 else "Ajustada" if r >= 0.85 else "Normal" if r >= 0.6 else "Holgada"

	antes = {z: estado_zona(z, cap) for z in zonas}

	movimientos = []
	deficit = sorted((z for z in zonas if dem[z] > cap[z]), key=lambda z: -(dem[z] - cap[z]))
	for z in deficit:
		donantes = sorted(
			(d for d in zonas if d != z and cap[d] and dem[d] / cap[d] < 0.6),
			key=lambda d: (d not in vecinas.get(z, set()), dem[d] / cap[d]),
		)
		for d in donantes:
			while dem[z] > cap[z] and disponibles[d]:
				crew, minutos = disponibles[d][0]
				# El donante tiene que quedar por debajo de 85 % después de prestar la cuadrilla
				if cap[d] - minutos <= 0 or dem[d] / (cap[d] - minutos) > 0.85:
					break
				disponibles[d].pop(0)
				cap[d] -= minutos
				cap[z] += minutos
				movimientos.append(
					{
						"cuadrilla": crew,
						"de": d,
						"a": z,
						"minutos": round(minutos),
						"vecina": d in vecinas.get(z, set()),
						"motivo": f"{z} pide más trabajo del que puede cubrir; {d} está holgada.",
					}
				)
	return {
		"zonas": {
			z: {
				"demanda_min": round(dem[z]),
				"capacidad_min": round(capacidad_min.get(z, 0)),
				"ocupacion_pct": _pct(dem[z], capacidad_min.get(z, 0)),
				"estado": antes[z],
				"estado_con_movimientos": estado_zona(z, cap),
			}
			for z in zonas
		},
		"movimientos": movimientos,
		"sin_cubrir_min": {z: round(dem[z] - cap[z]) for z in zonas if dem[z] > cap[z]},
	}


@dataclass
class CuadrillaEnCampo:
	"""Situación de una cuadrilla en este momento, para decidir a quién darle una orden nueva."""

	cuadrilla: object  # optimizacion.Cuadrilla o engine.Crew
	lat: float
	lng: float
	libre_desde: datetime
	ordenes_hoy: int = 0
	fuente_ubicacion: str = "GPS"
	minutos_desde_ubicacion: float | None = None
	notas: list[str] = field(default_factory=list)


def mejor_cuadrilla(
	trabajo,
	en_campo: list[CuadrillaEnCampo],
	ahora: datetime,
	settings: Settings | None = None,
	modelo: ModeloViaje | None = None,
	afinidad_minutos: float = 20.0,
	maximo: int = 3,
) -> list[dict]:
	"""Cuadrillas que pueden atender ``trabajo`` hoy, de mejor a peor, con la explicación."""
	settings = settings or Settings()
	modelo = modelo or ModeloViaje(velocidad_kmh=settings.average_speed_kmh, factor_vial=settings.road_factor)
	opciones = []
	for cc in en_campo:
		c = cc.cuadrilla
		if not elegible(trabajo, c):
			continue
		if cc.ordenes_hoy >= c.max_orders:
			continue
		destino = (trabajo.latitude, trabajo.longitude)
		minutos = modelo.minutos(
			(cc.lat, cc.lng),
			destino,
			getattr(c, "terreno", LLANO),
			getattr(trabajo, "terreno", LLANO),
			trabajo.zone,
		)
		salida = max(cc.libre_desde, ahora, c.shift_start)
		llegada = salida + timedelta(minutes=minutos)
		inicio = max(llegada, trabajo.window_start)
		fin = inicio + timedelta(minutes=trabajo.duration_minutes)
		if inicio > trabajo.window_end or fin > c.shift_end:
			continue
		af = getattr(c, "afinidad", {}).get(trabajo.zone or "", 0.0)
		espera = (inicio - llegada).total_seconds() / 60
		costo = (
			minutos
			+ (inicio - trabajo.window_start).total_seconds() / 60 * settings.delay_weight
			+ cc.ordenes_hoy * settings.load_penalty_minutes
			- af * afinidad_minutos
			- (settings.zone_bonus_minutes if trabajo.zone and c.zone == trabajo.zone else 0)
			- c.quality_bonus_minutes
		)
		razones = [f"{minutos:.0f} min de viaje desde su {cc.fuente_ubicacion.lower()}"]
		if cc.minutos_desde_ubicacion is not None:
			razones[0] += f" (hace {cc.minutos_desde_ubicacion:.0f} min)"
		if cc.libre_desde > ahora:
			razones.append(f"termina lo que está haciendo a las {cc.libre_desde:%H:%M}")
		if af >= 0.5:
			razones.append(f"rinde bien en {trabajo.zone} (afinidad {af:.2f})")
		if trabajo.zone and c.zone == trabajo.zone:
			razones.append("es de la zona")
		razones.append(f"le quedan {c.max_orders - cc.ordenes_hoy} cupos hoy")
		if espera > 30:
			razones.append(f"esperaría {espera:.0f} min a que abra la ventana")
		opciones.append(
			{
				"cuadrilla": c.crew,
				"contratista": c.contractor,
				"costo": round(costo, 1),
				"minutos_viaje": round(minutos, 1),
				"km": round(haversine_km(cc.lat, cc.lng, trabajo.latitude, trabajo.longitude), 1),
				"cupos": c.max_orders - cc.ordenes_hoy,
				"ubicacion": cc.fuente_ubicacion,
				"llegada": inicio,
				"termina": fin,
				"razones": razones + cc.notas,
			}
		)
	return sorted(opciones, key=lambda o: (o["costo"], o["cuadrilla"]))[:maximo]
