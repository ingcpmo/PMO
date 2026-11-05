# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Registro de eventos de seguridad.

Durante una petición web los eventos se guardan al final (``guardar_pendientes``, llamado
desde el hook ``after_request``), después del commit o del rollback de la petición. Así un
intento rechazado queda registrado aunque la petición termine en error, y el registro nunca
confirma a medias los cambios de la petición.
"""

import frappe
from frappe.utils import now_datetime

SEVERITY = {
	"Acceso denegado": "Media",
	"Límite de peticiones": "Media",
	"Archivo rechazado": "Alta",
	"Dato inválido": "Baja",
	"IP no permitida": "Alta",
	"Intento de alterar orden cerrada": "Alta",
	"Llegada fuera de rango": "Baja",
	"Otro": "Baja",
}


def registrar(event_type, detail="", reference_doctype=None, reference_name=None, severity=None):
	request = getattr(frappe.local, "request", None)
	session = getattr(frappe.local, "session", None)
	data = {
		"doctype": "QSG Evento Seguridad",
		"event_time": now_datetime(),
		"event_type": event_type,
		"severity": severity or SEVERITY.get(event_type, "Baja"),
		"user": session.user if session else None,
		"ip_address": getattr(frappe.local, "request_ip", None),
		"method": ((request.path if request else None) or frappe.form_dict.get("cmd") or "")[:140],
		"reference_doctype": reference_doctype,
		"reference_name": reference_name,
		"detail": str(detail or "")[:1000],
	}
	if request is not None:
		if not hasattr(frappe.local, "qsg_security_events"):
			frappe.local.qsg_security_events = []
		frappe.local.qsg_security_events.append(data)
	else:
		_insert(data)


def guardar_pendientes():
	events = getattr(frappe.local, "qsg_security_events", None)
	if not events:
		return
	frappe.local.qsg_security_events = []
	try:
		for data in events:
			_insert(data)
		frappe.db.commit()  # nosemgrep: transacción propia, después de cerrar la de la petición
	except Exception:
		frappe.db.rollback()
		frappe.log_error(title="QSG: no se pudo registrar un evento de seguridad")


def _insert(data):
	doc = frappe.get_doc(data)
	doc.flags.ignore_links = True
	doc.insert(ignore_permissions=True)


def denegar(message, detail=None, reference_doctype=None, reference_name=None, event_type="Acceso denegado"):
	"""Registra el evento y responde 403."""
	registrar(event_type, detail or message, reference_doctype, reference_name)
	frappe.throw(message, frappe.PermissionError)


def rechazar(message, detail=None, reference_doctype=None, reference_name=None, event_type="Dato inválido"):
	"""Registra el evento y rechaza la petición (HTTP 417)."""
	registrar(event_type, detail or message, reference_doctype, reference_name)
	frappe.throw(message, frappe.ValidationError)
