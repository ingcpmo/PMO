# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class QSGRecomendacion(Document):
	"""Recomendación de la inteligencia operativa: la propone el sistema y la decide una persona."""

	def validate(self):
		if self.has_value_changed("status") and self.status in ("Aceptada", "Descartada", "Resuelta"):
			self.resolved_by = frappe.session.user
			self.resolved_on = now_datetime()
