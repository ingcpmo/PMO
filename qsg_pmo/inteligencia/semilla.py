# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Datos complementarios de la inteligencia operativa. Se ejecuta en cada migración (``after_migrate``).

Solo agrega lo que falta; nunca cambia ni borra lo que ya existe:

* los municipios de Puerto Rico que no están en ninguna zona (la semilla original cubre 50 de 78),
* la zona «Islas» para Vieques y Culebra, que dependen de la lancha,
* el tipo de trabajo «Reparación HFC empresarial», que faltaba junto a su par FTTH,
* los valores por defecto de QSG Configuracion IA.
"""

import frappe

from qsg_pmo.inteligencia import territorio

ISLAS = ("Islas", 18.2000, -65.3800)
HFC_REP_EMP = {
	"work_type_code": "HFC-REP-EMP",
	"work_type_name": "Reparación HFC empresarial",
	"technology": "HFC",
	"segment": "Empresarial",
	"category": "Reparación",
	"duration_minutes": 120,
	"sla_hours": 8,
	"checklist_template": "Reparación",
	"skills": ["HFC-EMP"],
}


def completar():
	completar_municipios()
	agregar_tipo_hfc_empresarial()
	inicializar_configuracion()
	frappe.cache.delete_value("qsg_municipio_zona")


def completar_municipios():
	if not frappe.db.exists("DocType", "QSG Zona") or not frappe.db.count("QSG Zona"):
		return
	presentes = {
		territorio.municipio(m)
		for m in frappe.get_all(
			"QSG Zona Municipio", filters={"parenttype": "QSG Zona"}, pluck="municipality"
		)
	}
	faltan: dict[str, list[str]] = {}
	for muni, (_lat, _lng, _terreno, zona) in territorio.PUERTO_RICO.items():
		if muni not in presentes:
			faltan.setdefault(zona, []).append(muni)
	if "Islas" in faltan and not frappe.db.exists("QSG Zona", "Islas"):
		nombre, lat, lng = ISLAS
		frappe.get_doc(
			{"doctype": "QSG Zona", "zone_name": nombre, "latitude": lat, "longitude": lng}
		).insert(ignore_permissions=True)
	for zona, municipios in faltan.items():
		if not frappe.db.exists("QSG Zona", zona):
			continue
		doc = frappe.get_doc("QSG Zona", zona)
		for m in sorted(municipios):
			doc.append("municipalities", {"municipality": m})
		doc.save(ignore_permissions=True)


def agregar_tipo_hfc_empresarial():
	t = HFC_REP_EMP
	if frappe.db.exists("QSG Tipo de Trabajo", t["work_type_code"]):
		return
	if not all(frappe.db.exists("QSG Habilidad", s) for s in t["skills"]):
		return
	plantilla = (
		t["checklist_template"]
		if frappe.db.exists("QSG Plantilla Checklist", t["checklist_template"])
		else None
	)
	frappe.get_doc(
		{
			"doctype": "QSG Tipo de Trabajo",
			**{k: v for k, v in t.items() if k not in ("skills", "checklist_template")},
			"checklist_template": plantilla,
			"required_skills": [{"skill": s} for s in t["skills"]],
		}
	).insert(ignore_permissions=True)


def inicializar_configuracion():
	"""Un Single nunca guardado no tiene sus valores por defecto: se guardan la primera vez."""
	if not frappe.db.exists("DocType", "QSG Configuracion IA"):
		return
	if frappe.db.get_single_value("QSG Configuracion IA", "ai_provider"):
		return
	doc = frappe.get_single("QSG Configuracion IA")
	# Primera vez: las casillas sin guardar valen 0, así que se aplican todos los valores por defecto
	for campo in doc.meta.fields:
		if campo.default and campo.fieldtype != "Password":
			doc.set(campo.fieldname, campo.default)
	doc.flags.ignore_permissions = True
	doc.save()
