# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QSGConfiguracion(Document):
	def validate(self):
		if self.rate_limit_per_minute is not None and self.rate_limit_per_minute < 10:
			frappe.throw("El límite de peticiones no puede ser menor que 10 por minuto.")
		if self.max_photo_mb is not None and not (1 <= self.max_photo_mb <= 50):
			frappe.throw("El tamaño máximo de foto debe estar entre 1 y 50 MB.")

	def on_update(self):
		if self.has_value_changed("require_2fa_managers") and self.require_2fa_managers:
			from qsg_pmo.seguridad.endurecimiento import aplicar_doble_factor

			aplicar_doble_factor()
