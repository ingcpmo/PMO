# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QSGEventoSeguridad(Document):
	"""Registro de eventos de seguridad. Lo escribe el sistema; nadie lo puede editar."""

	def validate(self):
		if not self.is_new():
			frappe.throw("El registro de seguridad no se puede modificar.", frappe.PermissionError)
