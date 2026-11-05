"""Modelo de lenguaje de QSG PMO: Claude (externo), uno local con Ollama, o ninguno.

Principios:

* **El modelo recomienda y explica; no decide.** Las asignaciones salen del optimizador y las
  aprueba una persona. El modelo interpreta texto libre, resume el día y responde preguntas usando
  herramientas de solo lectura.
* **Todo funciona sin modelo.** Con el proveedor «Ninguno» cada caso de uso tiene una versión por
  reglas o plantillas.
* **Datos personales protegidos.** A un modelo externo no se le envían teléfonos, correos, cuentas,
  nombres ni calles, salvo que la configuración lo permita explícitamente. Los datos del tablero que
  se le pasan son agregados (conteos, códigos de cuadrilla y de orden).
* **Lo que devuelve se valida** contra el catálogo antes de usarse.

Claude se usa con el SDK oficial ``anthropic``; el modelo por defecto es ``claude-opus-5-5`` y, en
los modelos que lo admiten, se activa el respaldo del servidor (``fallbacks="default"``): si el
modelo declina una solicitud por sus filtros de seguridad, la API la reintenta con el modelo de
respaldo recomendado en la misma llamada. Ollama se usa con su API HTTP (``/api/chat``).
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from qsg_pmo.inteligencia import solicitudes

MODELO_CLAUDE = "claude-opus-5-5"
MODELO_OLLAMA = "qwen2.5:7b"
CLAUDE, OLLAMA, NINGUNO = "Claude", "Ollama", "Ninguno"
# Modelos con respaldo del servidor ante una negativa (server-side fallback, modo "default")
CON_RESPALDO = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}
BETA_RESPALDO = "server-side-fallback-2026-07-01"

SISTEMA = (
	"Eres el asistente de operaciones de QSG PMO, la oficina que coordina cuadrillas de instalación y "
	"reparación HFC y FTTH (residencial y empresarial) para Liberty en Puerto Rico. Respondes en español "
	"claro y práctico, para despachadores, supervisores y gerentes.\n"
	"Reglas:\n"
	"- Usa solo los datos que te dan o que devuelven las herramientas. Si un dato no está, dilo; no lo "
	"inventes.\n"
	"- Recomienda acciones concretas (qué hacer, quién y cuándo). Las asignaciones las aprueba una "
	"persona: propones, no ejecutas.\n"
	"- Ten en cuenta la realidad de Puerto Rico: la cordillera central es más lenta, Vieques y Culebra "
	"dependen de la lancha, los apagones de LUMA y las alertas del clima afectan el trabajo, y el "
	"trabajo en altura se suspende con viento fuerte.\n"
	"- Prioriza: seguridad, citas y SLA en riesgo, clientes empresariales, órdenes sin asignar, "
	"pendientes de evidencia y materiales.\n"
	"- Sé breve: viñetas cortas, cifras concretas, sin relleno."
)


class ErrorIA(Exception):
	pass


@dataclass
class ConfigIA:
	proveedor: str = NINGUNO
	modelo: str | None = None
	api_key: str | None = None
	base_url: str | None = None
	timeout_s: float = 60.0
	permitir_datos_personales: bool = False


@dataclass
class Herramienta:
	"""Función de solo lectura que el modelo puede llamar. ``parametros`` es un JSON Schema de objeto."""

	nombre: str
	descripcion: str
	funcion: Callable[[dict], Any]
	parametros: dict = field(
		default_factory=lambda: {
			"type": "object",
			"properties": {},
			"required": [],
			"additionalProperties": False,
		}
	)


class Proveedor:
	nombre = NINGUNO
	externo = False

	@property
	def disponible(self) -> bool:
		return self.nombre != NINGUNO

	def completar(
		self, usuario: str, esquema: dict | None = None, esfuerzo: str = "medium", max_tokens: int = 16000
	) -> str:
		raise ErrorIA("No hay un modelo de lenguaje configurado.")

	def conversar(self, usuario: str, herramientas: list[Herramienta], max_vueltas: int = 8) -> str:
		raise ErrorIA("No hay un modelo de lenguaje configurado.")


def _ejecutar(herramientas: dict[str, Herramienta], nombre: str, entrada: dict | None) -> tuple[str, bool]:
	h = herramientas.get(nombre)
	if not h:
		return f"Herramienta desconocida: {nombre}", True
	try:
		salida = json.dumps(h.funcion(entrada or {}), ensure_ascii=False, default=str)
	except Exception as e:  # el error vuelve al modelo como resultado, no rompe la conversación
		return f"Error al consultar {nombre}: {e}", True
	return salida[:30000], False


# ---------------------------------------------------------------------- Claude
class ProveedorClaude(Proveedor):
	nombre = CLAUDE
	externo = True

	def __init__(self, config: ConfigIA, cliente=None):
		self.modelo = config.modelo or MODELO_CLAUDE
		if cliente is None:
			try:
				import anthropic
			except ImportError as e:
				raise ErrorIA("Falta el paquete «anthropic» en el servidor (pip install anthropic).") from e
			cliente = anthropic.Anthropic(
				api_key=config.api_key or None, timeout=config.timeout_s, max_retries=2
			)
		self.cliente = cliente

	def _crear(self, mensajes: list, esfuerzo: str, max_tokens: int, esquema=None, herramientas=None):
		params: dict[str, Any] = {
			"model": self.modelo,
			"max_tokens": max_tokens,
			# El prompt de sistema no cambia entre llamadas: se puede cachear
			"system": [{"type": "text", "text": SISTEMA, "cache_control": {"type": "ephemeral"}}],
			"messages": mensajes,
			"output_config": {"effort": esfuerzo},
		}
		if esquema:
			params["output_config"]["format"] = {"type": "json_schema", "schema": esquema}
		if herramientas:
			params["tools"] = herramientas
		if self.modelo in CON_RESPALDO:
			params["betas"] = [BETA_RESPALDO]
			params["fallbacks"] = "default"
		try:
			import anthropic

			errores: tuple = (anthropic.APIStatusError, anthropic.APIConnectionError)
		except ImportError:
			errores = ()
		try:
			respuesta = self.cliente.beta.messages.create(**params)
		except errores as e:
			raise ErrorIA(_mensaje_error(e)) from e
		if respuesta.stop_reason == "refusal":
			raise ErrorIA("El modelo declinó la solicitud. Reformule la pregunta.")
		return respuesta

	@staticmethod
	def _texto(respuesta) -> str:
		if respuesta.stop_reason == "max_tokens":
			raise ErrorIA("La respuesta del modelo quedó incompleta (límite de tokens).")
		return "".join(b.text for b in respuesta.content if getattr(b, "type", None) == "text").strip()

	def completar(self, usuario, esquema=None, esfuerzo="medium", max_tokens=16000) -> str:
		respuesta = self._crear([{"role": "user", "content": usuario}], esfuerzo, max_tokens, esquema=esquema)
		return self._texto(respuesta)

	def conversar(self, usuario, herramientas, max_vueltas=8) -> str:
		por_nombre = {h.nombre: h for h in herramientas}
		definiciones = [
			{"name": h.nombre, "description": h.descripcion, "input_schema": h.parametros, "strict": True}
			for h in herramientas
		]
		mensajes: list[dict] = [{"role": "user", "content": usuario}]
		for _ in range(max_vueltas):
			respuesta = self._crear(mensajes, "medium", 16000, herramientas=definiciones)
			# Se devuelve el contenido completo (incluye bloques de razonamiento) para mantener el hilo
			if respuesta.stop_reason == "pause_turn":
				mensajes.append({"role": "assistant", "content": respuesta.content})
				continue
			usos = [b for b in respuesta.content if getattr(b, "type", None) == "tool_use"]
			if respuesta.stop_reason != "tool_use" or not usos:
				return self._texto(respuesta)
			mensajes.append({"role": "assistant", "content": respuesta.content})
			resultados = []
			for uso in usos:
				salida, error = _ejecutar(por_nombre, uso.name, uso.input)
				resultados.append(
					{"type": "tool_result", "tool_use_id": uso.id, "content": salida, "is_error": error}
				)
			# Todos los resultados en un solo mensaje
			mensajes.append({"role": "user", "content": resultados})
		raise ErrorIA("La consulta necesitó demasiados pasos. Haga una pregunta más concreta.")


def _mensaje_error(e) -> str:
	codigo = getattr(e, "status_code", None)
	if codigo == 401:
		return "La clave de la API de Claude no es válida."
	if codigo == 403:
		return "La clave de la API no tiene permiso para este modelo."
	if codigo == 404:
		return "El modelo configurado no existe. Revise «Modelo» en QSG Configuracion IA."
	if codigo == 429:
		return "Se alcanzó el límite de uso de la API de Claude. Intente en un minuto."
	if codigo and codigo >= 500:
		return "El servicio de Claude no está disponible en este momento. Intente más tarde."
	if codigo:
		return f"La API de Claude rechazó la solicitud ({codigo})."
	return "No hay conexión con la API de Claude. Revise la salida a internet del servidor."


# ---------------------------------------------------------------------- Ollama (local)
class ProveedorOllama(Proveedor):
	nombre = OLLAMA
	externo = False

	def __init__(self, config: ConfigIA, transporte: Callable[[str, dict, float], dict] | None = None):
		self.modelo = config.modelo or MODELO_OLLAMA
		self.url = (config.base_url or "http://localhost:11434").rstrip("/")
		self.timeout = config.timeout_s
		self.transporte = transporte or _post_json

	def _chat(self, mensajes: list, esquema=None, herramientas=None) -> dict:
		cuerpo: dict[str, Any] = {
			"model": self.modelo,
			"messages": [{"role": "system", "content": SISTEMA}, *mensajes],
			"stream": False,
			"options": {"temperature": 0.2},
		}
		if esquema:
			cuerpo["format"] = esquema
		if herramientas:
			cuerpo["tools"] = herramientas
		try:
			return self.transporte(f"{self.url}/api/chat", cuerpo, self.timeout)
		except (urllib.error.URLError, TimeoutError, OSError) as e:
			raise ErrorIA(f"No hay conexión con Ollama en {self.url}. ¿Está encendido el servicio?") from e

	def completar(self, usuario, esquema=None, esfuerzo="medium", max_tokens=16000) -> str:
		r = self._chat([{"role": "user", "content": usuario}], esquema=esquema)
		return (r.get("message") or {}).get("content", "").strip()

	def conversar(self, usuario, herramientas, max_vueltas=8) -> str:
		por_nombre = {h.nombre: h for h in herramientas}
		definiciones = [
			{
				"type": "function",
				"function": {"name": h.nombre, "description": h.descripcion, "parameters": h.parametros},
			}
			for h in herramientas
		]
		mensajes: list[dict] = [{"role": "user", "content": usuario}]
		for _ in range(max_vueltas):
			r = self._chat(mensajes, herramientas=definiciones)
			msg = r.get("message") or {}
			llamadas = msg.get("tool_calls") or []
			if not llamadas:
				return (msg.get("content") or "").strip()
			mensajes.append(msg)
			for llamada in llamadas:
				f = llamada.get("function") or {}
				args = f.get("arguments") or {}
				if isinstance(args, str):
					try:
						args = json.loads(args)
					except ValueError:
						args = {}
				salida, _ = _ejecutar(por_nombre, f.get("name", ""), args)
				mensajes.append({"role": "tool", "content": salida, "tool_name": f.get("name", "")})
		raise ErrorIA("La consulta necesitó demasiados pasos. Haga una pregunta más concreta.")


def _post_json(url: str, cuerpo: dict, timeout: float) -> dict:
	req = urllib.request.Request(
		url, data=json.dumps(cuerpo).encode(), headers={"Content-Type": "application/json"}, method="POST"
	)
	with urllib.request.urlopen(req, timeout=timeout) as r:  # nosec B310 - URL configurada por el administrador
		return json.load(r)


def proveedor(config: ConfigIA | None) -> Proveedor:
	if not config or config.proveedor == NINGUNO:
		return Proveedor()
	if config.proveedor == CLAUDE:
		if not config.api_key:
			raise ErrorIA("Falta la clave de la API de Claude en QSG Configuracion IA.")
		return ProveedorClaude(config)
	if config.proveedor == OLLAMA:
		return ProveedorOllama(config)
	raise ErrorIA(f"Proveedor desconocido: {config.proveedor}")


# ====================================================================== casos de uso
def esquema_solicitud(catalogo: solicitudes.Catalogo) -> dict:
	"""JSON Schema de la orden interpretada. Solo campos operativos: los personales salen por reglas."""
	codigos = [t.codigo for t in catalogo.tipos]

	def opcional(tipo: dict) -> dict:
		return {"anyOf": [tipo, {"type": "null"}]}

	return {
		"type": "object",
		"properties": {
			"work_type": opcional({"type": "string", "enum": codigos}) if codigos else {"type": "null"},
			"priority": {"type": "string", "enum": list(solicitudes.PRIORIDADES)},
			"municipality": opcional({"type": "string"}),
			"appointment_date": opcional({"type": "string", "description": "AAAA-MM-DD"}),
			"window": opcional({"type": "string", "enum": ["AM", "PM", "Todo el día"]}),
			"external_order_id": opcional({"type": "string"}),
			"resumen": {"type": "string", "description": "Una línea: qué pide el cliente"},
		},
		"required": [
			"work_type",
			"priority",
			"municipality",
			"appointment_date",
			"window",
			"external_order_id",
			"resumen",
		],
		"additionalProperties": False,
	}


def interpretar_solicitud(
	texto: str, catalogo: solicitudes.Catalogo, prov: Proveedor, hoy: date, permitir_datos_personales=False
) -> dict:
	"""Texto libre -> campos de ``QSG Orden``. Reglas siempre; el modelo, si hay, completa y corrige."""
	datos = solicitudes.extraer(texto, catalogo, hoy)
	datos["fuente"] = "Reglas"
	if not prov.disponible:
		return datos
	enviar = texto if (permitir_datos_personales or not prov.externo) else solicitudes.anonimizar(texto)
	tipos = "\n".join(
		f"- {t.codigo}: {t.nombre} ({t.tecnologia}, {t.segmento}, {t.categoria})" for t in catalogo.tipos
	)
	pedido = (
		f"Hoy es {hoy.isoformat()} ({solicitudes.DIAS[hoy.weekday()]}). Interpreta esta solicitud de "
		f"servicio y devuelve el JSON pedido. Tipos de trabajo válidos:\n{tipos}\n\n"
		"Si un dato no aparece, usa null. «Crítica» solo para emergencias o servicios esenciales; "
		"una reparación empresarial sin servicio es «Alta».\n\n"
		f"Solicitud:\n<<<\n{enviar}\n>>>"
	)
	try:
		bruto = prov.completar(pedido, esquema=esquema_solicitud(catalogo), esfuerzo="low", max_tokens=8000)
		ia = json.loads(bruto)
	except (ErrorIA, ValueError) as e:
		datos["aviso_ia"] = f"Se usaron solo las reglas: {e}"
		return datos
	return _combinar(datos, ia, catalogo)


def _combinar(datos: dict, ia: dict, catalogo: solicitudes.Catalogo) -> dict:
	from qsg_pmo.inteligencia import territorio

	tipo = catalogo.tipo(ia.get("work_type"))
	if tipo:
		datos.update(
			work_type=tipo.codigo, technology=tipo.tecnologia, segment=tipo.segmento, category=tipo.categoria
		)
	if ia.get("priority") in solicitudes.PRIORIDADES:
		# Una emergencia detectada por reglas no se rebaja
		if not (datos.get("priority") == "Crítica" and ia["priority"] != "Crítica"):
			datos["priority"] = ia["priority"]
	if not datos.get("municipality") and (muni := territorio.municipio(ia.get("municipality"))):
		datos["municipality"] = muni
		datos["zone"] = catalogo.municipio_a_zona.get(muni) or territorio.zona_sugerida(muni)
	if not datos.get("appointment_date") and ia.get("appointment_date"):
		try:
			datos["appointment_date"] = date.fromisoformat(ia["appointment_date"]).isoformat()
		except ValueError:
			pass
	if not datos.get("window_start") and ia.get("window"):
		datos["window_start"], datos["window_end"] = {
			"AM": ("08:00:00", "12:00:00"),
			"PM": ("12:00:00", "17:00:00"),
			"Todo el día": ("08:00:00", "17:00:00"),
		}[ia["window"]]
	if not datos.get("external_order_id") and ia.get("external_order_id"):
		datos["external_order_id"] = str(ia["external_order_id"])[:140]
	datos["resumen"] = str(ia.get("resumen") or "")[:300]
	datos["fuente"] = "Reglas + IA"
	return solicitudes.completar(datos)


def explicar_plan(datos: dict, prov: Proveedor) -> str:
	"""Explicación del plan propuesto para el despachador. ``datos`` son agregados, sin datos personales."""
	if prov.disponible:
		try:
			return prov.completar(
				"Explica este plan de despacho al despachador en 5 a 8 viñetas: qué logra, riesgos (SLA, "
				"órdenes sin asignar y por qué, cuadrillas muy cargadas, islas, clima) y qué revisar antes "
				"de aprobar.\n\n" + json.dumps(datos, ensure_ascii=False, default=str),
				esfuerzo="medium",
			)
		except ErrorIA:
			pass
	return _plan_por_plantilla(datos)


def _plan_por_plantilla(d: dict) -> str:
	lineas = [f"• {d.get('resumen', '')}".strip()]
	sin = d.get("sin_asignar_por_motivo") or {}
	for motivo, n in sin.items():
		lineas.append(f"• {n} sin asignar: {motivo}.")
	for c in d.get("cuadrillas_cargadas", []):
		lineas.append(f"• {c} queda con la agenda llena; cualquier atraso afecta sus últimas citas.")
	for nota in d.get("notas", []):
		lineas.append(f"• {nota}")
	if d.get("incidencias"):
		lineas.append(
			f"• Zonas con incidencia: {', '.join(d['incidencias'])}. Sus órdenes no se programaron."
		)
	lineas.append("• Revise las órdenes empresariales y las de prioridad alta antes de aprobar.")
	return "\n".join(x for x in lineas if x != "•")


def briefing(datos: dict, prov: Proveedor) -> str:
	"""Resumen del día para el gerente o el despachador, con acciones priorizadas."""
	if prov.disponible:
		try:
			return prov.completar(
				"Prepara el resumen operativo de este momento: primero una línea con el estado general, "
				"luego hasta 6 acciones priorizadas (qué, quién, para cuándo) y al final los números "
				"clave.\n\n" + json.dumps(datos, ensure_ascii=False, default=str),
				esfuerzo="medium",
			)
		except ErrorIA:
			pass
	return _briefing_por_plantilla(datos)


def _briefing_por_plantilla(d: dict) -> str:
	k = d.get("kpis", {})
	acciones = []
	if k.get("sla_vencido"):
		acciones.append(f"Atender {k['sla_vencido']} órdenes con SLA vencido (despacho, ahora).")
	if k.get("sla_en_riesgo"):
		acciones.append(
			f"Proteger {k['sla_en_riesgo']} órdenes con SLA en riesgo: confirmar llegada o reasignar."
		)
	for a in d.get("alertas", [])[:3]:
		acciones.append(a)
	if d.get("pendientes_altos"):
		acciones.append(
			f"Cerrar {d['pendientes_altos']} pendientes de severidad alta (evidencia, reprogramación)."
		)
	for m in d.get("movimientos", [])[:2]:
		acciones.append(f"Mover {m['cuadrilla']} de {m['de']} a {m['a']}: {m['motivo']}")
	if d.get("materiales_faltantes"):
		acciones.append(f"Bodega: faltan materiales para {d['materiales_faltantes']} cuadrillas.")
	for i in d.get("incidencias", [])[:2]:
		acciones.append(f"Clima/incidencia: {i}")
	estado = "Operación en orden." if not acciones else f"{len(acciones)} temas requieren atención."
	numeros = ", ".join(f"{clave.replace('_', ' ')}: {valor}" for clave, valor in k.items())
	cuerpo = "\n".join(f"{i}. {a}" for i, a in enumerate(acciones[:6], start=1))
	return f"{estado}\n{cuerpo}\nNúmeros: {numeros}".strip()


def asistente(pregunta: str, herramientas: list[Herramienta], prov: Proveedor) -> str:
	"""Responde preguntas del equipo consultando datos con herramientas de solo lectura."""
	if not prov.disponible:
		return (
			"El asistente conversacional necesita un modelo de lenguaje (Claude o uno local con Ollama). "
			"Configúrelo en QSG Configuracion IA. Mientras tanto, el tablero de despacho muestra los "
			"mismos datos."
		)
	return prov.conversar(pregunta, herramientas)
