# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import get_datetime


class QSGIncidenciaZona(Document):
	"""Apagón, inundación, vía cerrada o alerta del clima que afecta el trabajo en una zona."""

	def validate(self):
		if self.to_datetime and get_datetime(self.to_datetime) < get_datetime(self.from_datetime):
			frappe.throw(_("La fecha «Hasta» no puede ser anterior a «Desde»."))
