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
		self.assertEqual(o1.status, "Programada")
		self.assertTrue(o1.estimated_finish)
		self.assertIn("Estado", [e.event_type for e in o1.events])
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

	def test_contratista_reasignacion_disponibilidad_y_retrabajo(self):
		date = add_days(nowdate(), 2)
		if not frappe.db.exists("QSG Contratista", "Contratista B"):
			frappe.get_doc({"doctype": "QSG Contratista", "contractor_name": "Contratista B"}).insert()
		make_crew("T-B-FTTH", "Contratista B", (18.3985, -66.1557), ["FTTH-RES", "RECONECT"], "Metro")
		self.assertEqual(frappe.db.get_value("QSG Contratista", "Contratista B", "active_crews"), 1)
		if not frappe.db.exists("QSG Contratista", "Contratista C"):
			frappe.get_doc({"doctype": "QSG Contratista", "contractor_name": "Contratista C"}).insert()
		make_crew("T-C-FTTH", "Contratista C", CAGUAS, ["FTTH-RES", "RECONECT"], "Este")

		# 1) Asignación al contratista: la orden pasa a «Asignada a contratista»
		o = make_order("T-2001", "FTTH-INST-RES", SAN_JUAN, date)
		o.contractor = "Contratista B"
		o.save()
		self.assertEqual(o.status, "Asignada a contratista")

		# 2) El plan respeta al contratista asignado aunque otra cuadrilla esté igual de cerca
		plan = frappe.get_doc({"doctype": "QSG Plan de Despacho", "plan_date": date}).insert()
		plan.generate_proposal()
		plan.reload()
		self.assertEqual({a.order: a.crew for a in plan.assignments}[o.name], "T-B-FTTH")

		# 3) Reasignación exige motivo y queda en el historial
		o.reload()
		self.assertRaises(frappe.ValidationError, o.reassign, contractor="Contratista C")
		o.reassign(crew="T-C-FTTH", reason="Contratista B sin material")
		o.reload()
		self.assertEqual((o.contractor, o.crew, o.status), ("Contratista C", "T-C-FTTH", "Programada"))
		self.assertTrue(any(e.event_type == "Reasignación" and e.reason for e in o.events))

		# 4) Una cuadrilla de otro contratista no se puede poner a mano sin reasignar
		o.crew = "T-B-FTTH"
		o.contractor = "Contratista C"
		self.assertRaises(frappe.ValidationError, o.save)

		# 5) Ausencia: la cuadrilla no se usa ese día
		frappe.get_doc(
			{
				"doctype": "QSG Disponibilidad",
				"crew": "T-B-FTTH",
				"from_date": date,
				"to_date": date,
				"reason": "Vacaciones",
			}
		).insert()
		o2 = make_order("T-2002", "FTTH-INST-RES", SAN_JUAN, date)
		o2.contractor = "Contratista B"
		o2.save()
		plan2 = frappe.get_doc({"doctype": "QSG Plan de Despacho", "plan_date": date}).insert()
		plan2.generate_proposal()
		plan2.reload()
		self.assertIn(o2.name, [u.order for u in plan2.unassigned])

		# 6) Post-operación: una orden nueva de la misma cuenta dentro de la garantía es retrabajo
		o3 = make_order("T-2003", "FTTH-RECON", SAN_JUAN, date)
		o3.account_number = "ACC-77"
		o3.crew = "T-C-FTTH"
		o3.status = "En sitio"
		o3.arrival_latitude, o3.arrival_longitude = SAN_JUAN[0] + 0.01, SAN_JUAN[1]
		o3.save()
		self.assertTrue(o3.arrival_out_of_range)  # ~1.1 km de la dirección
		for row in o3.checklist:
			row.photo = "/files/x.jpg" if row.item_type == "Foto" else None
			row.value = "Sí" if row.item_type == "Sí/No" else ("-20" if row.item_type == "Medición" else "ok")
		o3.status = "Completada"
		o3.closure_code = "COMP-OK"
		o3.save()
		self.assertTrue(o3.warranty_until)

		falla = frappe.get_doc(
			{
				"doctype": "QSG Orden",
				"customer": ensure_customer(),
				"external_order_id": "T-2004",
				"work_type": "FTTH-REP-RES",
				"subscriber_name": "Mismo cliente",
				"account_number": "ACC-77",
			}
		).insert()
		self.assertTrue(falla.is_rework)
		self.assertEqual(falla.rework_of, o3.name)
		self.assertEqual(falla.rework_contractor, "Contratista C")
		self.assertEqual(falla.priority, "Alta")

		# 7) Reportes de ocupación, capacidad y liquidación
		from qsg_pmo.qsg_pmo.report.capacidad_por_contratista.capacidad_por_contratista import (
			execute as capacidad,
		)
		from qsg_pmo.qsg_pmo.report.liquidacion_de_contratistas.liquidacion_de_contratistas import (
			execute as liquidacion,
		)
		from qsg_pmo.qsg_pmo.report.ocupacion_de_cuadrillas.ocupacion_de_cuadrillas import (
			execute as ocupacion,
		)

		_, rows = ocupacion({"date": date})
		b = next(r for r in rows if r["crew"] == "T-B-FTTH")
		self.assertTrue(b["availability"].startswith("No disponible"))
		_, rows = capacidad({"date": date})
		cb = next(r for r in rows if r["contractor"] == "Contratista B")
		self.assertEqual((cb["crews"], cb["available"]), (1, 0))
		_, rows = liquidacion({"from_date": nowdate(), "to_date": add_days(nowdate(), 3)})
		self.assertTrue(any(r["contractor"] == "Contratista C" and r["completed"] >= 1 for r in rows))

	def test_orden_duplicada(self):
		date = add_days(nowdate(), 1)
		make_order("T-DUP-1", "FTTH-RECON", SAN_JUAN, date)
		self.assertRaises(frappe.DuplicateEntryError, make_order, "T-DUP-1", "FTTH-RECON", SAN_JUAN, date)
