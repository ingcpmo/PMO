# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Datos de demostración para probar QSG PMO de punta a punta.

    bench --site <sitio> execute qsg_pmo.demo.crear

Crea dos contratistas, cuatro cuadrillas, ocho órdenes de Liberty para hoy, un plan de
despacho aprobado y un técnico de prueba (tecnico@qsg.pr / Campo2026!) que entra a /campo.
No usar en producción.
"""

import frappe
from frappe.utils import nowdate

from qsg_pmo.install import create_roles, seed
from qsg_pmo.tests.test_flujo import ensure_customer, make_crew

TECH_EMAIL = "tecnico@qsg.pr"
TECH_PASSWORD = "Campo2026!"
CUSTOMER = "Liberty Puerto Rico"

CREWS = [
	("CUA-FTTH-01", "Fibra Boricua LLC", (18.4655, -66.1057), ["FTTH-RES", "FTTH-EMP", "RECONECT"], "Metro"),
	("CUA-FTTH-02", "Fibra Boricua LLC", (18.3985, -66.1557), ["FTTH-RES", "RECONECT"], "Metro"),
	("CUA-FTTH-03", "Fibra Boricua LLC", (18.4400, -66.0200), ["FTTH-RES", "RECONECT"], "Metro"),
	("CUA-HFC-01", "Cable Este Services", (18.2341, -66.0485), ["HFC-RES", "HFC-EMP", "RECONECT"], "Este"),
]

ORDERS = [
	# id cliente, tipo, (lat, lng), ventana, zona, municipio, suscriptor, dirección
	("LPR-552301", "FTTH-INST-RES", (18.4500, -66.0700), ("08:00", "12:00"), "Metro", "San Juan", "María Torres", "Calle Loíza 1854"),
	("LPR-552302", "FTTH-INST-EMP", (18.4200, -66.0600), ("08:00", "12:00"), "Metro", "Guaynabo", "Café del Sur Inc.", "Ave. Ponce de León 1500, Local 3"),
	("LPR-552303", "FTTH-RECON", (18.3900, -66.1600), ("12:00", "17:00"), "Metro", "Bayamón", "Luis Ortiz", "Urb. Santa Rosa, Calle 9 B-12"),
	("LPR-552304", "HFC-INST-RES", (18.2400, -66.0300), ("08:00", "12:00"), "Este", "Caguas", "Carmen Ruiz", "Calle Ruiz Belvis 45"),
	("LPR-552305", "HFC-RECON", (18.2600, -66.0100), ("12:00", "17:00"), "Este", "Gurabo", "Pedro Santiago", "Bo. Navarro, Carr. 181 km 3"),
	("LPR-552306", "FTTH-INST-RES", (18.4000, -66.1400), ("12:00", "17:00"), "Metro", "Bayamón", "Ana Meléndez", "Calle Del Parque 352, Apt 4B"),
	("LPR-552307", "FTTH-RECON", (18.4489, -66.0632), ("13:00", "17:00"), "Metro", "San Juan", "Ramón Vega", "Calle Cerra 610"),
	("LPR-552308", "HFC-REP-RES", (18.0111, -66.6141), ("08:00", "12:00"), "Sur", "Ponce", "Gloria Pagán", "Calle Marina 22"),
]


@frappe.whitelist()
def crear(fecha: str | None = None):
	frappe.only_for("System Manager")
	fecha = fecha or nowdate()
	create_roles()
	seed()
	ensure_customer(CUSTOMER)
	for name in ("Fibra Boricua LLC", "Cable Este Services"):
		if not frappe.db.exists("QSG Contratista", name):
			frappe.get_doc({"doctype": "QSG Contratista", "contractor_name": name}).insert()
	for code, contractor, loc, skills, zone in CREWS:
		if not frappe.db.exists("QSG Cuadrilla", code):
			make_crew(code, contractor, loc, skills, zone)

	_tecnico("CUA-FTTH-01")

	for i, (ext, wt, loc, (s, e), zone, mun, who, addr) in enumerate(ORDERS):
		if frappe.db.exists("QSG Orden", {"customer": CUSTOMER, "external_order_id": ext}):
			continue
		frappe.get_doc(
			{
				"doctype": "QSG Orden",
				"customer": CUSTOMER,
				"external_order_id": ext,
				"work_type": wt,
				"subscriber_name": who,
				"address": addr,
				"municipality": mun,
				"zone": zone,
				"phone": f"787-555-01{i:02d}",
				"account_number": f"80{i:04d}",
				"latitude": loc[0],
				"longitude": loc[1],
				"appointment_date": fecha,
				"window_start": s + ":00",
				"window_end": e + ":00",
				"priority": "Alta" if "EMP" in wt else "Normal",
			}
		).insert()

	plan = frappe.get_doc({"doctype": "QSG Plan de Despacho", "plan_date": fecha}).insert()
	plan.generate_proposal()
	plan.reload()
	plan.approve()
	frappe.db.commit()
	return {
		"plan": plan.name,
		"tecnico": TECH_EMAIL,
		"password": TECH_PASSWORD,
		"app_campo": "/campo",
	}


def _tecnico(crew_code):
	if not frappe.db.exists("User", TECH_EMAIL):
		u = frappe.get_doc(
			{
				"doctype": "User",
				"email": TECH_EMAIL,
				"first_name": "José",
				"last_name": "Rivera",
				"send_welcome_email": 0,
				"language": "es",
			}
		)
		u.append("roles", {"role": "QSG Tecnico"})
		u.insert(ignore_permissions=True)
		u.new_password = TECH_PASSWORD
		u.save(ignore_permissions=True)
	crew = frappe.get_doc("QSG Cuadrilla", crew_code)
	if not any(m.user == TECH_EMAIL for m in crew.members):
		crew.append(
			"members",
			{"member_name": "José Rivera", "user": TECH_EMAIL, "role_in_crew": "Líder", "phone": "787-555-0101"},
		)
		crew.save()
