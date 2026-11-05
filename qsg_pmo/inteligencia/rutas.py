"""Tiempo de viaje entre dos puntos.

Por defecto: distancia en línea recta x factor vial / velocidad, más lenta en la cordillera y con
el cruce en lancha a Vieques y Culebra. Si el GPS de las cuadrillas ya mostró la velocidad real de
una zona, se usa esa. Si hay un servidor OSRM con el mapa de Puerto Rico, se usan sus tiempos.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

from qsg_pmo.assignment.engine import haversine_km
from qsg_pmo.inteligencia.territorio import ISLA, LLANO, MONTANOSO

Punto = tuple[float, float]


@dataclass
class ModeloViaje:
	velocidad_kmh: float = 35.0
	# Las carreteras no son línea recta
	factor_vial: float = 1.4
	# En la cordillera central se avanza a esta fracción de la velocidad normal
	factor_montana: float = 0.65
	# Cruce a Vieques o Culebra: traslado al muelle, espera y lancha
	minutos_ferry: float = 150.0
	# Velocidad real medida con el GPS, por zona (km/h)
	velocidad_zona: dict[str, float] = field(default_factory=dict)
	# Tiempos reales (minutos) entre puntos, p. ej. de OSRM; None si no hay dato
	matriz: Callable[[Punto, Punto], float | None] | None = None

	def km(self, a: Punto, b: Punto) -> float:
		return haversine_km(a[0], a[1], b[0], b[1]) * self.factor_vial

	def minutos(
		self, a: Punto, b: Punto, terreno_a: str = LLANO, terreno_b: str = LLANO, zona: str | None = None
	) -> float:
		cruza_mar = (terreno_a == ISLA) != (terreno_b == ISLA)
		extra = self.minutos_ferry if cruza_mar else 0.0
		if self.matriz and not cruza_mar:
			real = self.matriz(a, b)
			if real is not None:
				return real
		velocidad = self.velocidad_zona.get(zona or "", self.velocidad_kmh)
		if MONTANOSO in (terreno_a, terreno_b) and zona not in self.velocidad_zona:
			velocidad *= self.factor_montana
		return self.km(a, b) / max(velocidad, 5.0) * 60 + extra


# ---------------------------------------------------------------------- OSRM
def url_tabla_osrm(base_url: str, puntos: list[Punto]) -> str:
	coords = ";".join(f"{lng:.6f},{lat:.6f}" for lat, lng in puntos)
	return f"{base_url.rstrip('/')}/table/v1/driving/{coords}?annotations=duration"


def leer_tabla_osrm(respuesta: dict, puntos: list[Punto]) -> dict[tuple[Punto, Punto], float]:
	"""Convierte la respuesta de OSRM (segundos) en {(a, b): minutos}."""
	if respuesta.get("code") != "Ok":
		raise ValueError(f"OSRM respondió {respuesta.get('code')}: {respuesta.get('message', '')}")
	tabla = {}
	for i, fila in enumerate(respuesta["durations"]):
		for j, segundos in enumerate(fila):
			if segundos is not None:
				tabla[(puntos[i], puntos[j])] = segundos / 60
	return tabla


def matriz_osrm(base_url: str, puntos: list[Punto], timeout: float = 10.0, max_puntos: int = 100):
	"""Pide a OSRM los tiempos entre todos los puntos. Devuelve una función para ``ModeloViaje.matriz``.

	OSRM limita el tamaño de la tabla (100 por defecto); con más puntos se usa la estimación.
	"""
	unicos = list(dict.fromkeys((round(p[0], 6), round(p[1], 6)) for p in puntos))
	if not base_url or not unicos or len(unicos) > max_puntos:
		return None
	with urllib.request.urlopen(url_tabla_osrm(base_url, unicos), timeout=timeout) as r:  # nosec B310
		tabla = leer_tabla_osrm(json.load(r), unicos)

	def consultar(a: Punto, b: Punto) -> float | None:
		return tabla.get(((round(a[0], 6), round(a[1], 6)), (round(b[0], 6), round(b[1], 6))))

	return consultar
