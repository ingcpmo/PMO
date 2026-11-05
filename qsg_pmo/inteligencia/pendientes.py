"""Lo que le falta a cada orden para no dejar trabajo a medias.

Las reglas de cierre de ``QSG Orden`` ya impiden completar sin evidencia; esto se adelanta y dice,
antes del cierre y durante el día, qué falta y qué hacer. También detecta órdenes trabadas
(en sitio demasiado tiempo, programadas que nadie salió a atender, fallidas sin reprogramar) y
cierres que dejaron cola en bodega.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

ALTA, MEDIA, BAJA = "Alta", "Media", "Baja"


@dataclass
class FilaChecklist:
	descripcion: str
	tipo: str
	obligatorio: bool
	valor: str | None = None
	foto: str | None = None
	cumple: bool = False


@dataclass
class OrdenAbierta:
	orden: str
	estado: str
	cuadrilla: str | None = None
	categoria: str | None = None  # Instalación, Reparación, Reconectorización…
	segmento: str | None = None
	inicio_ventana: datetime | None = None
	fin_ventana: datetime | None = None
	duracion_min: float | None = None
	salio: datetime | None = None
	llego: datetime | None = None
	termino: datetime | None = None
	checklist: list[FilaChecklist] = field(default_factory=list)
	tiene_kit: bool = False
	materiales: int = 0
	serial_equipo: str | None = None
	firma: bool = False
	codigo_cierre: str | None = None
	requiere_reprogramar: bool = False
	almacen_cuadrilla: bool = False
	salida_inventario: str | None = None
	solicitud_materiales: str | None = None
	solicitud_entregada: bool = True


def pendientes(o: OrdenAbierta, ahora: datetime) -> list[dict]:
	"""Lista de pendientes de una orden: [{codigo, severidad, mensaje, accion}]."""
	p: list[dict] = []

	def agregar(codigo, severidad, mensaje, accion):
		p.append(
			{"orden": o.orden, "codigo": codigo, "severidad": severidad, "mensaje": mensaje, "accion": accion}
		)

	en_campo = o.estado in ("Programada", "En ruta", "En sitio")
	if o.estado == "En sitio" or (o.estado == "Completada" and not o.termino):
		_evidencia(o, agregar)

	# ------------------------------------------------------------ trabadas durante el día
	if o.estado == "Programada" and o.fin_ventana and ahora > o.fin_ventana and not o.salio:
		agregar(
			"VENTANA_PERDIDA",
			ALTA,
			"La ventana de la cita terminó y nadie salió a atenderla.",
			"Llame al cliente para reprogramar y registre el código de cierre que corresponda.",
		)
	elif o.estado == "Programada" and o.inicio_ventana and ahora > o.inicio_ventana + timedelta(minutes=60):
		agregar(
			"SIN_SALIDA",
			MEDIA,
			"Pasó una hora del inicio de la ventana y la cuadrilla no ha marcado «En ruta».",
			"Confirme con la cuadrilla si va en camino.",
		)
	if o.estado == "En ruta" and o.salio and ahora - o.salio > timedelta(minutes=90):
		agregar(
			"RUTA_LARGA",
			MEDIA,
			f"Lleva {(ahora - o.salio).total_seconds() / 60:.0f} min «En ruta».",
			"Verifique la ubicación de la cuadrilla en el mapa.",
		)
	if o.estado == "En sitio" and o.llego and o.duracion_min:
		minutos = (ahora - o.llego).total_seconds() / 60
		if minutos > o.duracion_min * 1.5:
			agregar(
				"EN_SITIO_LARGO",
				MEDIA,
				f"Lleva {minutos:.0f} min en sitio (estimado {o.duracion_min:.0f}).",
				"Pregunte si necesita apoyo, material o escalar a la red.",
			)

	# ------------------------------------------------------------ después del cierre
	if (
		o.estado == "No completada"
		and o.requiere_reprogramar
		and o.termino
		and ahora - o.termino > timedelta(hours=24)
	):
		agregar(
			"SIN_REPROGRAMAR",
			ALTA,
			"Visita fallida que requiere reprogramación y lleva más de 24 h sin reprogramar.",
			"Cámbiela a «Reprogramada» para que entre al próximo plan.",
		)
	if o.estado == "Completada" and o.tiene_kit and o.almacen_cuadrilla and not o.salida_inventario:
		agregar(
			"SALIDA_INVENTARIO",
			MEDIA,
			"Completada sin salida de inventario del camión.",
			"Bodega: valide o cree la salida de inventario con los materiales y seriales.",
		)
	if en_campo and o.solicitud_materiales and not o.solicitud_entregada:
		agregar(
			"MATERIALES_SIN_RECOGER",
			ALTA if o.estado != "Programada" else MEDIA,
			"La solicitud de materiales de la cuadrilla no se ha entregado.",
			"Bodega: despache la transferencia antes de que la cuadrilla salga.",
		)
	return p


def _evidencia(o: OrdenAbierta, agregar):
	faltan = [f for f in o.checklist if f.obligatorio and not f.cumple]
	fuera = [f for f in faltan if f.tipo == "Medición" and f.valor not in (None, "")]
	sin_dato = [f for f in faltan if f not in fuera]
	if sin_dato:
		fotos = sum(1 for f in sin_dato if f.tipo == "Foto")
		texto = f"Faltan {len(sin_dato)} pasos obligatorios" + (f" ({fotos} fotos)" if fotos else "")
		agregar(
			"EVIDENCIA",
			ALTA,
			texto
			+ ": "
			+ "; ".join(f.descripcion for f in sin_dato[:4])
			+ ("…" if len(sin_dato) > 4 else ""),
			"Complete el checklist en la app antes de cerrar.",
		)
	for f in fuera:
		agregar(
			"MEDICION_FUERA",
			ALTA,
			f"{f.descripcion}: {f.valor} está fuera de rango.",
			"Revise conectores y empalmes y repita la medición; no se puede completar así.",
		)
	if o.tiene_kit and not o.materiales:
		agregar(
			"MATERIALES",
			ALTA,
			"No hay materiales ni equipos registrados y el tipo de trabajo tiene kit.",
			"Registre los materiales usados y el serial del equipo.",
		)
	if o.categoria == "Instalación" and not o.serial_equipo:
		agregar(
			"SERIAL",
			MEDIA,
			"Instalación sin serial del equipo (ONT o módem) en la orden.",
			"Escanee o escriba el serial del equipo instalado.",
		)
	if not o.firma:
		agregar(
			"FIRMA",
			MEDIA if o.segmento == "Empresarial" else BAJA,
			"Falta la firma del cliente.",
			"Pida la firma en la app al terminar.",
		)


def resumen(lista: list[dict]) -> dict:
	"""Conteo por severidad y por código para el tablero."""
	por_sev = {ALTA: 0, MEDIA: 0, BAJA: 0}
	por_codigo: dict[str, int] = {}
	for x in lista:
		por_sev[x["severidad"]] = por_sev.get(x["severidad"], 0) + 1
		por_codigo[x["codigo"]] = por_codigo.get(x["codigo"], 0) + 1
	return {"por_severidad": por_sev, "por_codigo": dict(sorted(por_codigo.items(), key=lambda kv: -kv[1]))}
