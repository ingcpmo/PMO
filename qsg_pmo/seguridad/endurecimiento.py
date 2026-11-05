# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Configuración segura del sitio. Se aplica al instalar y en cada migración.

Solo endurece: si alguien ya puso un valor más estricto, se respeta.
"""

import frappe
from frappe.utils import cint

MANAGER_ROLES = ("System Manager", "QSG Gerente", "QSG Despachador")


def aplicar():
	ss = frappe.get_single("System Settings")
	changes = {
		# bloqueo por fuerza bruta: 5 intentos y 10 minutos de espera
		"allow_consecutive_login_attempts": min(cint(ss.allow_consecutive_login_attempts) or 5, 5),
		"allow_login_after_fail": max(cint(ss.allow_login_after_fail), 600),
		# contraseñas: política activada, puntaje mínimo 3 de 4
		"enable_password_policy": 1,
		"minimum_password_score": str(max(cint(ss.minimum_password_score), 3)),
		# sesión de 12 horas (un turno), no 7 días
		"session_expiry": _shorter(ss.session_expiry, "12:00"),
		# no mostrar código fuente en los errores
		"allow_error_traceback": 0,
		# sin acceso por enlace enviado al correo
		"login_with_email_link": 0,
		# quitar ubicación y datos del teléfono de las fotos públicas
		"strip_exif_metadata_from_uploaded_images": 1,
		"logout_on_password_reset": 1,
	}
	_set_single("System Settings", ss, changes)

	ws = frappe.get_single("Website Settings")
	if not cint(ws.disable_signup):
		ws.db_set("disable_signup", 1)

	aplicar_doble_factor()


def aplicar_doble_factor():
	"""Doble factor (código por correo o app) para gerencia y despacho si la configuración lo pide."""
	try:
		required = cint(frappe.db.get_single_value("QSG Configuracion", "require_2fa_managers"))
	except Exception:
		required = 0
	if not required:
		return
	frappe.db.set_single_value("System Settings", "enable_two_factor_auth", 1)
	for role in MANAGER_ROLES:
		if frappe.db.exists("Role", role):
			frappe.db.set_value("Role", role, "two_factor_auth", 1)


def _shorter(current, target):
	def minutes(v):
		try:
			h, m = str(v or "0:0").split(":")[:2]
			return int(h) * 60 + int(m)
		except ValueError:
			return 10**9

	return current if current and minutes(current) <= minutes(target) else target


def _set_single(doctype, doc, values):
	for field, value in values.items():
		if str(doc.get(field)) != str(value):
			frappe.db.set_single_value(doctype, field, value)
	frappe.clear_cache()
