"""Prueba de integración del flujo completo: orden → plan → aprobación → cierre → evaluación."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from qsg_pmo.install import create_roles, seed

SAN_JUAN = (18.4655, -66.1057)
CAGUAS = (18.2341, -66.0485)


def ensure_tree(doctype, root, leaf, parent_field):
	"""Crea la raíz y una hoja del árbol si el asistente de configuración no se ha ejecutado."""
	if not frappe.db.exists(doctype, root):
		frappe.get_doc({"doctype": doctype, frappe.scrub(doctype) + "_name": root, "is_group": 1}).insert(
			ignore_permissions=True
		)
	if not frappe.db.exists(doctype, leaf):
		frappe.get_doc(
			{"doctype": doctype, frappe.scrub(doctype) + "_name": leaf, "is_group": 0, parent_field: root}
		).insert(ignore_permissions=True)


def ensure_customer(name="Liberty Puerto Rico (Prueba)"):
	ensure_tree("Customer Group", "All Customer Groups", "Telecom", "parent_customer_group")
	ensure_tree("Territory", "All Territories", "Puerto Rico", "parent_territory")
	if not frappe.db.exists("Customer", name):
		frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": name,
				"customer_group": "Telecom",
				"territory": "Puerto Rico",
			}
		).insert(ignore_permissions=True)
	return name


def make_crew(code, contractor, loc, skills, zone):
	if frappe.db.exists("QSG Cuadrilla", code):
		frappe.delete_doc("QSG Cuadrilla", code, force=1)
	return frappe.get_doc(
		{
			"doctype": "QSG Cuadrilla",
			"crew_code": code,
			"contractor": contractor,
			"base_zone": zone,
			"start_latitude": loc[0],
			"start_longitude": loc[1],
			"shift_start": "07:00:00",
			"shift_end": "17:00:00",
			"max_orders_per_day": 5,
			"skills": [{"skill": s} for s in skills],
		}
	).insert()


def make_order(ext, work_type, loc, date, start="08:00:00", end="12:00:00", zone="Metro"):
	return frappe.get_doc(
		{
			"doctype": "QSG Orden",
			"customer": ensure_customer(),
			"external_order_id": ext,
			"work_type": work_type,
			"subscriber_name": f"Suscriptor {ext}",
			"municipality": "San Juan",
			"zone": zone,
			"latitude": loc[0],
			"longitude": loc[1],
			"appointment_date": date,
			"window_start": start,
			"window_end": end,
		}
	).insert()


class TestFlujoQSG(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_roles()
		seed()
		if not frappe.db.exists("QSG Contratista", "Contratista Prueba"):
			frappe.get_doc({"doctype": "QSG Contratista", "contractor_name": "Contratista Prueba"}).insert()
		make_crew("T-FTTH-SJ", "Contratista Prueba", SAN_JUAN, ["FTTH-RES", "RECONECT"], "Metro")
		make_crew("T-HFC-CAG", "Contratista Prueba", CAGUAS, ["HFC-RES", "RECONECT"], "Este")

	def test_flujo_completo(self):
		date = add_days(nowdate(), 1)
		o1 = make_order("T-1001", "FTTH-INST-RES", SAN_JUAN, date)
		o2 = make_order("T-1002", "HFC-INST-RES", CAGUAS, date, zone="Este")
		o3 = make_order("T-1003", "FTTH-INST-EMP", SAN_JUAN, date)  # nadie tiene FTTH-EMP

		# La orden copia el checklist de la plantilla y calcula el SLA con el fin de la ventana
		self.assertTrue(len(o1.checklist) > 5)
		self.assertEqual(str(o1.sla_due), f"{date} 12:00:00")
		self.assertEqual(o1.sla_status, "En tiempo")

		plan = frappe.get_doc({"doctype": "QSG Plan de Despacho", "plan_date": date}).insert()
		result = plan.generate_proposal()
		plan.reload()
		by_order = {a.order: a.crew for a in plan.assignments}
		self.assertEqual(by_order.get(o1.name), "T-FTTH-SJ")
		self.assertEqual(by_order.get(o2.name), "T-HFC-CAG")
		self.assertIn(o3.name, [u.order for u in plan.unassigned])
		self.assertEqual(result["unassigned"], 1)

		plan.approve()
		o1.reload()
		self.assertEqual(o1.status, "Asignada")
		self.assertEqual(o1.crew, "T-FTTH-SJ")
		self.assertEqual(o1.contractor, "Contratista Prueba")

		# No se puede completar sin la evidencia obligatoria
		o1.status = "Completada"
		o1.closure_code = "COMP-OK"
		self.assertRaises(frappe.ValidationError, o1.save)

		# Código de cierre que no corresponde al estado
		o1.reload()
		o1.status = "Completada"
		o1.closure_code = "CLI-AUS"
		self.assertRaises(frappe.ValidationError, o1.save)

		# Medición fuera de rango no cumple
		o1.reload()
		for row in o1.checklist:
			if row.item_type == "Foto":
				row.photo = "/files/evidencia.jpg"
			elif row.item_type == "Sí/No":
				row.value = "Sí"
			elif row.item_type == "Medición":
				row.value = "-30" if row.unit == "dBm" else "500"
			else:
				row.value = "ok"
		o1.status = "En sitio"
		o1.save()
		rx = next(r for r in o1.checklist if r.unit == "dBm")
		self.assertEqual(rx.compliant, 0)

		rx.value = "-19.5"
		o1.status = "Completada"
		o1.closure_code = "COMP-OK"
		o1.save()
		self.assertEqual(o1.status, "Completada")
		self.assertTrue(o1.finished_on)

		# Encuesta y evaluación del contratista
		frappe.get_doc({"doctype": "QSG Encuesta", "order": o1.name, "rating": 0.8, "nps": 9}).insert()
		o2.reload()
		o2.status = "No completada"
		o2.closure_code = "CLI-AUS"
		o2.save()
		self.assertEqual(o2.sla_status, "Cumplido")  # cliente ausente detiene el reloj

		ev = frappe.get_doc(
			{
				"doctype": "QSG Evaluacion Contratista",
				"contractor": "Contratista Prueba",
				"period_start": nowdate(),
				"period_end": add_days(nowdate(), 2),
			}
		).insert()
		self.assertEqual(ev.orders_total, 2)
		self.assertEqual(ev.first_time_right, 100)  # la no completada fue por el cliente
		self.assertEqual(ev.avg_rating, 4)
		self.assertTrue(ev.score > 0)
		self.assertEqual(
			frappe.db.get_value("QSG Contratista", "Contratista Prueba", "current_grade"), ev.grade
		)

	def test_orden_duplicada(self):
		date = add_days(nowdate(), 1)
		make_order("T-DUP-1", "FTTH-RECON", SAN_JUAN, date)
		self.assertRaises(frappe.DuplicateEntryError, make_order, "T-DUP-1", "FTTH-RECON", SAN_JUAN, date)
