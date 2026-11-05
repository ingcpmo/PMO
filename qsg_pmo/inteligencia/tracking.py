"""Seguimiento de las cuadrillas por GPS.

Recibe las ubicaciones que envía la app de campo (o un rastreador Traccar) y produce:

* el recorrido del día (km, minutos en movimiento y paradas),
* la velocidad real por zona, que alimenta al optimizador en lugar de una velocidad fija,
* el estado de cada cuadrilla con alertas accionables para el despachador.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from qsg_pmo.assignment.engine import haversine_km
from qsg_pmo.inteligencia.rutas import ModeloViaje

# Más rápido que esto entre dos lecturas es un salto del GPS, no un viaje
VELOCIDAD_MAX_KMH = 140.0
PRECISION_MAX_M = 150.0
EN_MOVIMIENTO_KMH = 5.0

SIN_SENAL = "Sin señal"
DETENIDA = "Detenida fuera de ruta"
TARDE = "Llegará tarde"
EN_SITIO_SIN_MARCAR = "En sitio sin marcar llegada"
SIN_GPS = "Sin ubicación"


@dataclass
class Ping:
	cuadrilla: str
	momento: datetime
	lat: float
	lng: float
	precision_m: float | None = None
	zona: str | None = None


@dataclass
class Parada:
	inicio: datetime
	fin: datetime
	lat: float
	lng: float

	@property
	def minutos(self) -> float:
		return (self.fin - self.inicio).total_seconds() / 60


@dataclass
class Visita:
	"""Una orden de la ruta de la cuadrilla, para comparar con el GPS."""

	orden: str
	lat: float
	lng: float
	estado: str
	ventana_fin: datetime | None = None
	zona: str | None = None
	terreno: str = "Llano"


@dataclass
class Alerta:
	tipo: str
	cuadrilla: str
	mensaje: str
	orden: str | None = None
	severidad: str = "Media"


@dataclass
class EstadoCuadrilla:
	cuadrilla: str
	lat: float | None = None
	lng: float | None = None
	ultimo_ping: datetime | None = None
	km_hoy: float = 0.0
	minutos_en_movimiento: float = 0.0
	alertas: list[Alerta] = field(default_factory=list)
	siguiente_orden: str | None = None
	llegada_estimada: datetime | None = None


def metros(a_lat, a_lng, b_lat, b_lng) -> float:
	return haversine_km(a_lat, a_lng, b_lat, b_lng) * 1000


def limpiar(pings: list[Ping]) -> list[Ping]:
	"""Ordena, quita duplicados, lecturas imprecisas y saltos imposibles."""
	salida: list[Ping] = []
	for p in sorted(pings, key=lambda p: p.momento):
		if not (-90 <= p.lat <= 90 and -180 <= p.lng <= 180) or (p.lat == 0 and p.lng == 0):
			continue
		if p.precision_m is not None and p.precision_m > PRECISION_MAX_M:
			continue
		if salida:
			prev = salida[-1]
			horas = (p.momento - prev.momento).total_seconds() / 3600
			if horas <= 0:
				continue
			if haversine_km(prev.lat, prev.lng, p.lat, p.lng) / horas > VELOCIDAD_MAX_KMH:
				continue
		salida.append(p)
	return salida


def recorrido(pings: list[Ping], parada_min: float = 5.0, radio_m: float = 150.0) -> dict:
	"""Km recorridos, minutos en movimiento y paradas de al menos ``parada_min`` minutos."""
	pings = limpiar(pings)
	km = 0.0
	movimiento = 0.0
	paradas: list[Parada] = []
	ancla = None
	for prev, p in itertools.pairwise(pings):
		d = haversine_km(prev.lat, prev.lng, p.lat, p.lng)
		minutos = (p.momento - prev.momento).total_seconds() / 60
		if minutos > 0 and d / (minutos / 60) >= EN_MOVIMIENTO_KMH:
			km += d
			movimiento += minutos
		if ancla is None:
			ancla = prev
		if metros(ancla.lat, ancla.lng, p.lat, p.lng) > radio_m:
			if (prev.momento - ancla.momento).total_seconds() / 60 >= parada_min:
				paradas.append(Parada(ancla.momento, prev.momento, ancla.lat, ancla.lng))
			ancla = p
	if ancla is not None and pings and (pings[-1].momento - ancla.momento).total_seconds() / 60 >= parada_min:
		paradas.append(Parada(ancla.momento, pings[-1].momento, ancla.lat, ancla.lng))
	return {"km": round(km, 2), "minutos_en_movimiento": round(movimiento, 1), "paradas": paradas}


def velocidad_por_zona(pings: list[Ping], min_tramos: int = 10) -> dict[str, float]:
	"""Velocidad media en movimiento por zona (km/h), con al menos ``min_tramos`` tramos de muestra."""
	por_zona: dict[str, list[tuple[float, float]]] = {}
	por_cuadrilla: dict[str, list[Ping]] = {}
	for p in pings:
		por_cuadrilla.setdefault(p.cuadrilla, []).append(p)
	for lista in por_cuadrilla.values():
		lista = limpiar(lista)
		for prev, p in itertools.pairwise(lista):
			if not p.zona or p.zona != prev.zona:
				continue
			horas = (p.momento - prev.momento).total_seconds() / 3600
			# Tramos de hasta 15 minutos: más largos esconden paradas
			if horas <= 0 or horas > 0.25:
				continue
			km = haversine_km(prev.lat, prev.lng, p.lat, p.lng)
			if km / horas >= EN_MOVIMIENTO_KMH:
				por_zona.setdefault(p.zona, []).append((km, horas))
	return {
		zona: round(sum(k for k, _ in tramos) / sum(h for _, h in tramos), 1)
		for zona, tramos in por_zona.items()
		if len(tramos) >= min_tramos
	}


def estado(
	cuadrilla: str,
	pings: list[Ping],
	visitas: list[Visita],
	ahora: datetime,
	modelo: ModeloViaje | None = None,
	sin_senal_min: float = 20.0,
	detenida_min: float = 30.0,
	radio_m: float = 300.0,
	base: tuple[float, float] | None = None,
) -> EstadoCuadrilla:
	"""Estado actual de una cuadrilla con alertas para el despachador."""
	modelo = modelo or ModeloViaje()
	limpios = limpiar(pings)
	e = EstadoCuadrilla(cuadrilla)
	pendientes = [v for v in visitas if v.estado in ("Programada", "En ruta", "En sitio")]
	if not limpios:
		if pendientes:
			e.alertas.append(
				Alerta(SIN_GPS, cuadrilla, "La cuadrilla tiene órdenes hoy y no ha enviado su ubicación.")
			)
		return e
	r = recorrido(limpios)
	ultimo = limpios[-1]
	e.lat, e.lng, e.ultimo_ping = ultimo.lat, ultimo.lng, ultimo.momento
	e.km_hoy, e.minutos_en_movimiento = r["km"], r["minutos_en_movimiento"]

	minutos_sin_dato = (ahora - ultimo.momento).total_seconds() / 60
	if minutos_sin_dato > sin_senal_min and pendientes:
		e.alertas.append(
			Alerta(
				SIN_SENAL,
				cuadrilla,
				f"Última ubicación hace {minutos_sin_dato:.0f} min. Llame a la cuadrilla.",
				severidad="Alta" if minutos_sin_dato > 2 * sin_senal_min else "Media",
			)
		)

	cerca = [v for v in visitas if metros(ultimo.lat, ultimo.lng, v.lat, v.lng) <= radio_m]
	en_base = base is not None and metros(ultimo.lat, ultimo.lng, base[0], base[1]) <= radio_m
	quieta = _minutos_quieta(limpios, radio_m=150.0)
	for v in cerca:
		if v.estado in ("Programada", "En ruta") and quieta >= 10:
			e.alertas.append(
				Alerta(
					EN_SITIO_SIN_MARCAR,
					cuadrilla,
					f"Lleva {quieta:.0f} min en la dirección de {v.orden} sin marcar «En sitio».",
					orden=v.orden,
					severidad="Baja",
				)
			)
	if quieta >= detenida_min and not cerca and not en_base and pendientes:
		e.alertas.append(
			Alerta(
				DETENIDA,
				cuadrilla,
				f"Detenida {quieta:.0f} min lejos de sus órdenes y de la base.",
				severidad="Media",
			)
		)

	siguiente = next((v for v in pendientes if v.estado != "En sitio"), None)
	if siguiente is not None:
		minutos = modelo.minutos(
			(ultimo.lat, ultimo.lng), (siguiente.lat, siguiente.lng), zona=siguiente.zona
		)
		# Si hay una orden en sitio, primero la termina (no sabemos cuánto falta: se toma el reloj actual)
		e.siguiente_orden = siguiente.orden
		e.llegada_estimada = ahora + timedelta(minutes=minutos)
		if siguiente.ventana_fin and e.llegada_estimada > siguiente.ventana_fin:
			tarde = (e.llegada_estimada - siguiente.ventana_fin).total_seconds() / 60
			e.alertas.append(
				Alerta(
					TARDE,
					cuadrilla,
					f"Llegaría a {siguiente.orden} {tarde:.0f} min después de la ventana. "
					"Avise al cliente o reasigne.",
					orden=siguiente.orden,
					severidad="Alta",
				)
			)
	return e


def _minutos_quieta(pings: list[Ping], radio_m: float) -> float:
	"""Minutos que la cuadrilla lleva dentro de un radio de su última ubicación."""
	ultimo = pings[-1]
	desde = ultimo.momento
	for p in reversed(pings):
		if metros(p.lat, p.lng, ultimo.lat, ultimo.lng) > radio_m:
			break
		desde = p.momento
	return (ultimo.momento - desde).total_seconds() / 60


# ---------------------------------------------------------------------- Traccar
def desde_traccar(
	posiciones: list[dict], dispositivos: dict[int, str], zona_horaria: str = "America/Puerto_Rico"
) -> list[Ping]:
	"""Convierte ``GET /api/positions`` de Traccar en pings. ``dispositivos``: deviceId -> cuadrilla.

	Traccar entrega la hora en UTC; aquí se pasa a la hora local del sitio (sin zona), como el resto
	de QSG PMO.
	"""
	tz = ZoneInfo(zona_horaria)
	salida = []
	for pos in posiciones:
		crew = dispositivos.get(pos.get("deviceId"))
		if not crew or pos.get("valid") is False:
			continue
		momento = datetime.fromisoformat(str(pos["fixTime"]).replace("Z", "+00:00"))
		if momento.tzinfo is None:
			momento = momento.replace(tzinfo=UTC)
		salida.append(
			Ping(
				cuadrilla=crew,
				momento=momento.astimezone(tz).replace(tzinfo=None),
				lat=float(pos["latitude"]),
				lng=float(pos["longitude"]),
				precision_m=pos.get("accuracy") or None,
			)
		)
	return salida
