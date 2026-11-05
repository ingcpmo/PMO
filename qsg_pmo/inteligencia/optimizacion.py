"""Optimización del plan de despacho.

Parte del plan del motor por reglas (``qsg_pmo.assignment.engine.plan``, sin cambiarlo) y de una
construcción por inserción, recalcula los tiempos con un modelo de viaje realista
(``rutas.ModeloViaje``: terreno, ferry, velocidad medida por GPS u OSRM) y los mejora con
búsqueda local:

* **reubicar** una orden en otra cuadrilla o en otra posición de la misma ruta,
* **intercambiar** dos órdenes entre cuadrillas,
* **invertir** un tramo de la ruta (2-opt),
* **insertar** las órdenes que quedaron sin asignar.

Respeta las mismas reglas duras del motor (habilidad, contratista ya asignado, capacidad, ventana
de cita y fin de turno) y agrega tres de la operación en Puerto Rico: zonas con incidencia
(apagón, inundación, alerta del clima) no reciben trabajo, Vieques y Culebra solo van a cuadrillas
habilitadas para el ferry, y el atraso en clientes empresariales pesa más. Si el resultado no es
mejor que el plan del motor por reglas, se devuelve ese plan, así que nunca empeora.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from qsg_pmo.assignment.engine import (
	PRIORITY_RANK,
	REASON_NO_CAPACITY,
	REASON_NO_CONTRACTOR_CREW,
	REASON_NO_LOCATION,
	REASON_NO_SKILL,
	REASON_NO_WINDOW,
	Assignment,
	Crew,
	Job,
	Settings,
	Unassigned,
)
from qsg_pmo.assignment.engine import plan as plan_por_reglas
from qsg_pmo.inteligencia.rutas import ModeloViaje
from qsg_pmo.inteligencia.territorio import ISLA, LLANO

REASON_ISLA = "Vieques/Culebra: ninguna cuadrilla habilitada para el ferry tiene la habilidad"
EMPRESARIAL = "Empresarial"
# Una orden sin asignar cuesta más que cualquier ruta: primero se asigna, después se acorta
PENALIDAD_NO_ASIGNADA = 100_000.0


@dataclass
class Trabajo(Job):
	"""Orden con los datos que el motor por reglas no usa."""

	segmento: str = "Residencial"
	terreno: str = LLANO
	# Motivo si la zona tiene una incidencia que impide trabajar (apagón, inundación, alerta)
	bloqueo: str | None = None


@dataclass
class Cuadrilla(Crew):
	terreno: str = LLANO
	# zona -> 0..1, qué tan bien rinde la cuadrilla en esa zona (de ``zonas.afinidad``)
	afinidad: dict[str, float] = field(default_factory=dict)
	opera_islas: bool = False


@dataclass
class Opciones:
	# El atraso en un cliente empresarial pesa este múltiplo del residencial
	factor_empresarial: float = 2.0
	# Minutos de bonificación para la cuadrilla con afinidad 1.0 en la zona de la orden
	afinidad_minutos: float = 20.0
	tiempo_max_s: float = 5.0
	rondas_max: int = 50


@dataclass
class Metricas:
	asignadas: int = 0
	sin_asignar: int = 0
	km: float = 0.0
	minutos_viaje: float = 0.0
	minutos_atraso: float = 0.0
	costo: float = 0.0


@dataclass
class Resultado:
	asignaciones: list[Assignment]
	no_asignadas: list[Unassigned]
	metricas: Metricas
	referencia: Metricas
	mejoras: int = 0
	usa_reglas: bool = False
	notas: list[str] = field(default_factory=list)

	@property
	def km_ahorrados(self) -> float:
		return round(self.referencia.km - self.metricas.km, 1)

	@property
	def minutos_ahorrados(self) -> float:
		return round(self.referencia.minutos_viaje - self.metricas.minutos_viaje, 1)

	@staticmethod
	def km_por_orden(m: Metricas) -> float:
		return round(m.km / m.asignadas, 1) if m.asignadas else 0.0

	def resumen(self) -> str:
		r, m = self.referencia, self.metricas
		partes = [
			f"{m.asignadas} órdenes asignadas ({m.asignadas - r.asignadas:+d} contra el motor por reglas)"
		]
		partes.append(
			f"{m.km:.1f} km de manejo, {self.km_por_orden(m)} km por orden "
			f"(motor por reglas: {self.km_por_orden(r)} km por orden)"
		)
		partes.append(
			f"{m.minutos_viaje:.0f} min de viaje ({self.minutos_ahorrados:+.0f} min contra el motor)"
		)
		return "; ".join(partes)


def _urgencia(job: Job):
	return (PRIORITY_RANK.get(job.priority, 2), job.sla_due or datetime.max, job.window_start, job.order)


def elegible(job: Job, crew: Crew) -> bool:
	if job.contractor and crew.contractor != job.contractor:
		return False
	if not job.skills <= crew.skills:
		return False
	if getattr(job, "terreno", LLANO) == ISLA:
		return getattr(crew, "opera_islas", False) or crew.zone == "Islas"
	return True


class _Planificador:
	def __init__(self, crews, settings, modelo, opciones):
		self.crews = {c.crew: c for c in crews}
		self.settings = settings
		self.modelo = modelo
		self.opciones = opciones
		self._cache: dict[tuple, tuple[float, float]] = {}

	def viaje(self, a, b, terreno_a, terreno_b, zona) -> tuple[float, float]:
		"""(minutos, km) con caché: la búsqueda local consulta los mismos tramos miles de veces."""
		clave = (a, b, terreno_a, terreno_b, zona)
		if clave not in self._cache:
			self._cache[clave] = (
				self.modelo.minutos(a, b, terreno_a, terreno_b, zona),
				self.modelo.km(a, b),
			)
		return self._cache[clave]

	# ------------------------------------------------------------------ evaluación de una ruta
	def evaluar(self, crew: Crew, ruta: list[Job]):
		"""(factible, costo, detalle). El detalle tiene inicio, fin, km y minutos de cada parada."""
		n = crew.preassigned + len(ruta)
		if n > crew.max_orders:
			return False, 0.0, []
		s, o = self.settings, self.opciones
		t = crew.shift_start
		pos = (crew.latitude, crew.longitude)
		terreno = getattr(crew, "terreno", LLANO)
		afinidad = getattr(crew, "afinidad", {})
		costo = s.load_penalty_minutes * sum(range(crew.preassigned, n))
		detalle = []
		for job in ruta:
			destino = (job.latitude, job.longitude)
			jterreno = getattr(job, "terreno", LLANO)
			minutos, km = self.viaje(pos, destino, terreno, jterreno, job.zone)
			inicio = max(t + timedelta(minutes=minutos), job.window_start)
			if inicio > job.window_end:
				return False, 0.0, []
			fin = inicio + timedelta(minutes=job.duration_minutes)
			if fin > crew.shift_end:
				return False, 0.0, []
			atraso = (inicio - job.window_start).total_seconds() / 60
			peso = s.delay_weight * (
				o.factor_empresarial if getattr(job, "segmento", "") == EMPRESARIAL else 1
			)
			costo += minutos + atraso * peso - crew.quality_bonus_minutes
			if job.zone and crew.zone == job.zone:
				costo -= s.zone_bonus_minutes
			costo -= o.afinidad_minutos * afinidad.get(job.zone or "", 0.0)
			detalle.append((job, inicio, fin, km, minutos, atraso))
			t, pos, terreno = fin, destino, jterreno
		return True, costo, detalle

	def costo_total(self, rutas, sin_asignar) -> float:
		total = 0.0
		for crew_name, ruta in rutas.items():
			if ruta:
				total += self.evaluar(self.crews[crew_name], ruta)[1]
		for job in sin_asignar:
			total += PENALIDAD_NO_ASIGNADA * (4 - PRIORITY_RANK.get(job.priority, 2))
		return total

	# ------------------------------------------------------------------ inserción
	def mejor_insercion(self, job, rutas, excluir=None):
		"""(delta, cuadrilla, posición) más barata y factible, o None."""
		mejor = None
		for name, crew in self.crews.items():
			if name == excluir or not elegible(job, crew):
				continue
			ruta = rutas[name]
			if crew.preassigned + len(ruta) >= crew.max_orders:
				continue
			base = self.evaluar(crew, ruta)[1] if ruta else 0.0
			for i in range(len(ruta) + 1):
				ok, costo, _ = self.evaluar(crew, [*ruta[:i], job, *ruta[i:]])
				if ok and (mejor is None or (costo - base, name, i) < mejor):
					mejor = (costo - base, name, i)
		return mejor

	def construir(self, jobs):
		rutas = {name: [] for name in self.crews}
		sin_asignar = []
		for job in sorted(jobs, key=_urgencia):
			mejor = self.mejor_insercion(job, rutas)
			if mejor is None:
				sin_asignar.append(job)
			else:
				_, name, i = mejor
				rutas[name].insert(i, job)
		return rutas, sin_asignar

	def reparar(self, rutas):
		"""Quita las paradas que no caben con el modelo de viaje realista."""
		fuera = []
		for name, ruta in rutas.items():
			crew = self.crews[name]
			while ruta and not self.evaluar(crew, ruta)[0]:
				for k in range(1, len(ruta) + 1):
					if not self.evaluar(crew, ruta[:k])[0]:
						fuera.append(ruta.pop(k - 1))
						break
		return fuera

	# ------------------------------------------------------------------ búsqueda local
	def mejorar(self, rutas, sin_asignar, limite):
		mejoras = 0
		for _ in range(self.opciones.rondas_max):
			if time.monotonic() > limite:
				break
			cambio = (
				self._insertar_pendientes(rutas, sin_asignar)
				| self._reubicar(rutas, limite)
				| self._intercambiar(rutas, limite)
				| self._dos_opt(rutas, limite)
			)
			if not cambio:
				break
			mejoras += 1
		return mejoras

	def _insertar_pendientes(self, rutas, sin_asignar):
		cambio = False
		for job in sorted(list(sin_asignar), key=_urgencia):
			mejor = self.mejor_insercion(job, rutas)
			if mejor is not None:
				_, name, i = mejor
				rutas[name].insert(i, job)
				sin_asignar.remove(job)
				cambio = True
		return cambio

	def _reubicar(self, rutas, limite):
		cambio = False
		for origen in list(rutas):
			i = 0
			while i < len(rutas[origen]):
				if time.monotonic() > limite:
					return cambio
				job = rutas[origen][i]
				resto = rutas[origen][:i] + rutas[origen][i + 1 :]
				antes = self.evaluar(self.crews[origen], rutas[origen])[1]
				despues_origen = self.evaluar(self.crews[origen], resto)[1] if resto else 0.0
				ahorro_origen = antes - despues_origen
				mejor = None
				for destino, crew in self.crews.items():
					if not elegible(job, crew):
						continue
					ruta = resto if destino == origen else rutas[destino]
					if destino != origen and crew.preassigned + len(ruta) >= crew.max_orders:
						continue
					base = (
						(despues_origen if destino == origen else self.evaluar(crew, ruta)[1])
						if ruta
						else 0.0
					)
					for k in range(len(ruta) + 1):
						if destino == origen and k == i:
							continue
						ok, costo, _ = self.evaluar(crew, [*ruta[:k], job, *ruta[k:]])
						delta = costo - base - ahorro_origen
						if ok and delta < -1e-6 and (mejor is None or (delta, destino, k) < mejor):
							mejor = (delta, destino, k)
				if mejor:
					_, destino, k = mejor
					rutas[origen] = resto
					rutas[destino].insert(k, job)
					cambio = True
				else:
					i += 1
		return cambio

	def _intercambiar(self, rutas, limite):
		cambio = False
		nombres = sorted(rutas)
		for a_idx, a in enumerate(nombres):
			for b in nombres[a_idx + 1 :]:
				i = 0
				while i < len(rutas[a]):
					if time.monotonic() > limite:
						return cambio
					hecho = False
					for j in range(len(rutas[b])):
						ja, jb = rutas[a][i], rutas[b][j]
						if not (elegible(jb, self.crews[a]) and elegible(ja, self.crews[b])):
							continue
						nueva_a = [*rutas[a][:i], jb, *rutas[a][i + 1 :]]
						nueva_b = [*rutas[b][:j], ja, *rutas[b][j + 1 :]]
						ok_a, ca, _ = self.evaluar(self.crews[a], nueva_a)
						ok_b, cb, _ = self.evaluar(self.crews[b], nueva_b)
						if not (ok_a and ok_b):
							continue
						antes = (
							self.evaluar(self.crews[a], rutas[a])[1]
							+ self.evaluar(self.crews[b], rutas[b])[1]
						)
						if ca + cb < antes - 1e-6:
							rutas[a], rutas[b] = nueva_a, nueva_b
							cambio = hecho = True
							break
					if not hecho:
						i += 1
		return cambio

	def _dos_opt(self, rutas, limite):
		cambio = False
		for name, ruta in rutas.items():
			crew = self.crews[name]
			mejorado = True
			while mejorado and len(ruta) > 2:
				if time.monotonic() > limite:
					return cambio
				mejorado = False
				actual = self.evaluar(crew, ruta)[1]
				for i in range(len(ruta) - 1):
					for k in range(i + 1, len(ruta)):
						nueva = ruta[:i] + ruta[i : k + 1][::-1] + ruta[k + 1 :]
						ok, costo, _ = self.evaluar(crew, nueva)
						if ok and costo < actual - 1e-6:
							ruta[:] = nueva
							cambio = mejorado = True
							break
					if mejorado:
						break
		return cambio

	# ------------------------------------------------------------------ salida
	def metricas(self, rutas, sin_asignar) -> Metricas:
		m = Metricas(sin_asignar=len(sin_asignar), costo=self.costo_total(rutas, sin_asignar))
		for name, ruta in rutas.items():
			if not ruta:
				continue
			_, _, detalle = self.evaluar(self.crews[name], ruta)
			m.asignadas += len(ruta)
			m.km += sum(d[3] for d in detalle)
			m.minutos_viaje += sum(d[4] for d in detalle)
			m.minutos_atraso += sum(d[5] for d in detalle)
		m.km, m.minutos_viaje, m.minutos_atraso = (
			round(m.km, 1),
			round(m.minutos_viaje, 1),
			round(m.minutos_atraso, 1),
		)
		return m

	def asignaciones(self, rutas) -> list[Assignment]:
		salida = []
		for name in sorted(rutas):
			crew = self.crews[name]
			_, _, detalle = self.evaluar(crew, rutas[name])
			for idx, (job, inicio, fin, km, minutos, _) in enumerate(detalle, start=1):
				salida.append(
					Assignment(
						order=job.order,
						crew=name,
						contractor=crew.contractor,
						sequence=crew.preassigned + idx,
						estimated_arrival=inicio,
						estimated_finish=fin,
						travel_km=round(km, 2),
						travel_minutes=round(minutos, 1),
					)
				)
		return salida

	def motivo(self, job, rutas) -> str:
		if job.latitude is None or job.longitude is None:
			return REASON_NO_LOCATION
		if getattr(job, "bloqueo", None):
			return f"Zona con incidencia: {job.bloqueo}"
		pool = [c for c in self.crews.values() if not job.contractor or c.contractor == job.contractor]
		con_habilidad = [c for c in pool if job.skills <= c.skills]
		if not con_habilidad:
			return REASON_NO_CONTRACTOR_CREW if job.contractor else REASON_NO_SKILL
		elegibles = [c for c in con_habilidad if elegible(job, c)]
		if not elegibles:
			return REASON_ISLA
		if all(c.preassigned + len(rutas.get(c.crew, [])) >= c.max_orders for c in elegibles):
			return REASON_NO_CAPACITY
		return REASON_NO_WINDOW


def optimizar(
	jobs: list[Job],
	crews: list[Crew],
	settings: Settings | None = None,
	modelo: ModeloViaje | None = None,
	opciones: Opciones | None = None,
) -> Resultado:
	settings = settings or Settings()
	modelo = modelo or ModeloViaje(velocidad_kmh=settings.average_speed_kmh, factor_vial=settings.road_factor)
	opciones = opciones or Opciones()
	limite = time.monotonic() + opciones.tiempo_max_s
	for c in crews:
		c.reset()
	p = _Planificador(crews, settings, modelo, opciones)

	directas = []
	planificables = []
	for job in jobs:
		if job.latitude is None or job.longitude is None or getattr(job, "bloqueo", None):
			directas.append(job)
		else:
			planificables.append(job)

	# 1) Plan del motor por reglas, re-evaluado con el modelo de viaje realista
	por_reglas, _ = plan_por_reglas(planificables, crews, settings)
	idx = {j.order: j for j in planificables}
	rutas_ref = {name: [] for name in p.crews}
	for a in sorted(por_reglas, key=lambda a: (a.crew, a.sequence)):
		job = idx[a.order]
		if elegible(job, p.crews[a.crew]):
			rutas_ref[a.crew].append(job)
	asignadas_ref = {j.order for r in rutas_ref.values() for j in r}
	sin_ref = [j for j in planificables if j.order not in asignadas_ref]
	sin_ref += p.reparar(rutas_ref)
	referencia = p.metricas(rutas_ref, sin_ref + directas)

	# 2) Dos puntos de partida mejorados con búsqueda local: el plan por reglas y una inserción
	mitad = time.monotonic() + (limite - time.monotonic()) / 2
	rutas_a = {k: list(v) for k, v in rutas_ref.items()}
	sin_a = list(sin_ref)
	mejoras_a = p.mejorar(rutas_a, sin_a, mitad)
	rutas_b, sin_b = p.construir(planificables)
	mejoras_b = p.mejorar(rutas_b, sin_b, limite)
	if p.costo_total(rutas_b, sin_b) < p.costo_total(rutas_a, sin_a):
		rutas, sin, mejoras = rutas_b, sin_b, mejoras_b
	else:
		rutas, sin, mejoras = rutas_a, sin_a, mejoras_a

	final = p.metricas(rutas, sin + directas)
	usa_reglas = final.costo >= referencia.costo - 1e-6
	if usa_reglas:
		rutas, sin, final = rutas_ref, sin_ref, referencia

	notas = []
	if usa_reglas:
		notas.append("El plan del motor por reglas ya era el mejor encontrado.")
	if any(j.terreno == ISLA for j in planificables if isinstance(j, Trabajo)):
		notas.append("Hay órdenes en Vieques/Culebra: confirme el horario de la lancha antes de aprobar.")
	return Resultado(
		asignaciones=p.asignaciones(rutas),
		no_asignadas=[Unassigned(j.order, p.motivo(j, rutas)) for j in sorted(sin + directas, key=_urgencia)],
		metricas=final,
		referencia=referencia,
		mejoras=mejoras,
		usa_reglas=usa_reglas,
		notas=notas,
	)
