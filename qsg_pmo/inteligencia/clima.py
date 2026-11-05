"""Alertas del Servicio Nacional de Meteorología (NWS San Juan) convertidas en incidencias por zona.

Fuente: ``https://api.weather.gov/alerts/active?area=PR`` (GeoJSON, sin clave; exige un
User-Agent). El área de cada alerta trae municipios («Bayamón, Caguas…») o regiones («Northeast»,
«San Juan and Vicinity»); ambos se traducen a las zonas de QSG.

Impacto para la operación:

* **Suspender**: huracán, tormenta tropical, inundación repentina, tornado, marejada, viento extremo.
* **Sin altura**: viento fuerte o tronada severa; no se suben postes ni escaleras (taps HFC y drops aéreos).
* **Precaución**: inundación menor o calor; se trabaja, con rutas y descansos ajustados.
"""

from __future__ import annotations

from datetime import datetime

from qsg_pmo.inteligencia.territorio import clave, municipios_en_texto, normalizar, zona_sugerida

SUSPENDER = "Suspender"
SIN_ALTURA = "Sin altura"
PRECAUCION = "Precaución"

# palabra clave (en inglés o español, normalizada) -> impacto. El primero que coincide gana.
EVENTOS = [
	("hurricane warning", SUSPENDER),
	("aviso de huracan", SUSPENDER),
	("tropical storm warning", SUSPENDER),
	("aviso de tormenta tropical", SUSPENDER),
	("flash flood warning", SUSPENDER),
	("aviso de inundaciones repentinas", SUSPENDER),
	("tornado warning", SUSPENDER),
	("storm surge warning", SUSPENDER),
	("extreme wind warning", SUSPENDER),
	("hurricane watch", SIN_ALTURA),
	("vigilancia de huracan", SIN_ALTURA),
	("tropical storm watch", SIN_ALTURA),
	("vigilancia de tormenta tropical", SIN_ALTURA),
	("high wind", SIN_ALTURA),
	("wind advisory", SIN_ALTURA),
	("severe thunderstorm warning", SIN_ALTURA),
	("tronadas severas", SIN_ALTURA),
	("flood warning", PRECAUCION),
	("flood advisory", PRECAUCION),
	("advertencia de inundaciones", PRECAUCION),
	("aviso de inundaciones", PRECAUCION),
	("heat advisory", PRECAUCION),
	("excessive heat", PRECAUCION),
	("advertencia de calor", PRECAUCION),
]

# Regiones que usa el NWS en sus pronósticos de Puerto Rico -> zonas de QSG
REGIONES = {
	"san juan and vicinity": {"Metro"},
	"northeast": {"Este"},
	"noreste": {"Este"},
	"southeast": {"Este", "Sur"},
	"sureste": {"Este", "Sur"},
	"eastern interior": {"Este", "Centro"},
	"interior este": {"Este", "Centro"},
	"north central": {"Norte"},
	"norte central": {"Norte"},
	"central interior": {"Centro"},
	"interior central": {"Centro"},
	"northwest": {"Norte", "Oeste"},
	"noroeste": {"Norte", "Oeste"},
	"western interior": {"Oeste", "Centro"},
	"interior oeste": {"Oeste", "Centro"},
	"southwest": {"Oeste", "Sur"},
	"suroeste": {"Oeste", "Sur"},
	"south central": {"Sur"},
	"sur central": {"Sur"},
	"ponce and vicinity": {"Sur"},
	"mayaguez and vicinity": {"Oeste"},
	"culebra": {"Islas"},
	"vieques": {"Islas"},
}


def impacto(evento: str | None) -> str | None:
	n = normalizar(evento)
	for palabra, valor in EVENTOS:
		if palabra in n:
			return valor
	return None


def zonas_del_area(
	area: str | None, municipio_a_zona: dict[str, str] | None = None
) -> tuple[set[str], set[str]]:
	"""(zonas, municipios) mencionados en el área de una alerta."""
	municipios = municipios_en_texto(area)
	zonas = {(municipio_a_zona or {}).get(m) or zona_sugerida(m) for m in municipios} - {None}
	n = f" {clave(area)} "
	for region, zs in REGIONES.items():
		if f" {region} " in n:
			zonas |= zs
	return zonas, municipios


def _fecha(valor: str | None) -> datetime | None:
	if not valor:
		return None
	try:
		return datetime.fromisoformat(valor.replace("Z", "+00:00"))
	except ValueError:
		return None


def incidencias_desde_nws(geojson: dict, municipio_a_zona: dict[str, str] | None = None) -> list[dict]:
	"""Una incidencia por alerta relevante, con zonas, municipios, impacto y vigencia."""
	salida = []
	for f in geojson.get("features", []):
		p = f.get("properties", {})
		efecto = impacto(p.get("event"))
		if not efecto or p.get("status", "Actual") != "Actual" or p.get("messageType") == "Cancel":
			continue
		zonas, municipios = zonas_del_area(p.get("areaDesc"), municipio_a_zona)
		if not zonas:
			continue
		salida.append(
			{
				"id": p.get("id") or f.get("id"),
				"evento": p.get("event"),
				"titulo": p.get("headline") or p.get("event"),
				"impacto": efecto,
				"severidad": p.get("severity"),
				"zonas": sorted(zonas),
				"municipios": sorted(municipios),
				"desde": _fecha(p.get("onset") or p.get("effective")),
				"hasta": _fecha(p.get("ends") or p.get("expires")),
				"fuente": "NWS",
			}
		)
	return salida


def descargar_alertas(user_agent: str, area: str = "PR", timeout: float = 15.0) -> dict:
	"""Alertas activas del NWS. Requiere salida a internet hacia api.weather.gov."""
	import json
	import urllib.request

	req = urllib.request.Request(
		f"https://api.weather.gov/alerts/active?area={area}",
		headers={"User-Agent": user_agent, "Accept": "application/geo+json"},
	)
	with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 - URL fija de NWS
		return json.load(r)
