"""Inteligencia operativa sobre la base de datos: semilla, plan optimizado, incidencias, GPS, mejor
cuadrilla, pendientes, recomendaciones, órdenes desde texto y permisos."""

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, get_datetime, nowdate

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
		from unittest.mock import patch

		o = make_order("IA-030", "FTTH-INST-RES", CAROLINA, nowdate(), "00:00:00", "23:59:00")
		# Como si fueran las 9:00: el turno de las cuadrillas de prueba es de 7:00 a 17:00 y la prueba
		# no debe depender de la hora en que corre
		with patch(
			"qsg_pmo.inteligencia.servicio.now_datetime", return_value=get_datetime(f"{nowdate()} 09:00:00")
		):
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

	def test_jornada_simulada_solo_en_sitio_de_demostracion(self):
		from qsg_pmo import demo
		from qsg_pmo.inteligencia import demo_vivo

		frappe.local.conf.qsg_demo_vivo = 0
		self.addCleanup(lambda: frappe.local.conf.pop("qsg_demo_vivo", None))
		self.assertRaises(frappe.PermissionError, demo_vivo.paso)
		frappe.local.conf.qsg_demo_vivo = 1
		if not frappe.db.exists("QSG Orden", {"customer": demo.CUSTOMER, "external_order_id": "LPR-552301"}):
			demo.crear()
		self.assertGreaterEqual(demo_vivo.reiniciar()["ordenes"], 8)
		self.addCleanup(demo_vivo.reiniciar)
		cerradas = 0
		for _ in range(40):
			r = demo_vivo.paso()
			cerradas = frappe.db.count(
				"QSG Orden",
				{
					"customer": demo.CUSTOMER,
					"external_order_id": ("like", "LPR-%"),
					"status": ("in", ("Completada", "No completada")),
					"appointment_date": nowdate(),
				},
			)
			if cerradas >= 2 and r["paso"] >= 3:
				break
		self.assertGreaterEqual(cerradas, 2)
		self.assertTrue(frappe.db.exists("QSG Ubicacion", {"crew": "CUA-FTTH-01"}))
		self.assertTrue(
			frappe.db.exists("QSG Orden", {"customer": demo.CUSTOMER, "external_order_id": demo_vivo.URGENTE})
		)
		self.assertTrue(
			frappe.db.exists("QSG Recomendacion", {"rec_type": "Reasignación", "status": "Nueva"})
		)
		r = demo_vivo.reiniciar()
		self.assertFalse(
			frappe.db.exists("QSG Orden", {"customer": demo.CUSTOMER, "external_order_id": demo_vivo.URGENTE})
		)
		self.assertEqual(
			frappe.db.count(
				"QSG Orden",
				{"customer": demo.CUSTOMER, "status": "Completada", "external_order_id": ("like", "LPR-%")},
			),
			0,
		)
		self.assertEqual(r["fecha"], nowdate())

	def test_cuenta_propia_y_reanudar_otro_dia(self):
		from frappe.utils.password import check_password

		from qsg_pmo import demo
		from qsg_pmo.inteligencia import demo_vivo

		correo = "persona.prueba@ejemplo.com"
		frappe.local.conf.qsg_demo_vivo = 0
		self.addCleanup(lambda: frappe.local.conf.pop("qsg_demo_vivo", None))
		self.assertRaises(frappe.PermissionError, demo_vivo.crear_cuenta, correo)
		frappe.local.conf.qsg_demo_vivo = 1
		if not frappe.db.exists("QSG Orden", {"customer": demo.CUSTOMER, "external_order_id": "LPR-552301"}):
			demo.crear()
		self.addCleanup(lambda: frappe.delete_doc("User", correo, force=1, ignore_permissions=True))

		r = demo_vivo.crear_cuenta(" Persona.Prueba@Ejemplo.com ")
		self.assertEqual(r["usuario"], correo)
		self.assertEqual(check_password(correo, r["contrasena"]), correo)
		self.assertIn("QSG Gerente", frappe.get_roles(correo))
		# No es miembro de una cuadrilla: su GPS no se mezcla con la jornada simulada
		self.assertFalse(frappe.db.exists("QSG Cuadrilla Miembro", {"user": correo}))
		otra = demo_vivo.crear_cuenta(correo)["contrasena"]
		self.assertNotEqual(otra, r["contrasena"])
		self.assertRaises(frappe.ValidationError, demo_vivo.crear_cuenta, demo.TECH_EMAIL)
		self.assertRaises(frappe.ValidationError, demo_vivo.crear_cuenta, "no-es-correo")

		demo_vivo.reiniciar()
		self.addCleanup(demo_vivo.reiniciar)
		self.assertFalse(demo_vivo.al_reanudar()["reiniciada"])
		frappe.db.sql(
			"update `tabQSG Orden` set appointment_date = %s where customer = %s and external_order_id like %s",
			(add_days(nowdate(), -1), demo.CUSTOMER, "LPR-%"),
		)
		self.assertTrue(demo_vivo.al_reanudar()["reiniciada"])
		self.assertGreaterEqual(
			frappe.db.count(
				"QSG Orden",
				{
					"customer": demo.CUSTOMER,
					"external_order_id": ("like", "LPR-%"),
					"appointment_date": nowdate(),
				},
			),
			8,
		)

	# ------------------------------------------------------------------ perfiles, avisos y reglas (v0.5)
	def test_perfiles_y_alta_de_equipo(self):
		from frappe.utils.password import check_password

		from qsg_pmo.inteligencia import perfiles
		from qsg_pmo.www import campo

		gerente = ensure_user("gerente.ia@qsg.test", "QSG Gerente")
		correo, empresa = "contratista.nuevo@qsg.test", "Ana Campo Servicios"

		def limpiar():
			for crew in frappe.get_all("QSG Cuadrilla", filters={"contractor": empresa}, pluck="name"):
				frappe.delete_doc("QSG Cuadrilla", crew, force=1, ignore_permissions=True)
			frappe.delete_doc(
				"QSG Contratista", empresa, force=1, ignore_permissions=True, ignore_missing=True
			)
			frappe.delete_doc("User", correo, force=1, ignore_permissions=True, ignore_missing=True)

		self.addCleanup(limpiar)

		# Cada perfil abre lo suyo; desde el APK (?app=1) despacho va a su tablero y el contratista a su ruta
		frappe.set_user(TECNICO)
		self.assertEqual(api.mi_perfil()["perfil"], "Contratista")
		self.assertEqual(api.mi_perfil()["inicio"], "/campo")
		self.assertRaises(frappe.PermissionError, api.equipo)
		self.assertRaises(frappe.PermissionError, api.guardar_usuario, "Administrador", "x@qsg.test", "X")
		frappe.set_user(DESPACHADOR)
		self.assertEqual(api.mi_perfil()["inicio"], "/despacho")
		self.assertRaises(frappe.PermissionError, api.equipo)
		frappe.form_dict.app = "1"
		self.addCleanup(lambda: frappe.form_dict.pop("app", None))
		self.assertRaises(frappe.Redirect, campo.get_context, frappe._dict())
		self.assertEqual(frappe.local.flags.redirect_location, "/despacho")

		# El administrador da de alta a un contratista: usuario, empresa y cuadrilla lista para recibir
		frappe.set_user(gerente)
		self.assertEqual(api.mi_perfil()["perfil"], "Administrador")
		self.assertRaises(frappe.ValidationError, api.guardar_usuario, "Contratista", correo, "Ana Campo")
		r = api.guardar_usuario(
			"Contratista",
			correo,
			"Ana Campo",
			"787-555-0000",
			empresa,
			"Carolina",
			["FTTH-RES", "NO-EXISTE"],
			4,
		)
		self.assertTrue(r["nuevo"])
		self.assertEqual(check_password(correo, r["contrasena"]), correo)
		self.assertEqual(perfiles.perfil(correo), "Contratista")
		crew = frappe.get_doc("QSG Cuadrilla", r["cuadrilla"])
		self.assertEqual(crew.contractor, empresa)
		self.assertTrue(crew.start_latitude and crew.base_zone and crew.active)
		self.assertEqual([x.skill for x in crew.skills], ["FTTH-RES"])
		self.assertEqual(crew.max_orders_per_day, 4)
		self.assertEqual((str(crew.shift_start), str(crew.shift_end)), ("7:00:00", "17:00:00"))
		self.assertEqual([m.user for m in crew.members], [correo])
		fila = next(u for u in api.equipo()["usuarios"] if u["usuario"] == correo)
		self.assertEqual((fila["perfil"], fila["cuadrilla"], fila["activo"]), ("Contratista", crew.name, 1))

		# Guardar de nuevo no duplica la cuadrilla ni cambia la contraseña
		r2 = api.guardar_usuario(
			"Contratista",
			correo,
			"Ana Campo",
			None,
			None,
			"Bayamón",
			["FTTH-RES", "RECONECT"],
			None,
			"06:30",
			"22:00",
		)
		self.assertEqual(str(frappe.db.get_value("QSG Cuadrilla", crew.name, "shift_end")), "22:00:00")
		self.assertRaises(
			frappe.ValidationError,
			api.guardar_usuario,
			"Contratista",
			correo,
			"Ana",
			None,
			None,
			None,
			None,
			None,
			"18:00",
			"08:00",
		)
		self.assertEqual((r2["cuadrilla"], r2["contrasena"], r2["nuevo"]), (crew.name, None, False))
		self.assertEqual(frappe.db.count("QSG Cuadrilla", {"contractor": empresa}), 1)
		self.assertNotEqual(api.nueva_clave(correo)["contrasena"], r["contrasena"])

		# Desactivar al contratista saca a su cuadrilla de las recomendaciones
		api.estado_usuario(correo, 0)
		self.assertEqual(frappe.db.get_value("User", correo, "enabled"), 0)
		self.assertEqual(frappe.db.get_value("QSG Cuadrilla", crew.name, "active"), 0)
		api.estado_usuario(correo, 1)
		self.assertEqual(frappe.db.get_value("QSG Cuadrilla", crew.name, "active"), 1)

		# Nadie se da privilegios: ni al administrador del sistema, ni a sí mismo, ni a otro gerente
		self.assertRaises(frappe.PermissionError, api.nueva_clave, "Administrator")
		self.assertRaises(frappe.PermissionError, api.estado_usuario, gerente, 0)
		self.assertRaises(frappe.PermissionError, api.guardar_usuario, "Contratista", gerente, "Yo")
		otro_gerente = ensure_user("gerente2.ia@qsg.test", "QSG Gerente")
		frappe.db.set_value("User", otro_gerente, "owner", "Administrator")  # no lo creó este gerente
		self.assertRaises(frappe.PermissionError, api.nueva_clave, otro_gerente)
		self.assertRaises(frappe.ValidationError, api.guardar_usuario, "Dueño", "y@qsg.test", "Y")

	def test_aviso_al_contratista_y_confirmacion(self):
		from datetime import timedelta

		from frappe.utils import now_datetime

		o = make_order("IA-090", "FTTH-INST-RES", SAN_JUAN, nowdate(), "00:00:00", "23:59:00")
		o2 = make_order("IA-091", "FTTH-INST-RES", SAN_JUAN, nowdate(), "00:00:00", "23:59:00")
		ajeno = ensure_user("ajeno.ia@qsg.test", "QSG Tecnico")

		def cancelar():  # para no ocupar a la cuadrilla en las demás pruebas
			for name in (o.name, o2.name):
				frappe.db.set_value("QSG Orden", name, {"status": "Cancelada", "crew": None})

		self.addCleanup(cancelar)
		frappe.set_user(DESPACHADOR)
		api.reasignar(o.name, "IA-FTTH-SJ", "prueba de aviso")
		api.reasignar(o2.name, "IA-FTTH-SJ", "prueba de aviso")
		estado = {x["name"]: x["confirmacion"] for x in api.tablero()["ordenes"]}
		self.assertEqual(estado[o.name]["recibida"], 0)

		# El contratista de la cuadrilla recibe el aviso; otro contratista ni lo ve ni lo confirma
		frappe.set_user(TECNICO)
		self.assertLessEqual({o.name, o2.name}, {a["orden"] for a in api.mis_avisos()})
		frappe.set_user(ajeno)
		self.assertEqual(api.mis_avisos(), [])
		self.assertRaises(frappe.PermissionError, api.confirmar_aviso, o.name)
		self.assertRaises(frappe.PermissionError, api.por_asignar)
		self.assertRaises(frappe.PermissionError, api.tablero)
		self.assertEqual(frappe.get_list("QSG Orden", pluck="name"), [])
		for doctype in ("QSG Ubicacion", "QSG Aviso", "QSG Cuadrilla", "QSG Evaluacion Contratista"):
			self.assertFalse(frappe.has_permission(doctype, "read"), doctype)

		frappe.set_user(TECNICO)
		api.confirmar_aviso(o.name)
		self.assertNotIn(o.name, {a["orden"] for a in api.mis_avisos()})
		self.assertEqual(frappe.db.get_value("QSG Aviso", {"order": o.name}, "confirmed_by"), TECNICO)

		# Pasado el tiempo sin «Recibida», el tablero lo marca; la confirmada no aparece
		frappe.set_user("Administrator")
		frappe.db.set_value(
			"QSG Aviso", {"order": o2.name}, "assigned_on", now_datetime() - timedelta(minutes=45)
		)
		frappe.set_user(DESPACHADOR)
		tarde = {x["orden"] for x in api.tablero()["sin_confirmar"]}
		self.assertIn(o2.name, tarde)
		self.assertNotIn(o.name, tarde)
		# Reasignar vuelve a pedir la confirmación
		api.reasignar(o.name, "IA-FTTH-SJ", "se reasigna")
		frappe.set_user(TECNICO)
		self.assertIn(o.name, {a["orden"] for a in api.mis_avisos()})

	def test_por_asignar_calificacion_y_reglas(self):
		from unittest.mock import patch

		from frappe.utils import now_datetime

		from qsg_pmo.inteligencia import avisos, reglas

		o = make_order("IA-095", "FTTH-INST-RES", CAROLINA, nowdate(), "00:00:00", "23:59:00")
		frappe.set_user(DESPACHADOR)
		self.assertIn(o.name, api.tablero()["por_asignar"])
		with patch(
			"qsg_pmo.inteligencia.servicio.now_datetime", return_value=get_datetime(f"{nowdate()} 09:00:00")
		):
			r = api.por_asignar()
		fila = next(x for x in r["ordenes"] if x["name"] == o.name)
		self.addCleanup(lambda: frappe.db.set_value("QSG Orden", o.name, "status", "Cancelada"))
		mejor = fila["opciones"][0]
		self.assertIn(mejor["cuadrilla"], ("IA-FTTH-SJ", "IA-FTTH-CAG"))
		self.assertGreater(mejor["km"], 0)
		self.assertTrue(1 <= mejor["cupos"] <= 5)
		self.assertIn("categoria", mejor)

		# Reglas: despacho las ve, solo gerencia las cambia, y solo dentro de sus límites
		self.assertFalse(api.reglas()["editable"])
		self.assertRaises(frappe.PermissionError, api.guardar_reglas, {"ack_minutes": 5})
		frappe.set_user("Administrator")
		antes = avisos.minutos_para_confirmar()
		self.addCleanup(lambda: frappe.db.set_single_value("QSG Configuracion IA", "ack_minutes", antes))
		api.guardar_reglas({"ack_minutes": 7, "grade_a_bonus_minutes": 12})
		self.assertEqual(avisos.minutos_para_confirmar(), 7)
		self.assertEqual(frappe.db.get_single_value("QSG Configuracion", "grade_a_bonus_minutes"), 12)
		self.assertRaises(frappe.ValidationError, api.guardar_reglas, {"ack_minutes": 99999})
		self.assertRaises(frappe.ValidationError, api.guardar_reglas, {"ai_api_key": 1})

		# Calificación por código: con cierres recientes sale puntaje y categoría, una evaluación por mes
		cerrada = make_order("IA-096", "FTTH-INST-RES", SAN_JUAN, nowdate(), "08:00:00", "12:00:00")
		frappe.db.set_value(
			"QSG Orden",
			cerrada.name,
			{
				"contractor": CONTRATISTA,
				"crew": "IA-FTTH-SJ",
				"status": "Completada",
				"finished_on": now_datetime(),
				"appointment_date": add_days(nowdate(), -1),
				"sla_status": "Cumplido",
			},
		)
		frappe.db.set_value("QSG Contratista", CONTRATISTA, {"current_grade": None, "current_score": 0})
		nota = next(x for x in reglas.calificar_contratistas() if x["contratista"] == CONTRATISTA)
		self.assertIn(nota["categoria"], ("A", "B", "C"))
		self.assertEqual(
			frappe.db.get_value("QSG Contratista", CONTRATISTA, "current_grade"), nota["categoria"]
		)
		reglas.calificar_contratistas()
		self.assertEqual(
			frappe.db.count(
				"QSG Evaluacion Contratista", {"contractor": CONTRATISTA, "name": ("like", "AUTO-%")}
			),
			1,
		)
		p = api.perfil_contratista(CONTRATISTA)
		self.assertEqual(p["categoria"], nota["categoria"])
		self.assertGreaterEqual(p["evaluacion"]["orders_total"], 1)

	def test_briefing_y_asistente_sin_modelo(self):
		b = servicio.briefing()
		self.assertEqual(b["proveedor"], "Ninguno")
		self.assertTrue(b["texto"])
		self.assertIn("modelo de lenguaje", servicio.preguntar("¿Cómo vamos?")["respuesta"])
		self.assertTrue(servicio.ranking_zonas(30) is not None)
		self.assertIn("zonas", servicio.balance_zonas())
		self.assertIn("cuadrillas", servicio.plan_materiales())
		self.assertLessEqual(len(servicio.estado_cuadrillas()), frappe.db.count("QSG Cuadrilla"))
