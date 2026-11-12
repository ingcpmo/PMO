# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Tareas programadas de la inteligencia operativa (ver ``scheduler_events`` en hooks.py)."""

import frappe

from qsg_pmo.inteligencia import servicio


def _seguro(funcion, titulo):
	try:
		funcion()
	except Exception:
		frappe.log_error(title=f"QSG inteligencia: {titulo}")


def _calificar():
	from qsg_pmo.inteligencia import reglas

	reglas.calificar_contratistas()


def cada_5_minutos():
	_seguro(servicio.sincronizar_traccar, "Traccar")


def cada_15_minutos():
	_seguro(servicio.generar_recomendaciones, "recomendaciones del día")


def cada_hora():
	_seguro(servicio.actualizar_clima, "clima")
	_seguro(servicio.recomendaciones_de_manana, "recomendaciones de mañana")
	_seguro(_calificar, "calificación de contratistas")


def diaria():
	_seguro(servicio.aprender, "aprendizaje de velocidad y afinidad")
	_seguro(servicio.limpiar_ubicaciones, "limpieza de ubicaciones")
