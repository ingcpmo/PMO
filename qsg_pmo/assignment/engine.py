"""Motor de asignación por reglas de QSG PMO.

Funciones puras: no tocan la base de datos, para poder probarlas y
cambiar de motor (reglas, VROOM) sin tocar los DocTypes.

Algoritmo voraz determinista:
1. Ordena las órdenes por urgencia (prioridad, vencimiento SLA, inicio de ventana).
2. Para cada orden filtra cuadrillas elegibles: tienen las habilidades,
   no superan su máximo diario y pueden llegar dentro de la ventana y
   terminar dentro del turno.
3. Entre las elegibles elige la de menor costo (minutos de viaje + atraso
   dentro de la ventana + carga - bonificación por zona).
4. Lo que no cabe queda en ``unassigned`` con el motivo.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta

PRIORITY_RANK = {"Crítica": 0, "Alta": 1, "Normal": 2, "Baja": 3}

REASON_NO_SKILL = "Ninguna cuadrilla tiene las habilidades requeridas"
REASON_NO_CAPACITY = "Las cuadrillas con la habilidad ya están a capacidad"
REASON_NO_WINDOW = "Ninguna cuadrilla llega dentro de la ventana o del turno"
REASON_NO_LOCATION = "La orden no tiene coordenadas"
REASON_NO_CONTRACTOR_CREW = "El contratista asignado no tiene cuadrillas disponibles con la habilidad"


@dataclass
class Job:
	"""Una orden a asignar."""

	order: str
	latitude: float | None
	longitude: float | None
	window_start: datetime
	window_end: datetime
	duration_minutes: int
	skills: set[str] = field(default_factory=set)
	priority: str = "Normal"
	sla_due: datetime | None = None
	zone: str | None = None
	# Si la orden ya fue asignada a un contratista, solo sus cuadrillas son elegibles
	contractor: str | None = None


@dataclass
class Crew:
	"""Una cuadrilla disponible para el día."""

	crew: str
	latitude: float
	longitude: float
	shift_start: datetime
	shift_end: datetime
	skills: set[str] = field(default_factory=set)
	max_orders: int = 6
	zone: str | None = None
	contractor: str | None = None
	# Minutos de bonificación (positivo) o penalización (negativo) por la calificación del contratista
	quality_bonus_minutes: float = 0.0
	# Órdenes que la cuadrilla ya tiene programadas ese día en otros planes
	preassigned: int = 0
	# Estado interno durante la planificación
	_last_lat: float = field(init=False, default=0.0)
	_last_lng: float = field(init=False, default=0.0)
	_available_at: datetime = field(init=False, default=datetime.min)
	_count: int = field(init=False, default=0)

	def __post_init__(self):
		self.reset()

	def reset(self):
		self._last_lat = self.latitude
		self._last_lng = self.longitude
		self._available_at = self.shift_start
		self._count = self.preassigned


@dataclass
class Assignment:
	order: str
	crew: str
	contractor: str | None
	sequence: int
	estimated_arrival: datetime
	estimated_finish: datetime
	travel_km: float
	travel_minutes: float


@dataclass
class Unassigned:
	order: str
	reason: str


@dataclass
class Settings:
	average_speed_kmh: float = 35.0
	# Las carreteras de PR no son línea recta: factor sobre la distancia haversine
	road_factor: float = 1.4
	# Penalización en minutos por cada orden que la cuadrilla ya tiene (balanceo)
	load_penalty_minutes: float = 10.0
	# Bonificación en minutos si la cuadrilla es de la misma zona
	zone_bonus_minutes: float = 15.0
	# Peso de cada minuto de atraso respecto al inicio de la ventana
	delay_weight: float = 0.5


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
	r = 6371.0
	p1, p2 = math.radians(lat1), math.radians(lat2)
	dp = p2 - p1
	dl = math.radians(lng2 - lng1)
	a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
	return 2 * r * math.asin(math.sqrt(a))


def _urgency_key(job: Job):
	return (
		PRIORITY_RANK.get(job.priority, 2),
		job.sla_due or datetime.max,
		job.window_start,
		job.order,
	)


def plan(jobs: list[Job], crews: list[Crew], settings: Settings | None = None):
	"""Devuelve (asignaciones, no_asignadas)."""
	settings = settings or Settings()
	for c in crews:
		c.reset()

	assignments: list[Assignment] = []
	unassigned: list[Unassigned] = []

	for job in sorted(jobs, key=_urgency_key):
		if job.latitude is None or job.longitude is None:
			unassigned.append(Unassigned(job.order, REASON_NO_LOCATION))
			continue

		pool = [c for c in crews if not job.contractor or c.contractor == job.contractor]
		skilled = [c for c in pool if job.skills <= c.skills]
		if not skilled:
			reason = (
				REASON_NO_CONTRACTOR_CREW if job.contractor and len(pool) < len(crews) else REASON_NO_SKILL
			)
			unassigned.append(Unassigned(job.order, reason))
			continue

		with_capacity = [c for c in skilled if c._count < c.max_orders]
		if not with_capacity:
			unassigned.append(Unassigned(job.order, REASON_NO_CAPACITY))
			continue

		best = None
		for c in with_capacity:
			km = haversine_km(c._last_lat, c._last_lng, job.latitude, job.longitude) * settings.road_factor
			travel_min = km / settings.average_speed_kmh * 60
			arrival = c._available_at + timedelta(minutes=travel_min)
			# Si llega antes de la ventana, espera al inicio
			start = max(arrival, job.window_start)
			finish = start + timedelta(minutes=job.duration_minutes)
			if start > job.window_end or finish > c.shift_end:
				continue
			# Preferir atender temprano dentro de la ventana (protege la cita y el SLA)
			delay_min = (start - job.window_start).total_seconds() / 60
			cost = travel_min + delay_min * settings.delay_weight + c._count * settings.load_penalty_minutes
			if job.zone and c.zone == job.zone:
				cost -= settings.zone_bonus_minutes
			cost -= c.quality_bonus_minutes
			key = (cost, c.crew)
			if best is None or key < best[0]:
				best = (key, c, km, travel_min, start, finish)

		if best is None:
			unassigned.append(Unassigned(job.order, REASON_NO_WINDOW))
			continue

		_, c, km, travel_min, start, finish = best
		c._count += 1
		c._available_at = finish
		c._last_lat, c._last_lng = job.latitude, job.longitude
		assignments.append(
			Assignment(
				order=job.order,
				crew=c.crew,
				contractor=c.contractor,
				sequence=c._count,
				estimated_arrival=start,
				estimated_finish=finish,
				travel_km=round(km, 2),
				travel_minutes=round(travel_min, 1),
			)
		)

	return assignments, unassigned
