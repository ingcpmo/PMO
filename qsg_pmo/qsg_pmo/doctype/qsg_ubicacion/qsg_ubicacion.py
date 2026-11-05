# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QSGUbicacion(Document):
	"""Una lectura de GPS de una cuadrilla. La escribe el sistema y no se edita."""

	def validate(self):
		if not self.is_new():
			frappe.throw("Las ubicaciones no se pueden modificar.", frappe.PermissionError)
