"""Territorio de operación: los 78 municipios de Puerto Rico.

Coordenadas aproximadas del casco urbano de cada municipio (sirven como ubicación de respaldo
cuando una orden llega sin GPS; la orden queda marcada como «ubicación aproximada»), el tipo de
terreno (la cordillera central es más lenta) y las islas municipio, que dependen del ferry de Ceiba.

Para Centroamérica se agrega otro diccionario con la misma forma (cantones de Costa Rica,
distritos de Panamá…) y se elige con ``PAISES``.
"""

from __future__ import annotations

import re
import unicodedata

LLANO = "Llano"
MONTANOSO = "Montañoso"
ISLA = "Isla"

# municipio: (latitud, longitud, terreno, zona sugerida)
PUERTO_RICO: dict[str, tuple[float, float, str, str]] = {
	"Adjuntas": (18.1627, -66.7224, MONTANOSO, "Centro"),
	"Aguada": (18.3794, -67.1882, LLANO, "Oeste"),
	"Aguadilla": (18.4275, -67.1541, LLANO, "Oeste"),
	"Aguas Buenas": (18.2569, -66.1030, MONTANOSO, "Este"),
	"Aibonito": (18.1400, -66.2660, MONTANOSO, "Centro"),
	"Añasco": (18.2827, -67.1396, LLANO, "Oeste"),
	"Arecibo": (18.4725, -66.7157, LLANO, "Norte"),
	"Arroyo": (17.9658, -66.0613, LLANO, "Sur"),
	"Barceloneta": (18.4505, -66.5385, LLANO, "Norte"),
	"Barranquitas": (18.1866, -66.3063, MONTANOSO, "Centro"),
	"Bayamón": (18.3989, -66.1557, LLANO, "Metro"),
	"Cabo Rojo": (18.0866, -67.1457, LLANO, "Oeste"),
	"Caguas": (18.2341, -66.0485, LLANO, "Este"),
	"Camuy": (18.4838, -66.8449, LLANO, "Norte"),
	"Canóvanas": (18.3791, -65.9013, LLANO, "Este"),
	"Carolina": (18.3808, -65.9574, LLANO, "Metro"),
	"Cataño": (18.4413, -66.1180, LLANO, "Metro"),
	"Cayey": (18.1119, -66.1660, MONTANOSO, "Centro"),
	"Ceiba": (18.2641, -65.6485, LLANO, "Este"),
	"Ciales": (18.3361, -66.4688, MONTANOSO, "Centro"),
	"Cidra": (18.1758, -66.1613, MONTANOSO, "Centro"),
	"Coamo": (18.0799, -66.3580, LLANO, "Sur"),
	"Comerío": (18.2192, -66.2257, MONTANOSO, "Centro"),
	"Corozal": (18.3411, -66.3170, MONTANOSO, "Centro"),
	"Culebra": (18.3030, -65.3010, ISLA, "Islas"),
	"Dorado": (18.4588, -66.2677, LLANO, "Norte"),
	"Fajardo": (18.3258, -65.6524, LLANO, "Este"),
	"Florida": (18.3625, -66.5616, LLANO, "Norte"),
	"Guánica": (17.9716, -66.9080, LLANO, "Sur"),
	"Guayama": (17.9841, -66.1138, LLANO, "Sur"),
	"Guayanilla": (18.0191, -66.7918, LLANO, "Sur"),
	"Guaynabo": (18.3575, -66.1110, LLANO, "Metro"),
	"Gurabo": (18.2544, -65.9730, LLANO, "Este"),
	"Hatillo": (18.4863, -66.8254, LLANO, "Norte"),
	"Hormigueros": (18.1396, -67.1274, LLANO, "Oeste"),
	"Humacao": (18.1497, -65.8274, LLANO, "Este"),
	"Isabela": (18.5005, -67.0243, LLANO, "Oeste"),
	"Jayuya": (18.2186, -66.5916, MONTANOSO, "Centro"),
	"Juana Díaz": (18.0525, -66.5066, LLANO, "Sur"),
	"Juncos": (18.2275, -65.9210, LLANO, "Este"),
	"Lajas": (18.0497, -67.0593, LLANO, "Oeste"),
	"Lares": (18.2950, -66.8782, MONTANOSO, "Centro"),
	"Las Marías": (18.2517, -66.9921, MONTANOSO, "Oeste"),
	"Las Piedras": (18.1830, -65.8663, LLANO, "Este"),
	"Loíza": (18.4313, -65.8802, LLANO, "Este"),
	"Luquillo": (18.3725, -65.7166, LLANO, "Este"),
	"Manatí": (18.4277, -66.4922, LLANO, "Norte"),
	"Maricao": (18.1808, -66.9799, MONTANOSO, "Oeste"),
	"Maunabo": (18.0072, -65.8993, LLANO, "Este"),
	"Mayagüez": (18.2013, -67.1397, LLANO, "Oeste"),
	"Moca": (18.3947, -67.1132, LLANO, "Oeste"),
	"Morovis": (18.3258, -66.4066, MONTANOSO, "Norte"),
	"Naguabo": (18.2116, -65.7349, LLANO, "Este"),
	"Naranjito": (18.3008, -66.2449, MONTANOSO, "Centro"),
	"Orocovis": (18.2269, -66.3913, MONTANOSO, "Centro"),
	"Patillas": (18.0063, -66.0157, LLANO, "Sur"),
	"Peñuelas": (18.0563, -66.7216, LLANO, "Sur"),
	"Ponce": (18.0111, -66.6141, LLANO, "Sur"),
	"Quebradillas": (18.4738, -66.9385, LLANO, "Norte"),
	"Rincón": (18.3402, -67.2499, LLANO, "Oeste"),
	"Río Grande": (18.3802, -65.8313, LLANO, "Este"),
	"Sabana Grande": (18.0777, -66.9604, LLANO, "Oeste"),
	"Salinas": (17.9775, -66.2979, LLANO, "Sur"),
	"San Germán": (18.0807, -67.0411, LLANO, "Oeste"),
	"San Juan": (18.4655, -66.1057, LLANO, "Metro"),
	"San Lorenzo": (18.1897, -65.9610, MONTANOSO, "Este"),
	"San Sebastián": (18.3366, -66.9902, MONTANOSO, "Oeste"),
	"Santa Isabel": (17.9661, -66.4049, LLANO, "Sur"),
	"Toa Alta": (18.3883, -66.2482, LLANO, "Norte"),
	"Toa Baja": (18.4440, -66.2546, LLANO, "Norte"),
	"Trujillo Alto": (18.3547, -66.0074, LLANO, "Metro"),
	"Utuado": (18.2655, -66.7005, MONTANOSO, "Centro"),
	"Vega Alta": (18.4122, -66.3313, LLANO, "Norte"),
	"Vega Baja": (18.4444, -66.3874, LLANO, "Norte"),
	"Vieques": (18.1263, -65.4401, ISLA, "Islas"),
	"Villalba": (18.1272, -66.4922, MONTANOSO, "Sur"),
	"Yabucoa": (18.0505, -65.8793, LLANO, "Este"),
	"Yauco": (18.0350, -66.8499, LLANO, "Sur"),
}

