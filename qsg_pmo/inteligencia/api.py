# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""API de la inteligencia operativa: ``/api/method/qsg_pmo.inteligencia.api.<método>``.

Cada método exige un rol y tiene límite de peticiones (``qsg_pmo.seguridad.limites``), igual que la
API de campo. Los supervisores de contratista solo ven sus cuadrillas.
"""

import frappe
from frappe import _

from qsg_pmo.inteligencia import servicio as s
from qsg_pmo.seguridad.limites import limitar


@frappe.whitelist(methods=["POST"])
@limitar()
def reportar_ubicacion(
	lat=None, lng=None, precision=None, velocidad=None, bateria=None, orden=None, momento=None
) -> dict:
	"""La app de campo envía la ubicación de la cuadrilla mientras está abierta."""
	if frappe.session.user == "Guest":
		raise frappe.PermissionError
	return s.registrar_ubicacion(lat, lng, precision, velocidad, bateria, orden, momento)


@frappe.whitelist()
@limitar()
def tablero(fecha=None) -> dict:
	"""Todo lo que muestra el tablero de despacho (/despacho)."""
	frappe.only_for(s.SUPERVISION)
	return s.tablero(fecha)


@frappe.whitelist()
@limitar()
def estado_cuadrillas(fecha=None) -> list:
	frappe.only_for(s.SUPERVISION)
	return s.estado_cuadrillas(fecha, s.cuadrillas_visibles())


@frappe.whitelist()
@limitar()
def mejor_cuadrilla(orden: str, ignorar_contratista: int = 0) -> dict:
	frappe.only_for(s.DESPACHO)
	return s.mejor_cuadrilla(orden, ignorar_contratista=bool(int(ignorar_contratista or 0)))


@frappe.whitelist(methods=["POST"])
@limitar()
def reasignar(orden: str, cuadrilla: str, motivo: str, recomendacion: str | None = None) -> dict:
	"""Acepta una sugerencia: reasigna con el método existente de la orden (deja el motivo en el historial)."""
	frappe.only_for(s.DESPACHO)
	from qsg_pmo.seguridad import validacion as v

	doc = frappe.get_doc("QSG Orden", orden)
	estado = doc.reassign(crew=cuadrilla, reason=v.texto(motivo, 300) or _("Sugerencia de QSG PMO"))
	from qsg_pmo.inteligencia import avisos

	avisos.registrar(orden, cuadrilla)
	if recomendacion and frappe.db.exists("QSG Recomendacion", recomendacion):
		atender(recomendacion, "Aceptada")
	return {"orden": orden, "status": estado, "cuadrilla": cuadrilla}


@frappe.whitelist(methods=["POST"])
@limitar()
def atender(recomendacion: str, estado: str) -> dict:
	frappe.only_for(s.DESPACHO)
	if estado not in ("Aceptada", "Descartada", "Resuelta"):
		frappe.throw(_("Estado no válido."))
	doc = frappe.get_doc("QSG Recomendacion", recomendacion)
	doc.status = estado
	doc.save()
	return {"name": doc.name, "status": doc.status}


@frappe.whitelist()
@limitar()
def ranking_zonas(dias: int = 30) -> dict:
	frappe.only_for(s.DESPACHO)
	return s.ranking_zonas(min(max(int(dias or 30), 1), 365))


@frappe.whitelist()
@limitar()
def balance_zonas(fecha=None) -> dict:
	frappe.only_for(s.DESPACHO)
	return s.balance_zonas(fecha)


@frappe.whitelist()
@limitar()
def plan_materiales(fecha=None) -> dict:
	frappe.only_for(s.BODEGA)
	return s.plan_materiales(fecha)


@frappe.whitelist()
@limitar()
def pendientes(fecha=None) -> dict:
	frappe.only_for(s.SUPERVISION)
	return s.pendientes_del_dia(fecha, s.cuadrillas_visibles())


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.25)
def optimizar_plan(plan: str) -> dict:
	frappe.only_for(s.DESPACHO)
	return s.optimizar_plan(plan)


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.25)
def ajustar_materiales_del_plan(plan: str) -> list:
	"""Ajusta a mano las solicitudes de materiales de un plan aprobado al stock de los camiones."""
	frappe.only_for(s.BODEGA)
	doc = frappe.get_doc("QSG Plan de Despacho", plan)
	if doc.status != "Aprobado":
		frappe.throw(_("Primero apruebe el plan."))
	return s.ajustar_solicitudes(doc)


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.25)
def interpretar_solicitud(texto: str) -> dict:
	frappe.only_for(s.DESPACHO)
	return s.interpretar(texto)


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.25)
def crear_orden_desde_texto(texto: str, customer: str | None = None) -> dict:
	frappe.only_for(s.DESPACHO)
	return s.crear_orden_desde_texto(texto, customer)


@frappe.whitelist()
@limitar(factor=0.1)
def briefing(fecha=None) -> dict:
	frappe.only_for(s.DESPACHO)
	return s.briefing(fecha)


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.1)
def preguntar(pregunta: str) -> dict:
	frappe.only_for(s.DESPACHO)
	return s.preguntar(pregunta)


@frappe.whitelist(methods=["POST"])
@limitar()
def demo_paso() -> dict:
	"""Jornada simulada (solo en un sitio de demostración): avanza un paso."""
	frappe.only_for(s.DESPACHO)
	from qsg_pmo.inteligencia import demo_vivo

	return demo_vivo.paso()


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.1)
def demo_reiniciar() -> dict:
	"""Jornada simulada (solo en un sitio de demostración): vuelve a empezar el día."""
	frappe.only_for(s.DESPACHO)
	from qsg_pmo.inteligencia import demo_vivo

	return demo_vivo.reiniciar()


# ---------------------------------------------------------------------- perfiles, equipo, reglas y avisos
@frappe.whitelist()
@limitar()
def mi_perfil() -> dict:
	"""Perfil del usuario conectado: decide si la app abre el tablero o la ruta de campo."""
	if frappe.session.user == "Guest":
		raise frappe.PermissionError
	from qsg_pmo.inteligencia import perfiles

	return perfiles.mi_perfil()


@frappe.whitelist()
@limitar()
def mis_avisos() -> list:
	"""Órdenes asignadas a la cuadrilla del usuario que todavía no marca como «Recibida»."""
	if frappe.session.user == "Guest":
		raise frappe.PermissionError
	from qsg_pmo.inteligencia import avisos

	return avisos.mis_avisos()


@frappe.whitelist(methods=["POST"])
@limitar()
def confirmar_aviso(orden: str) -> dict:
	if frappe.session.user == "Guest":
		raise frappe.PermissionError
	from qsg_pmo.inteligencia import avisos

	return avisos.confirmar(orden)


@frappe.whitelist()
@limitar(factor=0.25)
def por_asignar(limite: int = 20) -> dict:
	"""Peticiones sin cuadrilla, cada una con sus mejores opciones calculadas por reglas."""
	frappe.only_for(s.DESPACHO)
	from qsg_pmo.inteligencia import reglas

	return reglas.por_asignar(limite)


@frappe.whitelist()
@limitar()
def perfil_contratista(contratista: str) -> dict:
	frappe.only_for(s.DESPACHO)
	from qsg_pmo.inteligencia import reglas

	return reglas.perfil_contratista(contratista)


@frappe.whitelist()
@limitar()
def reglas() -> dict:
	frappe.only_for(s.DESPACHO)
	from qsg_pmo.inteligencia import reglas as r

	return r.reglas()


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.25)
def guardar_reglas(valores) -> dict:
	from qsg_pmo.inteligencia import reglas as r

	return r.guardar_reglas(valores)


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.1)
def recalcular_calificaciones() -> list:
	frappe.only_for(("System Manager", "QSG Gerente"))
	from qsg_pmo.inteligencia import reglas as r

	return r.calificar_contratistas()


@frappe.whitelist()
@limitar()
def equipo() -> dict:
	from qsg_pmo.inteligencia import perfiles

	return perfiles.equipo()


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.25)
def guardar_usuario(
	perfil: str,
	correo: str,
	nombre: str | None = None,
	telefono: str | None = None,
	contratista: str | None = None,
	municipio: str | None = None,
	habilidades=None,
	cupo: int | None = None,
	turno_desde: str | None = None,
	turno_hasta: str | None = None,
) -> dict:
	from qsg_pmo.inteligencia import perfiles

	return perfiles.guardar_usuario(
		perfil, correo, nombre, telefono, contratista, municipio, habilidades, cupo, turno_desde, turno_hasta
	)


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.25)
def estado_usuario(correo: str, activo: int) -> dict:
	from qsg_pmo.inteligencia import perfiles

	return perfiles.estado_usuario(correo, activo)


@frappe.whitelist(methods=["POST"])
@limitar(factor=0.1)
def nueva_clave(correo: str) -> dict:
	from qsg_pmo.inteligencia import perfiles

	return perfiles.nueva_clave(correo)
