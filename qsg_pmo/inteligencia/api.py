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
