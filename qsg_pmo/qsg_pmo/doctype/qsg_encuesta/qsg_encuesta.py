# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QSGEncuesta(Document):
	def validate(self):
		if self.nps is not None and not 0 <= self.nps <= 10:
			frappe.throw("La recomendación debe estar entre 0 y 10.")

	def on_update(self):
		frappe.db.set_value("QSG Orden", self.order, "customer_rating", self.rating, update_modified=False)
