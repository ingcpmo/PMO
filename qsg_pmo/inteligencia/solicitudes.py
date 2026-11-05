"""Interpretación de solicitudes en texto libre (correo, ticket o mensaje de Liberty) por reglas.

Funciona sin modelo de lenguaje y también valida lo que devuelve el modelo: el tipo de trabajo tiene
que existir en el catálogo y el municipio en el territorio. Los datos personales (teléfono, cuenta,
correo) salen siempre del texto original con expresiones regulares, nunca del modelo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from qsg_pmo.inteligencia import territorio

TELEFONO_RE = re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?(787|939)\)?[\s.-]?(\d{3})[\s.-]?(\d{4})(?!\d)")
CORREO_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
CUENTA_RE = re.compile(
	r"\b(?:cuenta|account|acct|cta)\.?\s*(?:#|no\.?|num\.?|n[uú]mero)?\s*[:=]?\s*(\d{6,14})", re.I
)
ORDEN_RE = re.compile(
	r"\b(?:orden|order|ticket|caso|case|wo|so|ot)\s*(?:#|no\.?|num\.?)?\s*[:=]?\s*([A-Z0-9][A-Z0-9-]{3,30})",
	re.I,
)
# «Cliente: X» al inicio de línea o en medio del texto («… Cliente: X. Dirección: Y. Tel …»); el valor
# termina donde empieza otra etiqueta, en un salto de línea o en «;».
_ETIQUETAS = (
	r"tel[eé]fono|tel\.?|cel(?:ular)?\.?|cuenta|direcci[oó]n|dir\.|cliente|suscriptor|nombre|contacto"
	r"|fecha|ticket|orden|caso|correo|email"
)
ETIQUETA_RE = (
	r"(?:^|\n|;|[.,]\s)\s*(?:{})\s*[:=-]\s*([^\n;]+?)\s*"
	r"(?=[.,]?\s+(?:" + _ETIQUETAS + r")(?![a-záéíóúñ])|[\n;]|$)"
)
NOMBRE_RE = re.compile(ETIQUETA_RE.format("cliente|suscriptor|nombre|contacto|customer|name"), re.I)
DIRECCION_RE = re.compile(ETIQUETA_RE.format("direcci[oó]n|dir\\.?|address|ubicaci[oó]n"), re.I)
FECHA_ISO_RE = re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b")
FECHA_DMY_RE = re.compile(r"\b(\d{1,2})/(\d{1,2})/(20\d{2})\b")
HORAS_RE = re.compile(
	r"\b(?:de\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?\s*(?:a|-|hasta)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?",
	re.I,
)
DIAS = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo"]

PRIORIDADES = ("Crítica", "Alta", "Normal", "Baja")


@dataclass
class TipoTrabajo:
	codigo: str
	nombre: str
	tecnologia: str
	segmento: str
	categoria: str


@dataclass
class Catalogo:
	tipos: list[TipoTrabajo] = field(default_factory=list)
	# municipio oficial -> zona configurada en QSG Zona
	municipio_a_zona: dict[str, str] = field(default_factory=dict)

	def tipo(self, codigo: str | None) -> TipoTrabajo | None:
		return next((t for t in self.tipos if t.codigo == codigo), None)


def _tiene(n: str, *palabras: str) -> bool:
	return any(re.search(rf"\b{p}", n) for p in palabras)


def tecnologia(n: str) -> str | None:
	if _tiene(n, "fibra", "ftth", "ont\\b", "gpon", "optic", "splitter", "cto\\b", "roseta"):
		return "FTTH"
	if _tiene(n, "hfc", "coax", "docsis", "cable ?modem", "modem", "tap\\b", "conector f\\b"):
		return "HFC"
	return None


def segmento(n: str) -> str:
	if _tiene(
		n, "empresa", "negocio", "comercial", "b2b", "corporativ", "oficina", "pyme", "empresarial", "tienda"
	):
		return "Empresarial"
	return "Residencial"


def categoria(n: str) -> str | None:
	if _tiene(n, "reconector", "reponch", "cambio de conector"):
		return "Reconectorización"
	if _tiene(
		n,
		"averia",
		"falla",
		"sin servicio",
		"no funciona",
		"repar",
		"intermiten",
		"lento",
		"no hay senal",
		"caido",
	):
		return "Reparación"
	if _tiene(
		n, "instala", "nuevo servicio", "servicio nuevo", "alta de servicio", "conexion nueva", "activacion"
	):
		return "Instalación"
	if _tiene(n, "conector"):
		return "Reconectorización"
	return None


def prioridad(n: str, seg: str, cat: str | None) -> str:
	# Crítica solo para emergencias y servicios esenciales; «urgente» de un cliente es Alta
	if _tiene(n, "emergencia", "hospital", "policia", "bomberos", "911", "servicio esencial", "critic"):
		return "Crítica"
	if _tiene(n, "prioridad baja", "cuando puedan", "no urgente", "sin prisa"):
		return "Baja"
	if _tiene(n, "urgente", "vip", "prioridad alta", "lo antes posible", "asap", "escalad") or (
		seg == "Empresarial" and cat == "Reparación"
	):
		return "Alta"
	return "Normal"


def elegir_tipo(catalogo: Catalogo, tec: str | None, seg: str, cat: str | None) -> TipoTrabajo | None:
	candidatos = [
		t for t in catalogo.tipos if (not cat or t.categoria == cat) and (not tec or t.tecnologia == tec)
	]
	if not candidatos:
		return None
	exactos = [t for t in candidatos if t.segmento == seg]
	elegidos = exactos or candidatos
	# Con datos incompletos solo se decide si no hay ambigüedad
	return elegidos[0] if len(elegidos) == 1 or (tec and cat) else None


def fecha(n: str, hoy: date) -> date | None:
	if m := FECHA_ISO_RE.search(n):
		return date(int(m[1]), int(m[2]), int(m[3]))
	if m := FECHA_DMY_RE.search(n):
		return date(int(m[3]), int(m[2]), int(m[1]))
	if "pasado manana" in n:
		return hoy + timedelta(days=2)
	# «mañana» es el día siguiente; «la mañana» es el horario
	if re.search(r"(?<!la )\bmanana\b", n):
		return hoy + timedelta(days=1)
	if re.search(r"\bhoy\b", n):
		return hoy
	for i, d in enumerate(DIAS):
		if re.search(rf"\b(?:el |este |proximo )?{d}\b", n):
			delta = (i - hoy.weekday()) % 7 or 7
			return hoy + timedelta(days=delta)
	return None


def _hora(h: str, m: str | None, sufijo: str | None, referencia: str | None) -> str:
	hora = int(h)
	suf = (sufijo or referencia or "").lower().replace(".", "")
	if suf == "pm" and hora < 12:
		hora += 12
	if suf == "am" and hora == 12:
		hora = 0
	if not suf and hora < 7:
		hora += 12  # «de 1 a 5» en una cita de campo es de la tarde
	return f"{hora:02d}:{int(m or 0):02d}:00"


def ventana(n: str) -> tuple[str, str] | None:
	# Fechas y teléfonos tienen números con guion que parecen horarios («11-06», «555-1234»)
	limpio = TELEFONO_RE.sub(" ", FECHA_DMY_RE.sub(" ", FECHA_ISO_RE.sub(" ", n)))
	for m in HORAS_RE.finditer(limpio):
		inicio = _hora(m[1], m[2], m[3], m[6])
		fin = _hora(m[4], m[5], m[6], m[3])
		if "06:00:00" <= inicio < fin <= "21:00:00":
			return inicio, fin
	if re.search(r"\b(?:am|a\.m\.|en la manana|por la manana|de manana)\b", n):
		return "08:00:00", "12:00:00"
	if re.search(r"\b(?:pm|p\.m\.|tarde|en la tarde|por la tarde)\b", n):
		return "12:00:00", "17:00:00"
	if "todo el dia" in n:
		return "08:00:00", "17:00:00"
	return None


def telefono(texto: str) -> str | None:
	m = TELEFONO_RE.search(texto)
	return f"{m[1]}-{m[2]}-{m[3]}" if m else None


def extraer(texto: str, catalogo: Catalogo, hoy: date) -> dict:
	"""Campos de ``QSG Orden`` encontrados en el texto, más ``faltantes`` y ``confianza``."""
	n = territorio.normalizar(texto)
	tec, seg, cat = tecnologia(n), segmento(n), categoria(n)
	tipo = elegir_tipo(catalogo, tec, seg, cat)
	muni = territorio.municipio(texto)
	datos = {
		"work_type": tipo.codigo if tipo else None,
		"technology": tipo.tecnologia if tipo else tec,
		"segment": tipo.segmento if tipo else seg,
		"category": tipo.categoria if tipo else cat,
		"priority": prioridad(n, seg, cat),
		"municipality": muni,
		"zone": (catalogo.municipio_a_zona.get(muni) or territorio.zona_sugerida(muni)) if muni else None,
		"phone": telefono(texto),
		"account_number": (m[1] if (m := CUENTA_RE.search(texto)) else None),
		"external_order_id": (m[1] if (m := ORDEN_RE.search(texto)) else None),
		"subscriber_name": (m[1].strip(" .,") if (m := NOMBRE_RE.search(texto)) else None),
		"address": (m[1].strip(" .,") if (m := DIRECCION_RE.search(texto)) else None),
		"appointment_date": None,
		"window_start": None,
		"window_end": None,
	}
	if d := fecha(n, hoy):
		datos["appointment_date"] = d.isoformat()
	if v := ventana(n):
		datos["window_start"], datos["window_end"] = v
	if muni and territorio.es_isla(muni):
		datos["nota_isla"] = f"{muni} requiere cuadrilla habilitada para el ferry."
	return completar(datos)


def completar(datos: dict) -> dict:
	obligatorios = {
		"work_type": "tipo de trabajo",
		"municipality": "municipio",
		"address": "dirección",
		"phone": "teléfono",
		"appointment_date": "fecha de la cita",
	}
	datos["faltantes"] = [etiqueta for campo, etiqueta in obligatorios.items() if not datos.get(campo)]
	datos["confianza"] = round(1 - len(datos["faltantes"]) / (len(obligatorios) + 1), 2)
	return datos


def anonimizar(texto: str) -> str:
	"""Quita teléfonos, correos, cuentas, nombres y calles antes de enviar el texto a un modelo externo.

	Conserva el municipio, que hace falta para clasificar la orden.
	"""
	t = TELEFONO_RE.sub("[TELÉFONO]", texto)
	t = CORREO_RE.sub("[CORREO]", t)
	t = CUENTA_RE.sub(lambda m: m[0].replace(m[1], "[CUENTA]"), t)
	t = NOMBRE_RE.sub(lambda m: m[0].replace(m[1], "[NOMBRE]"), t)

	def calle(m):
		muni = territorio.municipio(m[1])
		return m[0].replace(m[1], f"[DIRECCIÓN]{f' ({muni})' if muni else ''}")

	return DIRECCION_RE.sub(calle, t)
