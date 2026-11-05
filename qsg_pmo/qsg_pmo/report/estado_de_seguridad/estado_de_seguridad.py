# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Estado de seguridad del sitio: cada control con OK, ALERTA o FALLA y qué hacer."""

from frappe import _

from qsg_pmo.seguridad.verificar import ejecutar


def execute(filters=None):
	columns = [
		{"fieldname": "estado", "label": _("Estado"), "fieldtype": "Data", "width": 90},
		{"fieldname": "area", "label": _("Área"), "fieldtype": "Data", "width": 110},
		{"fieldname": "control", "label": _("Control"), "fieldtype": "Data", "width": 280},
		{"fieldname": "detalle", "label": _("Situación"), "fieldtype": "Data", "width": 320},
		{"fieldname": "accion", "label": _("Qué hacer"), "fieldtype": "Data", "width": 380},
	]
	result = ejecutar()
	order = {"FALLA": 0, "ALERTA": 1, "OK": 2}
	data = sorted(result["controles"], key=lambda c: order[c["estado"]])
	s = result["resumen"]
	summary = [
		{"label": _("Controles en orden"), "value": s["OK"], "indicator": "Green"},
		{"label": _("Alertas"), "value": s["ALERTA"], "indicator": "Orange"},
		{"label": _("Fallas"), "value": s["FALLA"], "indicator": "Red"},
	]
	return columns, data, None, None, summary