# Zonas que comparten frontera (para mover cuadrillas sin cruzar la isla)
ZONAS_VECINAS: dict[str, set[str]] = {
	"Metro": {"Este", "Norte", "Centro"},
	"Este": {"Metro", "Centro", "Sur", "Islas"},
	"Norte": {"Metro", "Centro", "Oeste"},
	"Oeste": {"Norte", "Centro", "Sur"},
	"Sur": {"Este", "Centro", "Oeste"},
	"Centro": {"Metro", "Este", "Norte", "Oeste", "Sur"},
	"Islas": {"Este"},
}

# Puerto de la lancha a Vieques y Culebra
PUERTO_FERRY = (18.2593, -65.6340)

PAISES = {"Puerto Rico": PUERTO_RICO}


def normalizar(texto: str | None) -> str:
	"""Minúsculas, sin acentos ni espacios repetidos: «Mayagüez» → «mayaguez». Conserva la puntuación."""
	if not texto:
		return ""
	t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
	return " ".join(t.lower().split())


def clave(texto: str | None) -> str:
	"""Como ``normalizar`` pero solo letras y números, para comparar nombres («Caguas, PR» → «caguas pr»)."""
	return " ".join(re.sub(r"[^a-z0-9]+", " ", normalizar(texto)).split())


_INDICE = {clave(m): m for m in PUERTO_RICO}


def municipio(texto: str | None, catalogo: dict | None = None) -> str | None:
	"""Nombre oficial del municipio a partir de lo que escribió el cliente («mayaguez», «SAN JUAN»)."""
	catalogo = catalogo or PUERTO_RICO
	indice = _INDICE if catalogo is PUERTO_RICO else {clave(m): m for m in catalogo}
	n = clave(texto)
	if not n:
		return None
	if n in indice:
		return indice[n]
	# El nombre más largo que aparezca completo en el texto («Bo. Pueblo, Río Grande PR»)
	for nombre in sorted(indice, key=len, reverse=True):
		if f" {nombre} " in f" {n} ":
			return indice[nombre]
	return None


def ubicacion(nombre: str | None) -> tuple[float, float] | None:
	m = municipio(nombre)
	return PUERTO_RICO[m][:2] if m else None


def terreno(nombre: str | None) -> str:
	m = municipio(nombre)
	return PUERTO_RICO[m][2] if m else LLANO


def zona_sugerida(nombre: str | None) -> str | None:
	m = municipio(nombre)
	return PUERTO_RICO[m][3] if m else None


def es_isla(nombre: str | None) -> bool:
	return terreno(nombre) == ISLA


def municipio_cercano(lat: float | None, lng: float | None, max_km: float = 25.0) -> str | None:
	"""Municipio cuyo casco urbano está más cerca de la coordenada (aproximado, sin polígonos)."""
	if lat is None or lng is None:
		return None
	from qsg_pmo.assignment.engine import haversine_km

	km, nombre = min((haversine_km(lat, lng, v[0], v[1]), m) for m, v in PUERTO_RICO.items())
	return nombre if km <= max_km else None


def municipios_en_texto(texto: str | None) -> set[str]:
	"""Todos los municipios mencionados en un texto (p. ej. el área de una alerta del clima)."""
	n = f" {clave(texto)} "
	return {oficial for nombre, oficial in _INDICE.items() if f" {nombre} " in n}
