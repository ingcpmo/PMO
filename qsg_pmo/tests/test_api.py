"""API de la app de campo e integración: permisos por cuadrilla, flujo del técnico y recepción de órdenes."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from qsg_pmo import api
from qsg_pmo.install import create_roles, seed
from qsg_pmo.tests.test_flujo import CAGUAS, SAN_JUAN, ensure_customer, make_crew, make_order

TECH = "tecnico.api@qsg.test"


def _jpeg() -> bytes:
	import io

	from PIL import Image

	buf = io.BytesIO()
	Image.new("RGB", (8, 8), (200, 30, 30)).save(buf, "JPEG")
	return buf.getvalue()


JPEG = _jpeg()


def attach_photo(order_name, file_name="evidencia.jpg"):
	"""Foto real (firma JPEG) adjunta a la orden, como la sube la app."""
	f = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"attached_to_doctype": "QSG Orden",
			"attached_to_name": order_name,
			"is_private": 1,
			"content": JPEG,
		}
	).insert(ignore_permissions=True)
	return f.file_url


def ensure_user(email, role):
	if not frappe.db.exists("User", email):
		u = frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": "Prueba", "send_welcome_email": 0}
		)
		u.append("roles", {"role": role})
		u.insert(ignore_permissions=True)
	return email


class TestApiCampo(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_roles()
		seed()
		if not frappe.db.exists("QSG Contratista", "Contratista API"):
			frappe.get_doc({"doctype": "QSG Contratista", "contractor_name": "Contratista API"}).insert()
		ensure_user(TECH, "QSG Tecnico")
		crew = make_crew("T-API-1", "Contratista API", SAN_JUAN, ["FTTH-RES", "RECONECT"], "Metro")
		crew.append("members", {"member_name": "Técnico API", "user": TECH})
		crew.save()
		make_crew("T-API-2", "Contratista API", CAGUAS, ["FTTH-RES", "RECONECT"], "Este")

	def tearDown(self):
		frappe.set_user("Administrator")

	def _order(self, ext, crew):
		o = make_order(ext, "FTTH-RECON", SAN_JUAN, nowdate())
		o.contractor, o.crew, o.route_sequence = "Contratista API", crew, 1
		o.save()
		return o

	def test_tecnico_solo_ve_su_cuadrilla(self):
		mine = self._order("API-001", "T-API-1")
		other = self._order("API-002", "T-API-2")
		frappe.set_user(TECH)
		names = [o.name for o in api.mis_ordenes()]
		self.assertIn(mine.name, names)
		self.assertNotIn(other.name, names)
		self.assertRaises(frappe.PermissionError, api.orden, other.name)
		# también en la API REST / lista del escritorio
		visible = frappe.get_list("QSG Orden", pluck="name")
		self.assertIn(mine.name, visible)
		self.assertNotIn(other.name, visible)
		self.assertFalse(frappe.has_permission("QSG Orden", doc=other.name, ptype="read"))

	def test_flujo_del_tecnico(self):
		o = self._order("API-003", "T-API-1")
		photo = attach_photo(o.name)
		frappe.set_user(TECH)
		data = api.cambiar_estado(o.name, "En ruta")
		self.assertEqual(data["status"], "En ruta")
		data = api.cambiar_estado(o.name, "En sitio", lat=SAN_JUAN[0], lng=SAN_JUAN[1])
		self.assertEqual(data["status"], "En sitio")
		self.assertEqual(data["arrival_out_of_range"], 0)

		# sin evidencia no se puede completar
		self.assertRaises(frappe.ValidationError, api.cerrar, o.name, "COMP-OK")

		filas = []
		for r in data["checklist"]:
			if r["item_type"] == "Foto":
				filas.append({"name": r["name"], "photo": photo})
			elif r["item_type"] == "Sí/No":
				filas.append({"name": r["name"], "value": "Sí"})
			elif r["item_type"] == "Medición":
				lo, hi = r["min_value"] or None, r["max_value"] or None
				v = (lo + hi) / 2 if lo is not None and hi is not None else (lo or 0) + 1
				filas.append({"name": r["name"], "value": str(v)})
			else:
				filas.append({"name": r["name"], "value": "ok"})
		data = api.guardar_checklist(o.name, frappe.as_json(filas))
		self.assertTrue(all(r["compliant"] for r in data["checklist"] if r["mandatory"]))

		data = api.cerrar(o.name, "COMP-OK", notas="Listo", firma="data:image/png;base64,iVBORw0KGgo=")
		self.assertEqual(data["status"], "Completada")
		self.assertTrue(data["has_signature"])
		self.assertRaises(frappe.ValidationError, api.cerrar, o.name, "COMP-OK")

	def test_no_completada_por_cliente(self):
		o = self._order("API-004", "T-API-1")
		frappe.set_user(TECH)
		api.cambiar_estado(o.name, "En sitio")
		data = api.cerrar(o.name, "CLI-AUS", notas="Nadie en casa")
		self.assertEqual(data["status"], "No completada")

	def test_recibir_orden_crea_y_actualiza(self):
		customer = ensure_customer()
		r = api.recibir_orden(
			customer=customer,
			external_order_id="LIB-API-9001",
			work_type="FTTH-INST-RES",
			subscriber_name="Cliente API",
			municipality="San Juan",
			zone="Metro",
			appointment_date=nowdate(),
			window_start="08:00:00",
			window_end="12:00:00",
		)
		self.assertTrue(r["created"])
		self.assertEqual(frappe.db.get_value("QSG Orden", r["name"], "source"), "API")
		r2 = api.recibir_orden(customer=customer, external_order_id="LIB-API-9001", phone="787-555-0000")
		self.assertFalse(r2["created"])
		self.assertEqual(r2["name"], r["name"])
		self.assertEqual(api.estado_orden("LIB-API-9001", customer)["status"], "Recibida")
		# un técnico no puede crear órdenes
		frappe.set_user(TECH)
		self.assertRaises(frappe.PermissionError, api.recibir_orden, customer=customer, external_order_id="X")

	def test_resumen(self):
		data = api.resumen()
		for key in ("abiertas", "sla_en_riesgo", "sla_vencido", "en_campo", "retrabajos_abiertos"):
			self.assertIn(key, data)
