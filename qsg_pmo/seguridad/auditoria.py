# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Preparación de usuarios y órdenes para la simulación y las pruebas de ataque.

    bench --site <sitio> execute qsg_pmo.seguridad.auditoria.preparar

Crea (si no existen) los usuarios de prueba de cada rol, las claves de API del usuario de
integración de Liberty y deja órdenes listas: una de la cuadrilla del técnico, una de otra
cuadrilla y otro contratista, y una cerrada. Devuelve todo en JSON para los scripts de
``auditoria/``. Solo para sitios de prueba.
"""

import frappe
from frappe.utils import nowdate

from qsg_pmo.demo import CUSTOMER, TECH_EMAIL, TECH_PASSWORD
from qsg_pmo.demo import crear as crear_demo

PASSWORD = "Prueba-QSG-2026!"
USERS = {
	"gerente": ("gerente@qsg.pr", "Gerardo", ["QSG Gerente"]),
	"despachador": ("despachador@qsg.pr", "Diana", ["QSG Despachador"]),
	"supervisor": ("supervisor@fibraboricua.pr", "Samuel", ["QSG Supervisor Contratista"]),
	"bodega": ("bodega@qsg.pr", "Berta", ["QSG Bodega"]),
	"liberty": ("integracion@liberty.pr", "Integración Liberty", ["QSG Despachador"]),
	"victima": ("victima@qsg.pr", "Víctor", ["QSG Tecnico"]),
}


def _user(email, first_name, roles):
	if not frappe.db.exists("User", email):
		u = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": first_name, "send_welcome_email": 0}
		)
		for r in roles:
			u.append("roles", {"role": r})
		u.insert(ignore_permissions=True)
	u = frappe.get_doc("User", email)
	u.new_password = PASSWORD
	u.save(ignore_permissions=True)
	return u


def preparar() -> dict:
	frappe.only_for("System Manager")
	if not frappe.db.exists("QSG Cuadrilla", "CUA-FTTH-01"):
		crear_demo()
	users = {k: _user(*v).name for k, v in USERS.items()}

	# El supervisor solo trabaja para Fibra Boricua LLC
	if not frappe.db.exists(
		"User Permission",
		{"user": users["supervisor"], "allow": "QSG Contratista", "for_value": "Fibra Boricua LLC"},
	):
		frappe.get_doc(
			{
				"doctype": "User Permission",
				"user": users["supervisor"],
				"allow": "QSG Contratista",
				"for_value": "Fibra Boricua LLC",
			}
		).insert(ignore_permissions=True)

	# Claves de API para la integración de Liberty
	liberty = frappe.get_doc("User", users["liberty"])
	secret = frappe.generate_hash(length=15)
	liberty.api_key = liberty.api_key or frappe.generate_hash(length=15)
	liberty.api_secret = secret
	liberty.save(ignore_permissions=True)

	# Deja todo como al principio para poder repetir las pruebas
	frappe.db.set_value("QSG Codigo de Cierre", "CLI-AUS", "billable", 1)
	# Frappe bloquea por usuario y también por IP: se limpia todo el registro de intentos
	frappe.cache.delete_value(["login_failed_count", "login_failed_time", "locked_account_time"])

	today = nowdate()
	own = _order("AUD-PROPIA", "CUA-FTTH-01", "Fibra Boricua LLC", today)
	deletable = _order("AUD-BORRAR", "CUA-FTTH-01", "Fibra Boricua LLC", today)
	other = _order("AUD-AJENA", "CUA-HFC-01", "Cable Este Services", today, work_type="HFC-RECON")
	closed = _closed_order(today)
	frappe.db.commit()
	return {
		"password": PASSWORD,
		"tecnico": {"user": TECH_EMAIL, "password": TECH_PASSWORD},
		"users": users,
		"liberty_token": f"{liberty.api_key}:{secret}",
		"orden_propia": own,
		"orden_ajena": other,
		"orden_cerrada": closed,
		"orden_borrable": deletable,
		"cliente": CUSTOMER,
	}


def _order(ext, crew, contractor, day, work_type="FTTH-RECON"):
	name = frappe.db.get_value("QSG Orden", {"customer": CUSTOMER, "external_order_id": ext})
	if name:
		frappe.db.set_value(
			"QSG Orden",
			name,
			{
				"status": "Programada",
				"arrival_latitude": 0,
				"arrival_longitude": 0,
				"arrival_out_of_range": 0,
				"closure_code": None,
			},
		)
		frappe.db.sql(
			"update `tabQSG Resultado Checklist` set value=null, photo=null, compliant=0 where parent=%s",
			name,
		)
		return name
	doc = frappe.get_doc(
		{
			"doctype": "QSG Orden",
			"customer": CUSTOMER,
			"external_order_id": ext,
			"work_type": work_type,
			"subscriber_name": f"Cliente {ext}",
			"municipality": "San Juan",
			"zone": "Metro",
			"latitude": 18.45,
			"longitude": -66.07,
			"appointment_date": day,
			"window_start": "08:00:00",
			"window_end": "17:00:00",
			"contractor": contractor,
			"crew": crew,
			"route_sequence": 9,
		}
	).insert(ignore_permissions=True)
	return doc.name


def _closed_order(day):
	name = frappe.db.get_value("QSG Orden", {"customer": CUSTOMER, "external_order_id": "AUD-CERRADA"})
	if name:
		return name
	doc = frappe.get_doc(
		{
			"doctype": "QSG Orden",
			"customer": CUSTOMER,
			"external_order_id": "AUD-CERRADA",
			"work_type": "FTTH-RECON",
			"subscriber_name": "Cliente cerrado",
			"municipality": "San Juan",
			"zone": "Metro",
			"latitude": 18.45,
			"longitude": -66.07,
			"appointment_date": day,
			"window_start": "08:00:00",
			"window_end": "17:00:00",
			"contractor": "Fibra Boricua LLC",
			"crew": "CUA-FTTH-01",
		}
	).insert(ignore_permissions=True)
	doc.status = "No completada"
	doc.closure_code = "CLI-AUS"
	doc.save(ignore_permissions=True)
	return doc.name
