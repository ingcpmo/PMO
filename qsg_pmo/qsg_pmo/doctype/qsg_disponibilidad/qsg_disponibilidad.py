# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate


class QSGDisponibilidad(Document):
	def validate(self):
		if getdate(self.to_date) < getdate(self.from_date):
			frappe.throw(_("La fecha final debe ser igual o posterior a la inicial."))
		busy = frappe.get_all(
			"QSG Orden",
			filters={
				"crew": self.crew,
				"appointment_date": ("between", (self.from_date, self.to_date)),
				"status": ("in", ("Programada", "En ruta")),
			},
			pluck="name",
		)
		if busy:
			frappe.msgprint(
				_("La cuadrilla tiene {0} órdenes programadas en esas fechas; reasígnelas: {1}").format(
					len(busy), ", ".join(busy)
				),
				indicator="orange",
				alert=True,
			)
