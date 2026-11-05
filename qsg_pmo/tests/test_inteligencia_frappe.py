"""Inteligencia operativa sobre la base de datos: semilla, plan optimizado, incidencias, GPS, mejor
cuadrilla, pendientes, recomendaciones, órdenes desde texto y permisos."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, nowdate

from qsg_pmo.install import create_roles, seed
from qsg_pmo.inteligencia import api, semilla, servicio, territorio
from qsg_pmo.tests.test_api import ensure_user
from qsg_pmo.tests.test_flujo import CAGUAS, SAN_JUAN, ensure_customer, make_crew, make_order

CONTRATISTA = "Contratista IA"
TECNICO = "tecnico.ia@qsg.test"
DESPACHADOR = "despachador.ia@qsg.test"
CAROLINA = (18.3808, -65.9574)


class TestInteligenciaFrappe(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		create_roles()
		seed()
		semilla.completar()
		if not frappe.db.exists("QSG Contratista", CONTRATISTA):
			frappe.get_doc({"doctype": "QSG Contratista", "contractor_name": CONTRATISTA}).insert()
		ensure_user(TECNICO, "QSG Tecnico")
		ensure_user(DESPACHADOR, "QSG Despachador")
		crew = make_crew("IA-FTTH-SJ", CONTRATISTA, SAN_JUAN, ["FTTH-RES", "RECONECT"], "Metro")
		crew.append("members", {"member_name": "Técnico IA", "user": TECNICO})
		crew.save()
		make_crew("IA-FTTH-CAG", CONTRATISTA, CAGUAS, ["FTTH-RES", "RECONECT"], "Este")

	def setUp(self):
		# El sitio puede tener la demostración: solo cuentan las cuadrillas de esta prueba
		otras = frappe.get_all(
			"QSG Cuadrilla", filters={"active": 1, "contractor": ("!=", CONTRATISTA)}, pluck="name"
		)
		for name in otras:
			frappe.db.set_value("QSG Cuadrilla", name, "active", 0)

		def reactivar():
			for name in otras:
				frappe.db.set_value("QSG Cuadrilla", name, "active", 1)

		self.addCleanup(reactivar)

	def tearDown(self):
		frappe.set_user("Administrator")
		frappe.local.qsg_security_events = []

	# ------------------------------------------------------------------ semilla
	def test_semilla_completa_sin_cambiar_lo_existente(self):
		municipios = {
			territorio.municipio(m)
			for m in frappe.get_all(
				"QSG Zona Municipio", filters={"parenttype": "QSG Zona"}, pluck="municipality"
			)
		}
		self.assertEqual(len(municipios - {None}), 78)
		self.assertTrue(frappe.db.exists("QSG Zona", "Islas"))
		self.assertTrue(frappe.db.exists("QSG Tipo de Trabajo", "HFC-REP-EMP"))
		# San Juan sigue en Metro, como en la semilla original
		self.assertEqual(servicio.municipio_a_zona()["San Juan"], "Metro")
		cfg = frappe.get_single("QSG Configuracion IA")
		self.assertEqual((cfg.ai_provider, cfg.use_terrain, cfg.net_material_requests), ("Ninguno", 1, 0))
		semilla.completar()  # idempotente
		self.assertEqual(frappe.db.count("QSG Zona", {"name": "Islas"}), 1)

	# ------------------------------------------------------------------ plan optimizado
	def _plan(self, fecha):
		return frappe.get_doc({"doctype": "QSG Plan de Despacho", "plan_date": fecha}).insert()

	def test_optimizar_plan_y_aprobar_como_siempre(self):
		fecha = add_days(nowdate(), 3)
		o1 = make_order("IA-001", "FTTH-INST-RES", SAN_JUAN, fecha, "08:00:00", "17:00:00")
		o2 = make_order("IA-002", "FTTH-INST-RES", CAGUAS, fecha, "08:00:00", "17:00:00", zone="Este")
		o3 = make_order("IA-003", "FTTH-RECON", CAROLINA, fecha, "08:00:00", "17:00:00")
		plan = self._plan(fecha)
		r = servicio.optimizar_plan(plan.name)
		plan.reload()
		self.assertEqual(plan.status, "Propuesto")
		self.assertEqual(r["assigned"], 3)
		por_orden = {a.order: a.crew for a in plan.assignments}
		self.assertEqual(por_orden[o2.name], "IA-FTTH-CAG")
		self.assertEqual(por_orden[o1.name], "IA-FTTH-SJ")
		self.assertIn("órdenes asignadas", r["resumen"])
		self.assertTrue(r["explicacion"])
		# La aprobación existente funciona igual sobre el plan optimizado
		plan.approve()
		o3.reload()
		self.assertEqual(o3.status, "Programada")
		self.assertTrue(o3.crew)

	def test_zona_con_incidencia_no_recibe_trabajo(self):
		fecha = add_days(nowdate(), 4)
		inc = frappe.get_doc(
			{
				"doctype": "QSG Incidencia Zona",
				"zone": "Este",
				"incident_type": "Apagón LUMA",
				"impact": "Suspender",
				"from_datetime": f"{fecha} 00:00:00",
				"to_datetime": f"{fecha} 23:59:00",
			}
		).insert()
		self.addCleanup(lambda: frappe.delete_doc("QSG Incidencia Zona", inc.name, force=1))
		o = make_order("IA-010", "FTTH-INST-RES", CAGUAS, fecha, "08:00:00", "17:00:00", zone="Este")
		plan = self._plan(fecha)
		servicio.optimizar_plan(plan.name)
		plan.reload()
		motivos = {u.order: u.reason for u in plan.unassigned}
		self.assertIn("Apagón LUMA", motivos[o.name])

	def test_ajuste_de_materiales_apagado_no_cambia_nada(self):
		plan = frappe._dict(status="Aprobado", name="X")
		plan.has_value_changed = lambda campo: True
		# Con la casilla apagada (valor de fábrica) el hook no toca las solicitudes
		self.assertIsNone(servicio.al_actualizar_plan(plan))

	# ------------------------------------------------------------------ GPS, estado y mejor cuadrilla
	def test_gps_del_tecnico_y_estado(self):
		hoy = nowdate()
		o = make_order("IA-020", "FTTH-INST-RES", CAROLINA, hoy, "08:00:00", "23:00:00")
		o.contractor, o.crew = CONTRATISTA, "IA-FTTH-SJ"
		o.save()
		frappe.set_user(TECNICO)
		r = api.reportar_ubicacion(lat=18.43, lng=-66.06, precision=10)
		self.assertTrue(r["ok"])
		frappe.set_user("Administrator")
		ping = frappe.get_last_doc("QSG Ubicacion", filters={"crew": "IA-FTTH-SJ"})
		self.assertEqual(ping.zone, "Metro")
		self.assertEqual(ping.user, TECNICO)
		estado = {e["cuadrilla"]: e for e in servicio.estado_cuadrillas(hoy)}
		self.assertEqual(estado["IA-FTTH-SJ"]["siguiente_orden"], o.name)
		# Cuadrilla con órdenes y sin GPS
		o2 = make_order("IA-021", "FTTH-INST-RES", CAGUAS, hoy, "08:00:00", "23:00:00", zone="Este")
		o2.contractor, o2.crew = CONTRATISTA, "IA-FTTH-CAG"
		o2.save()
		estado = {e["cuadrilla"]: e for e in servicio.estado_cuadrillas(hoy)}
		self.assertIn("Sin ubicación", [a["tipo"] for a in estado["IA-FTTH-CAG"]["alertas"]])

	def test_usuario_sin_cuadrilla_no_registra_gps(self):
		frappe.set_user(DESPACHADOR)
		self.assertFalse(api.reportar_ubicacion(lat=18.4, lng=-66.1)["ok"])

	def test_mejor_cuadrilla(self):
		o = make_order("IA-030", "FTTH-INST-RES", CAROLINA, nowdate(), "00:00:00", "23:59:00")
		r = servicio.mejor_cuadrilla(o.name)
		self.assertTrue(r["opciones"])
		self.assertEqual(r["opciones"][0]["cuadrilla"], "IA-FTTH-SJ")

	# ------------------------------------------------------------------ pendientes y recomendaciones
	def test_pendientes_de_una_orden_en_sitio(self):
		o = make_order("IA-040", "FTTH-INST-RES", SAN_JUAN, nowdate(), "08:00:00", "23:00:00")
		o.contractor, o.crew = CONTRATISTA, "IA-FTTH-SJ"
		o.save()
		o.status = "En sitio"
		o.save()
		codigos = {p["codigo"] for p in servicio.pendientes_del_dia()["pendientes"] if p["orden"] == o.name}
		self.assertIn("EVIDENCIA", codigos)

	def test_recomendacion_no_se_duplica(self):
		a = servicio.recomendar("Zona", "Prueba de clave", "detalle", clave="PRUEBA:IA")
		b = servicio.recomendar("Zona", "Prueba de clave", "otro detalle", clave="PRUEBA:IA")
		self.assertEqual(a, b)
		self.assertEqual(frappe.db.get_value("QSG Recomendacion", a, "detail"), "otro detalle")
		servicio.generar_recomendaciones()
		servicio.recomendaciones_de_manana()

	# ------------------------------------------------------------------ órdenes desde texto
	def test_orden_desde_texto_sin_duplicar(self):
		texto = (
			"Cliente: Panadería La Esquina\nDirección: Calle 5, Carolina\nTel 787-555-0101\n"
			"Instalación de fibra residencial pasado mañana en la tarde"
		)
		d = servicio.interpretar(texto)
		self.assertEqual(d["work_type"], "FTTH-INST-RES")
		self.assertEqual(d["zone"], "Metro")
		cliente = ensure_customer()
		a = servicio.crear_orden_desde_texto(texto, cliente)
		b = servicio.crear_orden_desde_texto(texto, cliente)
		self.assertTrue(a["created"])
		self.assertEqual(a["name"], b["name"])
		self.assertEqual(
			str(frappe.db.get_value("QSG Orden", a["name"], "window_start")).zfill(8)[:5], "12:00"
		)

	# ------------------------------------------------------------------ permisos
	def test_tecnico_no_ve_el_tablero(self):
		frappe.set_user(TECNICO)
		self.assertRaises(frappe.PermissionError, api.tablero)
		self.assertRaises(frappe.PermissionError, api.optimizar_plan, "X")
		frappe.set_user(DESPACHADOR)
		t = api.tablero()
		self.assertIn("cuadrillas", t)
		self.assertIn("IA-FTTH-SJ", [c["cuadrilla"] for c in t["cuadrillas"]])

	def test_briefing_y_asistente_sin_modelo(self):
		b = servicio.briefing()
		self.assertEqual(b["proveedor"], "Ninguno")
		self.assertTrue(b["texto"])
		self.assertIn("modelo de lenguaje", servicio.preguntar("¿Cómo vamos?")["respuesta"])
		self.assertTrue(servicio.ranking_zonas(30) is not None)
		self.assertIn("zonas", servicio.balance_zonas())
		self.assertIn("cuadrillas", servicio.plan_materiales())
		self.assertLessEqual(len(servicio.estado_cuadrillas()), frappe.db.count("QSG Cuadrilla"))
