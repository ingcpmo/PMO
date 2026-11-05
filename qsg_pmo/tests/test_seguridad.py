"""Módulo de seguridad: permisos por rol y por fila, órdenes cerradas, historial, archivos,
validaciones, límite de peticiones, registro de eventos y autodiagnóstico."""

from types import SimpleNamespace

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import nowdate

from qsg_pmo import api
from qsg_pmo.install import create_roles, seed
from qsg_pmo.seguridad import validacion as v
from qsg_pmo.seguridad.archivos import detectar_tipo
from qsg_pmo.seguridad.limites import LimiteExcedido, limitar
from qsg_pmo.tests.test_api import JPEG, attach_photo, ensure_user
from qsg_pmo.tests.test_flujo import CAGUAS, SAN_JUAN, make_crew, make_order

TECH = "tecnico.seg@qsg.test"
SUP = "supervisor.seg@qsg.test"
SUP_SIN = "supervisor.sin@qsg.test"
DESP = "despachador.seg@qsg.test"
PNG_FIRMA = "data:image/png;base64,iVBORw0KGgo="


def ensure_contractor(name):
	if not frappe.db.exists("QSG Contratista", name):
		frappe.get_doc({"doctype": "QSG Contratista", "contractor_name": name}).insert()


class TestSeguridad(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_roles()
		seed()
		ensure_contractor("Contratista Seg A")
		ensure_contractor("Contratista Seg B")
		ensure_user(TECH, "QSG Tecnico")
		ensure_user(SUP, "QSG Supervisor Contratista")
		ensure_user(SUP_SIN, "QSG Supervisor Contratista")
		ensure_user(DESP, "QSG Despachador")
		if not frappe.db.exists("User Permission", {"user": SUP, "allow": "QSG Contratista"}):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": SUP,
					"allow": "QSG Contratista",
					"for_value": "Contratista Seg A",
				}
			).insert(ignore_permissions=True)
		crew = make_crew("T-SEG-A", "Contratista Seg A", SAN_JUAN, ["FTTH-RES", "RECONECT"], "Metro")
		crew.append("members", {"member_name": "Técnico Seg", "user": TECH})
		crew.save()
		make_crew("T-SEG-B", "Contratista Seg B", CAGUAS, ["FTTH-RES", "RECONECT"], "Este")

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.qsg_security_events = []

	def _order(self, ext, crew, contractor):
		o = make_order(ext, "FTTH-RECON", SAN_JUAN, nowdate())
		o.contractor, o.crew, o.route_sequence = contractor, crew, 1
		o.save()
		return o

	def _events(self, event_type, name):
		return frappe.db.count("QSG Evento Seguridad", {"event_type": event_type, "reference_name": name})

	# ------------------------------------------------------------------ permisos por rol
	def test_tecnico_no_edita_ni_borra_por_rest(self):
		o = self._order("SEG-001", "T-SEG-A", "Contratista Seg A")
		frappe.set_user(TECH)
		self.assertTrue(frappe.has_permission("QSG Orden", "read", o.name))
		self.assertFalse(frappe.has_permission("QSG Orden", "write", o.name))
		self.assertFalse(frappe.has_permission("QSG Orden", "delete", o.name))
		self.assertFalse(frappe.has_permission("QSG Codigo de Cierre", "write"))
		self.assertFalse(frappe.has_permission("QSG Configuracion", "read"))
		self.assertFalse(frappe.has_permission("QSG Evaluacion Contratista", "create"))

	def test_despachador_ve_todo_y_no_borra(self):
		a = self._order("SEG-002", "T-SEG-A", "Contratista Seg A")
		b = self._order("SEG-003", "T-SEG-B", "Contratista Seg B")
		frappe.set_user(DESP)
		visible = frappe.get_list("QSG Orden", filters={"name": ["in", [a.name, b.name]]}, pluck="name")
		self.assertEqual(set(visible), {a.name, b.name})
		self.assertTrue(frappe.has_permission("QSG Orden", "write", b.name))
		self.assertFalse(frappe.has_permission("QSG Orden", "delete", b.name))

	# ------------------------------------------------------------------ permisos por fila
	def test_supervisor_solo_su_contratista(self):
		a = self._order("SEG-004", "T-SEG-A", "Contratista Seg A")
		b = self._order("SEG-005", "T-SEG-B", "Contratista Seg B")
		frappe.set_user(SUP)
		visible = frappe.get_list("QSG Orden", filters={"name": ["in", [a.name, b.name]]}, pluck="name")
		self.assertEqual(visible, [a.name])
		self.assertFalse(frappe.has_permission("QSG Orden", "read", b.name))
		self.assertRaises(frappe.PermissionError, api.orden, b.name)
		self.assertRaises(frappe.PermissionError, api.cambiar_estado, b.name, "En ruta")
		self.assertEqual(frappe.get_list("QSG Cuadrilla", filters={"name": "T-SEG-B"}), [])
		self.assertFalse(frappe.has_permission("QSG Evaluacion Contratista", "create"))

	def test_supervisor_sin_contratista_no_ve_nada(self):
		a = self._order("SEG-006", "T-SEG-A", "Contratista Seg A")
		frappe.set_user(SUP_SIN)
		self.assertEqual(frappe.get_list("QSG Orden", filters={"name": a.name}), [])
		self.assertFalse(frappe.has_permission("QSG Orden", "read", a.name))

	def test_acceso_denegado_queda_registrado(self):
		b = self._order("SEG-007", "T-SEG-B", "Contratista Seg B")
		frappe.set_user(TECH)
		self.assertRaises(frappe.PermissionError, api.orden, b.name)
		frappe.set_user("Administrator")
		self.assertEqual(self._events("Acceso denegado", b.name), 1)

	# ------------------------------------------------------------------ integridad de la orden
	def test_orden_cerrada_no_se_altera(self):
		o = self._order("SEG-008", "T-SEG-A", "Contratista Seg A")
		frappe.set_user(TECH)
		api.cambiar_estado(o.name, "En sitio")
		api.cerrar(o.name, "CLI-AUS", notas="Nadie en casa")
		frappe.set_user(DESP)
		doc = frappe.get_doc("QSG Orden", o.name)
		doc.closure_code = "COMP-OK"
		self.assertRaises(frappe.PermissionError, doc.save)
		frappe.set_user("Administrator")
		self.assertEqual(frappe.db.get_value("QSG Orden", o.name, "closure_code"), "CLI-AUS")
		self.assertEqual(self._events("Intento de alterar orden cerrada", o.name), 1)
		# reprogramar una visita fallida sí está permitido
		frappe.set_user(DESP)
		doc = frappe.get_doc("QSG Orden", o.name)
		doc.status = "Reprogramada"
		doc.save()

	def test_historial_solo_crece(self):
		o = self._order("SEG-009", "T-SEG-A", "Contratista Seg A")
		frappe.set_user(TECH)
		api.cambiar_estado(o.name, "En ruta")
		frappe.set_user(DESP)
		doc = frappe.get_doc("QSG Orden", o.name)
		self.assertTrue(doc.events)
		doc.events[0].reason = "alterado"
		self.assertRaises(frappe.PermissionError, doc.save)
		doc.reload()
		doc.events = []
		self.assertRaises(frappe.PermissionError, doc.save)

	def test_evento_de_seguridad_inmutable(self):
		frappe.local.request = None
		from qsg_pmo.seguridad.eventos import registrar

		registrar("Otro", "prueba de inmutabilidad", "QSG Orden", "SEG-INMUTABLE")
		name = frappe.db.get_value("QSG Evento Seguridad", {"reference_name": "SEG-INMUTABLE"})
		doc = frappe.get_doc("QSG Evento Seguridad", name)
		doc.detail = "borrado de huellas"
		self.assertRaises(frappe.ValidationError, doc.save)

	# ------------------------------------------------------------------ archivos
	def test_detectar_tipo_por_contenido(self):
		self.assertEqual(detectar_tipo(JPEG), "jpg")
		self.assertEqual(detectar_tipo(b"\x89PNG\r\n\x1a\n" + b"\x00" * 8), "png")
		self.assertIsNone(detectar_tipo(b"<html><script>alert(1)</script>"))
		self.assertIsNone(detectar_tipo(b"<svg onload=alert(1)>"))
		self.assertIsNone(detectar_tipo(b"MZ\x90\x00 ejecutable"))

	def test_filtro_de_archivos_en_ordenes(self):
		o = self._order("SEG-010", "T-SEG-A", "Contratista Seg A")
		self.assertTrue(attach_photo(o.name))
		bad = frappe.get_doc(
			{
				"doctype": "File",
				"file_name": "foto.jpg",
				"attached_to_doctype": "QSG Orden",
				"attached_to_name": o.name,
				"is_private": 1,
				"content": b"<html><script>alert(1)</script></html>",
			}
		)
		self.assertRaises(frappe.ValidationError, bad.insert, ignore_permissions=True)
		self.assertEqual(self._events("Archivo rechazado", o.name), 1)

	def test_foto_debe_ser_de_la_orden(self):
		a = self._order("SEG-011", "T-SEG-A", "Contratista Seg A")
		b = self._order("SEG-012", "T-SEG-A", "Contratista Seg A")
		foreign = attach_photo(b.name)
		self.assertEqual(v.foto_de_la_orden(foreign, b.name), foreign)
		self.assertRaises(frappe.ValidationError, v.foto_de_la_orden, foreign, a.name)
		self.assertRaises(frappe.ValidationError, v.foto_de_la_orden, "/private/files/otra.jpg", a.name)

	# ------------------------------------------------------------------ validaciones
	def test_texto_sin_html(self):
		self.assertNotIn("<", v.texto("<script>alert(1)</script>Ana"))
		self.assertEqual(v.texto('<img src=x onerror="alert(1)">Calle 1'), "Calle 1")
		self.assertEqual(v.texto("a\x00b\x07c"), "abc")
		self.assertEqual(len(v.texto("x" * 900, 100)), 100)

	def test_coordenadas_firma_y_numeros(self):
		self.assertEqual(v.coordenadas("18.4", "-66.1"), (18.4, -66.1))
		self.assertEqual(v.coordenadas(None, None), (None, None))
		self.assertRaises(frappe.ValidationError, v.coordenadas, 999, 0)
		self.assertRaises(frappe.ValidationError, v.coordenadas, "abc", 0)
		self.assertEqual(v.firma(PNG_FIRMA), PNG_FIRMA)
		self.assertRaises(frappe.ValidationError, v.firma, "javascript:alert(1)")
		self.assertRaises(frappe.ValidationError, v.firma, "data:image/png;base64,PHNjcmlwdD4=")
		self.assertEqual(v.numero("-18,5"), "-18.5")
		self.assertRaises(frappe.ValidationError, v.numero, "1; drop table")

	def test_ip_permitida_para_integracion(self):
		conf = frappe.get_single("QSG Configuracion")
		conf.integration_allowed_ips = "10.0.0.0/8, 200.1.2.3"
		conf.save()
		try:
			frappe.local.request_ip = "10.20.30.40"
			v.ip_permitida_para_integracion()
			frappe.local.request_ip = "200.1.2.3"
			v.ip_permitida_para_integracion()
			frappe.local.request_ip = "8.8.8.8"
			self.assertRaises(frappe.PermissionError, v.ip_permitida_para_integracion)
		finally:
			frappe.local.request_ip = None
			conf.integration_allowed_ips = ""
			conf.save()

	def test_recibir_orden_ignora_campos_no_permitidos(self):
		from qsg_pmo.tests.test_flujo import ensure_customer

		customer = ensure_customer()
		r = api.recibir_orden(
			customer=customer,
			external_order_id="SEG-MASS-1",
			work_type="FTTH-RECON",
			subscriber_name="<b>Masivo</b>",
			municipality="San Juan",
			zone="Metro",
			status="Completada",
			closure_code="COMP-OK",
			crew="T-SEG-B",
			is_rework=1,
		)
		doc = frappe.get_doc("QSG Orden", r["name"])
		self.assertEqual(doc.status, "Recibida")
		self.assertFalse(doc.closure_code or doc.crew or doc.is_rework)
		self.assertEqual(doc.subscriber_name, "Masivo")

	# ------------------------------------------------------------------ límite de peticiones
	def test_limite_de_peticiones(self):
		calls = []

		@limitar(por_minuto=3)
		def metodo_de_prueba():
			calls.append(1)
			return "ok"

		frappe.local.request = SimpleNamespace(path="/api/method/prueba")
		try:
			for _ in range(3):
				metodo_de_prueba()
			self.assertRaises(LimiteExcedido, metodo_de_prueba)
		finally:
			frappe.local.request = None
		self.assertEqual(len(calls), 3)
		queued = [e for e in frappe.local.qsg_security_events if e["event_type"] == "Límite de peticiones"]
		self.assertEqual(len(queued), 1)

	# ------------------------------------------------------------------ endurecimiento y diagnóstico
	def test_endurecimiento_aplicado(self):
		from qsg_pmo.seguridad.endurecimiento import aplicar

		aplicar()
		ss = frappe.get_single("System Settings")
		self.assertTrue(0 < ss.allow_consecutive_login_attempts <= 5)
		self.assertGreaterEqual(ss.allow_login_after_fail, 300)
		self.assertTrue(ss.enable_password_policy)
		self.assertGreaterEqual(int(ss.minimum_password_score), 3)
		self.assertFalse(ss.allow_error_traceback)
		self.assertTrue(frappe.db.get_single_value("Website Settings", "disable_signup"))

	def test_autodiagnostico(self):
		from qsg_pmo.seguridad.verificar import ejecutar

		result = ejecutar()
		controls = {c["control"]: c["estado"] for c in result["controles"]}
		for name in (
			"Técnico sin escritura directa en órdenes",
			"Cabeceras de seguridad",
			"Filtro de archivos",
			"Bloqueo por intentos fallidos",
			"Política de contraseñas",
		):
			self.assertEqual(controls[name], "OK", name)
		frappe.set_user(TECH)
		self.assertRaises(frappe.PermissionError, ejecutar)
