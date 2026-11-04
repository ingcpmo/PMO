# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class QSGCuadrilla(Document):
	def on_update(self):
		update_active_crews(self.contractor)
		before = self.get_doc_before_save()
		if before and before.contractor != self.contractor:
			update_active_crews(before.contractor)

	def after_delete(self):
		update_active_crews(self.contractor)


def update_active_crews(contractor):
	if not contractor or not frappe.db.exists("QSG Contratista", contractor):
		return
	count = frappe.db.count("QSG Cuadrilla", {"contractor": contractor, "active": 1})
	frappe.db.set_value("QSG Contratista", contractor, "active_crews", count, update_modified=False)
