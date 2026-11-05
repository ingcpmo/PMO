"""Pruebas del núcleo de inteligencia (sin base de datos)."""

import json
import random
import unittest
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from typing import ClassVar

from qsg_pmo.assignment.engine import REASON_NO_SKILL, Settings
from qsg_pmo.inteligencia import (
	clima,
	ia,
	materiales,
	pendientes,
	rutas,
	solicitudes,
	territorio,
	tracking,
	zonas,
)
from qsg_pmo.inteligencia.optimizacion import REASON_ISLA, Cuadrilla, Opciones, Trabajo, elegible, optimizar

DAY = datetime(2026, 11, 6)


def trabajo(order, muni, skills=("FTTH-RES",), ws=8, we=12, dur=90, **kw):
	lat, lng, ter, zona = territorio.PUERTO_RICO[muni]
	return Trabajo(
		order=order,
		latitude=lat,
		longitude=lng,
		window_start=DAY.replace(hour=ws),
		window_end=DAY.replace(hour=we),
		duration_minutes=dur,
		skills=set(skills),
		zone=kw.pop("zone", zona),
		terreno=ter,
		**kw,
	)


def cuadrilla(crew, muni, skills=("FTTH-RES", "RECONECT"), max_orders=6, **kw):
	lat, lng, ter, zona = territorio.PUERTO_RICO[muni]
	return Cuadrilla(
		crew=crew,
		latitude=lat,
		longitude=lng,
		shift_start=DAY.replace(hour=7),
		shift_end=DAY.replace(hour=17),
		skills=set(skills),
		max_orders=max_orders,
		zone=kw.pop("zone", zona),
		terreno=ter,
		**kw,
	)


def instancia(seed, n_jobs=24, n_crews=8):
	rnd = random.Random(seed)
	munis = [m for m, v in territorio.PUERTO_RICO.items() if v[2] != territorio.ISLA]
	tipos = [
		(("FTTH-RES",), 120, "Residencial"),
		(("HFC-RES",), 90, "Residencial"),
		(("FTTH-EMP",), 180, "Empresarial"),
		(("FTTH-RES", "RECONECT"), 60, "Residencial"),
	]
	jobs = []
	for i in range(n_jobs):
		sk, dur, seg = rnd.choice(tipos)
		ws = rnd.choice([8, 8, 12, 13])
		jobs.append(trabajo(f"O{i:03d}", rnd.choice(munis), sk, ws, ws + 4, dur, segmento=seg))
	bases = ["San Juan", "Caguas", "Ponce", "Mayagüez", "Arecibo", "Humacao", "Bayamón", "Cayey"]
	skills = [
		("FTTH-RES", "RECONECT"),
		("HFC-RES", "RECONECT"),
		("FTTH-RES", "FTTH-EMP", "RECONECT"),
		("FTTH-RES", "HFC-RES", "RECONECT"),
	]
	crews = [cuadrilla(f"C{k:02d}", bases[k % len(bases)], rnd.choice(skills)) for k in range(n_crews)]
	return jobs, crews


class TestTerritorio(unittest.TestCase):
	def test_78_municipios_con_zona(self):
		self.assertEqual(len(territorio.PUERTO_RICO), 78)
		for muni, (lat, lng, _terreno, zona) in territorio.PUERTO_RICO.items():
			self.assertTrue(17.8 < lat < 18.6 and -67.3 < lng < -65.2, muni)
			self.assertIn(zona, territorio.ZONAS_VECINAS, muni)

	def test_reconoce_municipio_escrito_de_cualquier_forma(self):
		self.assertEqual(territorio.municipio("mayaguez"), "Mayagüez")
		self.assertEqual(territorio.municipio("BO. PUEBLO, RIO GRANDE PR 00745"), "Río Grande")
		self.assertEqual(territorio.municipio("Calle 3, Sabana Grande"), "Sabana Grande")
		self.assertIsNone(territorio.municipio("Miami"))

	def test_islas_y_terreno(self):
		self.assertTrue(territorio.es_isla("Vieques"))
		self.assertEqual(territorio.terreno("Utuado"), territorio.MONTANOSO)
		self.assertEqual(
			territorio.municipios_en_texto("Caguas; Cayey y Cidra"), {"Caguas", "Cayey", "Cidra"}
		)


class TestRutas(unittest.TestCase):
	def test_montana_ferry_y_velocidad_medida(self):
		m = rutas.ModeloViaje()
		a, b = (18.20, -66.60), (18.25, -66.70)
		llano = m.minutos(a, b)
		self.assertGreater(m.minutos(a, b, territorio.MONTANOSO, territorio.LLANO), llano)
		self.assertGreater(m.minutos(a, b, territorio.LLANO, territorio.ISLA), llano + 100)
		m.velocidad_zona["Centro"] = 70.0
		self.assertLess(m.minutos(a, b, territorio.MONTANOSO, territorio.MONTANOSO, "Centro"), llano)

	def test_tabla_osrm(self):
		puntos = [(18.4, -66.1), (18.2, -66.0)]
		self.assertIn(
			"-66.100000,18.400000;-66.000000,18.200000", rutas.url_tabla_osrm("http://osrm:5000/", puntos)
		)
		tabla = rutas.leer_tabla_osrm({"code": "Ok", "durations": [[0, 1800], [1750, 0]]}, puntos)
		self.assertEqual(tabla[(puntos[0], puntos[1])], 30)
		with self.assertRaises(ValueError):
			rutas.leer_tabla_osrm({"code": "InvalidQuery"}, puntos)


class TestOptimizacion(unittest.TestCase):
	def _factible(self, resultado, jobs, crews):
		por_crew = {c.crew: c for c in crews}
		por_job = {j.order: j for j in jobs}
		vistos = set()
		for a in resultado.asignaciones:
			self.assertNotIn(a.order, vistos)
			vistos.add(a.order)
			j, c = por_job[a.order], por_crew[a.crew]
			self.assertTrue(elegible(j, c))
			self.assertLessEqual(a.estimated_arrival, j.window_end)
			self.assertGreaterEqual(a.estimated_arrival, j.window_start)
			self.assertLessEqual(a.estimated_finish, c.shift_end)
		cargas = {}
		for a in resultado.asignaciones:
			cargas[a.crew] = cargas.get(a.crew, 0) + 1
		for crew, n in cargas.items():
			self.assertLessEqual(n + por_crew[crew].preassigned, por_crew[crew].max_orders)
		self.assertEqual(vistos | {u.order for u in resultado.no_asignadas}, set(por_job))

	def test_nunca_peor_que_el_motor_por_reglas(self):
		mejor_en_km = 0
		for seed in range(12):
			jobs, crews = instancia(seed)
			r = optimizar(jobs, crews, Settings(), opciones=Opciones(tiempo_max_s=2))
			self._factible(r, jobs, crews)
			self.assertGreaterEqual(r.metricas.asignadas, r.referencia.asignadas)
			self.assertLessEqual(r.metricas.costo, r.referencia.costo + 1e-6)
			if r.metricas.asignadas == r.referencia.asignadas and r.metricas.km < r.referencia.km:
				mejor_en_km += 1
		# En la mayoría de los días con las mismas órdenes asignadas, maneja menos
		self.assertGreater(mejor_en_km, 0)

	def test_determinista(self):
		jobs, crews = instancia(7)
		a = optimizar(jobs, crews, opciones=Opciones(tiempo_max_s=2))
		jobs, crews = instancia(7)
		b = optimizar(jobs, crews, opciones=Opciones(tiempo_max_s=2))
		self.assertEqual(
			[(x.order, x.crew, x.sequence) for x in a.asignaciones],
			[(x.order, x.crew, x.sequence) for x in b.asignaciones],
		)

	def test_ordena_la_ruta_para_no_cruzar(self):
		# Una cuadrilla en San Juan con tres órdenes en línea hacia el este: el orden lógico es SJ → Carolina → Río Grande
		jobs = [
			trabajo("RG", "Río Grande", ws=8, we=17, dur=30),
			trabajo("SJ", "San Juan", ws=8, we=17, dur=30),
			trabajo("CA", "Carolina", ws=8, we=17, dur=30),
		]
		r = optimizar(jobs, [cuadrilla("C1", "San Juan")])
		self.assertEqual(
			[a.order for a in sorted(r.asignaciones, key=lambda a: a.sequence)], ["SJ", "CA", "RG"]
		)

	def test_islas_solo_con_cuadrilla_habilitada(self):
		jobs = [trabajo("VQ", "Vieques", ws=8, we=17)]
		r = optimizar(jobs, [cuadrilla("C1", "Ceiba")])
		self.assertEqual(r.no_asignadas[0].reason, REASON_ISLA)
		r = optimizar(jobs, [cuadrilla("C1", "Ceiba", opera_islas=True)])
		self.assertEqual(r.asignaciones[0].crew, "C1")

	def test_zona_con_incidencia_y_sin_habilidad(self):
		jobs = [
			trabajo("A", "Caguas", bloqueo="Apagón LUMA"),
			trabajo("B", "Caguas", skills=("HFC-EMP",)),
		]
		r = optimizar(jobs, [cuadrilla("C1", "Caguas")])
		motivos = {u.order: u.reason for u in r.no_asignadas}
		self.assertIn("Apagón LUMA", motivos["A"])
		self.assertEqual(motivos["B"], REASON_NO_SKILL)

	def test_cordillera_hace_inviable_una_ruta_optimista(self):
		# Con velocidad plana la cuadrilla «llegaría»; con el terreno real de Utuado no llega a tiempo
		job = trabajo("UT", "Jayuya", ws=7, we=8, dur=60)
		crew = cuadrilla("C1", "Arecibo")
		r = optimizar([job], [crew], modelo=rutas.ModeloViaje(factor_montana=0.3))
		self.assertEqual(r.asignaciones, [])
		r = optimizar([job], [crew], modelo=rutas.ModeloViaje(factor_montana=1.0, velocidad_kmh=60))
		self.assertEqual(len(r.asignaciones), 1)


class TestTracking(unittest.TestCase):
	def _pings(self, puntos, inicio=None, cada=5, crew="C1", zona="Metro"):
		inicio = inicio or DAY.replace(hour=8)
		return [
			tracking.Ping(crew, inicio + timedelta(minutes=i * cada), lat, lng, zona=zona)
			for i, (lat, lng) in enumerate(puntos)
		]

	def test_limpia_saltos_e_imprecisos(self):
		p = self._pings([(18.40, -66.10), (18.41, -66.10), (17.0, -64.0), (18.42, -66.10)])
		p.append(tracking.Ping("C1", DAY.replace(hour=9), 18.43, -66.10, precision_m=900))
		self.assertEqual(len(tracking.limpiar(p)), 3)

	def test_recorrido_paradas_y_velocidad(self):
		movimiento = [(18.40 + i * 0.01, -66.10) for i in range(12)]
		quieto = [(18.51, -66.10)] * 6
		r = tracking.recorrido(self._pings(movimiento + quieto))
		self.assertGreater(r["km"], 10)
		self.assertEqual(len(r["paradas"]), 1)
		v = tracking.velocidad_por_zona(self._pings(movimiento), min_tramos=5)
		self.assertTrue(10 < v["Metro"] < 20)

	def test_alertas(self):
		ahora = DAY.replace(hour=11)
		visitas = [
			tracking.Visita("O1", 18.45, -66.05, "Programada", ventana_fin=DAY.replace(hour=11, minute=10)),
		]
		# Detenida lejos 40 min, sin señal 30 min, y llegará tarde a O1
		pings = self._pings([(18.20, -66.60)] * 9, inicio=DAY.replace(hour=9, minute=50))
		e = tracking.estado("C1", pings, visitas, ahora)
		tipos = {a.tipo for a in e.alertas}
		self.assertIn(tracking.SIN_SENAL, tipos)
		self.assertIn(tracking.DETENIDA, tipos)
		self.assertIn(tracking.TARDE, tipos)
		# En la dirección de la orden sin marcar llegada
		pings = self._pings([(18.45, -66.05)] * 4, inicio=ahora - timedelta(minutes=15))
		e = tracking.estado("C1", pings, visitas, ahora)
		self.assertIn(tracking.EN_SITIO_SIN_MARCAR, {a.tipo for a in e.alertas})

	def test_traccar_en_hora_local(self):
		pos = [
			{"deviceId": 7, "fixTime": "2026-11-06T14:00:00.000+00:00", "latitude": 18.4, "longitude": -66.1}
		]
		p = tracking.desde_traccar(pos, {7: "C1"})
		self.assertEqual(p[0].momento, datetime(2026, 11, 6, 10, 0))


class TestZonas(unittest.TestCase):
	def _historial(self):
		h = []
		for i in range(30):
			h.append(
				zonas.OrdenHistorica(
					f"M{i}",
					"Metro",
					"C1",
					"Completada",
					date(2026, 10, 1 + i % 5),
					sla="Cumplido",
					minutos_estimados=60,
					minutos_servicio=60,
				)
			)
		for i in range(20):
			estado = "No completada" if i % 4 == 0 else "Completada"
			h.append(
				zonas.OrdenHistorica(
					f"E{i}",
					"Este",
					"C2",
					estado,
					date(2026, 10, 1 + i % 5),
					es_retrabajo=i % 5 == 1,
					sla="Incumplido" if i % 3 == 0 else "Cumplido",
					causa_cierre="Cliente" if estado != "Completada" else None,
					minutos_estimados=60,
					minutos_servicio=90,
				)
			)
		return h

	def test_metricas_y_observaciones(self):
		m = zonas.metricas_zona(self._historial())
		self.assertEqual(next(iter(m)), "Metro")
		self.assertGreater(m["Metro"]["puntaje"], m["Este"]["puntaje"])
		texto = " ".join(m["Este"]["observaciones"])
		self.assertIn("cliente", texto)
		self.assertIn("tarda", texto)

	def test_afinidad_suavizada(self):
		af = zonas.afinidad([*self._historial(), zonas.OrdenHistorica("X", "Sur", "C3", "Completada")])
		self.assertGreater(af["C1"]["Metro"], af["C2"]["Este"])
		self.assertLess(af["C3"]["Sur"], af["C1"]["Metro"])

	def test_mueve_cuadrillas_de_zona_holgada_vecina(self):
		r = zonas.demanda_capacidad(
			{"Metro": 1500, "Este": 200, "Oeste": 100},
			{"Metro": 1000, "Este": 1500, "Oeste": 1500},
			{"Este": [("C-E1", 500), ("C-E2", 500), ("C-E3", 500)], "Oeste": [("C-O1", 500)]},
		)
		self.assertEqual(r["movimientos"][0]["de"], "Este")
		self.assertEqual(r["zonas"]["Metro"]["estado"], "Déficit")
		self.assertNotEqual(r["zonas"]["Metro"]["estado_con_movimientos"], "Déficit")

	def test_mejor_cuadrilla_por_ubicacion_actual(self):
		job = trabajo("AV", "Carolina", ws=9, we=17, dur=60, priority="Alta")
		cerca = zonas.CuadrillaEnCampo(cuadrilla("C1", "San Juan"), 18.38, -65.96, DAY.replace(hour=10))
		lejos = zonas.CuadrillaEnCampo(cuadrilla("C2", "San Juan"), 18.01, -66.61, DAY.replace(hour=10))
		llena = zonas.CuadrillaEnCampo(
			cuadrilla("C3", "Carolina", max_orders=2), 18.38, -65.95, DAY.replace(hour=10), ordenes_hoy=2
		)
		sin_habilidad = zonas.CuadrillaEnCampo(
			cuadrilla("C4", "Carolina", skills=("HFC-RES",)), 18.38, -65.95, DAY.replace(hour=10)
		)
		r = zonas.mejor_cuadrilla(job, [lejos, llena, cerca, sin_habilidad], DAY.replace(hour=10))
		self.assertEqual([o["cuadrilla"] for o in r], ["C1", "C2"])
		self.assertIn("min de viaje", r[0]["razones"][0])


class TestMateriales(unittest.TestCase):
	def test_recoge_neto_y_devuelve_sobrantes(self):
		nec = materiales.necesidades(
			[("C1", "FTTH-INST-RES"), ("C1", "FTTH-INST-RES")],
			{"FTTH-INST-RES": [("DROP-50M", 1), ("ONT", 1), ("CONECTOR-SC", 2)]},
		)
		plan = materiales.plan_bodega(
			nec,
			{"C1": {"DROP-50M": 1, "ONT": 6, "CONECTOR-SC": 20}},
			stock_central={"DROP-50M": 0},
			serializados={"ONT"},
		)["C1"]
		self.assertEqual(plan["recoger"], {"DROP-50M": 2})
		self.assertEqual(plan["devolver"], {"ONT": 3, "CONECTOR-SC": 15})
		self.assertEqual(plan["faltante_central"], {"DROP-50M": 2})
		self.assertFalse(plan["lista"])

	def test_conciliacion_y_estancados(self):
		h = materiales.conciliar(
			{"DROP-50M": 1, "ONT": 1}, [("DROP-50M", 4, None), ("ONT", 1, None)], {"ONT"}
		)
		self.assertEqual({x["tipo"] for x in h}, {"Equipo sin serial", "Consumo mayor al kit"})
		self.assertEqual(materiales.conciliar({"ONT": 1}, [])[0]["tipo"], "Consumo sin registrar")
		c = materiales.consumo_por_cuadrilla([("C1", "DROP-50M", 1, 2)] * 6)
		self.assertEqual(c[0]["veces_el_kit"], 2.0)
		e = materiales.equipos_estancados([("SN1", "ONT", "C1", date(2026, 10, 20))], date(2026, 11, 6))
		self.assertEqual(e[0]["dias"], 17)


class TestPendientes(unittest.TestCase):
	def test_evidencia_y_trabadas(self):
		o = pendientes.OrdenAbierta(
			"O1",
			"En sitio",
			categoria="Instalación",
			segmento="Empresarial",
			llego=DAY.replace(hour=9),
			duracion_min=60,
			tiene_kit=True,
			checklist=[
				pendientes.FilaChecklist("Foto ONT", "Foto", True),
				pendientes.FilaChecklist("Potencia ONT", "Medición", True, valor="-30"),
				pendientes.FilaChecklist("Foto opcional", "Foto", False),
			],
		)
		codigos = {p["codigo"] for p in pendientes.pendientes(o, DAY.replace(hour=11))}
		self.assertEqual(
			codigos, {"EVIDENCIA", "MEDICION_FUERA", "MATERIALES", "SERIAL", "FIRMA", "EN_SITIO_LARGO"}
		)

	def test_despues_del_cierre_y_ventana(self):
		ahora = DAY.replace(hour=15)
		casos = {
			"VENTANA_PERDIDA": pendientes.OrdenAbierta("A", "Programada", fin_ventana=DAY.replace(hour=12)),
			"SIN_REPROGRAMAR": pendientes.OrdenAbierta(
				"B", "No completada", requiere_reprogramar=True, termino=ahora - timedelta(days=2)
			),
			"SALIDA_INVENTARIO": pendientes.OrdenAbierta(
				"C", "Completada", tiene_kit=True, almacen_cuadrilla=True, termino=ahora, firma=True
			),
			"MATERIALES_SIN_RECOGER": pendientes.OrdenAbierta(
				"D", "En ruta", solicitud_materiales="MR-1", solicitud_entregada=False
			),
		}
		for codigo, orden in casos.items():
			self.assertIn(codigo, {p["codigo"] for p in pendientes.pendientes(orden, ahora)}, codigo)
		r = pendientes.resumen(pendientes.pendientes(casos["VENTANA_PERDIDA"], ahora))
		self.assertEqual(r["por_severidad"]["Alta"], 1)


class TestClima(unittest.TestCase):
	# Misma forma que https://api.weather.gov/alerts/active?area=PR
	ALERTAS: ClassVar[dict] = {
		"features": [
			{
				"properties": {
					"id": "a1",
					"event": "Flash Flood Warning",
					"status": "Actual",
					"messageType": "Alert",
					"areaDesc": "Caguas, PR; Cayey, PR; Cidra, PR",
					"expires": "2026-11-06T18:00:00-04:00",
				}
			},
			{
				"properties": {
					"id": "a2",
					"event": "Wind Advisory",
					"status": "Actual",
					"messageType": "Alert",
					"areaDesc": "Northeast; San Juan and Vicinity",
				}
			},
			{
				"properties": {
					"id": "a3",
					"event": "Special Weather Statement",
					"status": "Actual",
					"areaDesc": "Ponce",
				}
			},
			{"properties": {"id": "a4", "event": "Flood Advisory", "status": "Test", "areaDesc": "Ponce"}},
		]
	}

	def test_alertas_a_zonas(self):
		inc = {i["id"]: i for i in clima.incidencias_desde_nws(self.ALERTAS, {"Caguas": "Este"})}
		self.assertEqual(set(inc), {"a1", "a2"})
		self.assertEqual(inc["a1"]["impacto"], clima.SUSPENDER)
		self.assertEqual(inc["a1"]["zonas"], ["Centro", "Este"])
		self.assertEqual(inc["a2"]["impacto"], clima.SIN_ALTURA)
		self.assertEqual(inc["a2"]["zonas"], ["Este", "Metro"])
		self.assertIsNotNone(inc["a1"]["hasta"])


CATALOGO = solicitudes.Catalogo(
	tipos=[
		solicitudes.TipoTrabajo(
			"FTTH-INST-RES", "Instalación FTTH residencial", "FTTH", "Residencial", "Instalación"
		),
		solicitudes.TipoTrabajo(
			"FTTH-REP-EMP", "Reparación FTTH empresarial", "FTTH", "Empresarial", "Reparación"
		),
		solicitudes.TipoTrabajo(
			"HFC-RECON", "Reconectorización HFC", "HFC", "Residencial", "Reconectorización"
		),
		solicitudes.TipoTrabajo(
			"HFC-INST-RES", "Instalación HFC residencial", "HFC", "Residencial", "Instalación"
		),
	],
	municipio_a_zona={"Caguas": "Este"},
)
HOY = date(2026, 11, 5)  # jueves

TEXTO_EMPRESA = """Ticket #LIB-2026-88123
Cliente: Farmacia El Pueblo
Dirección: Calle Muñoz Rivera 45, Caguas
Tel. (787) 555-0142  cuenta 123456789
El negocio está sin servicio de fibra desde anoche. Visita mañana de 8 a 12."""


class TestSolicitudes(unittest.TestCase):
	def test_reparacion_empresarial(self):
		d = solicitudes.extraer(TEXTO_EMPRESA, CATALOGO, HOY)
		self.assertEqual(d["work_type"], "FTTH-REP-EMP")
		self.assertEqual(d["priority"], "Alta")
		self.assertEqual((d["municipality"], d["zone"]), ("Caguas", "Este"))
		self.assertEqual(d["phone"], "787-555-0142")
		self.assertEqual(d["account_number"], "123456789")
		self.assertEqual(d["external_order_id"], "LIB-2026-88123")
		self.assertEqual(d["subscriber_name"], "Farmacia El Pueblo")
		self.assertEqual(d["appointment_date"], "2026-11-06")
		self.assertEqual((d["window_start"], d["window_end"]), ("08:00:00", "12:00:00"))
		self.assertEqual(d["faltantes"], [])

	def test_frases_de_fecha_y_horario(self):
		n = territorio.normalizar
		self.assertEqual(solicitudes.fecha(n("mañana en la mañana"), HOY), date(2026, 11, 6))
		self.assertIsNone(solicitudes.fecha(n("en la mañana"), HOY))
		self.assertEqual(solicitudes.fecha(n("el lunes"), HOY), date(2026, 11, 9))
		self.assertEqual(solicitudes.ventana(n("de 1 a 5")), ("13:00:00", "17:00:00"))
		self.assertIsNone(solicitudes.ventana(n("fecha 2026-11-06 tel 787-555-1234")))
		self.assertEqual(solicitudes.ventana(n("por la tarde")), ("12:00:00", "17:00:00"))

	def test_reconexion_hfc_y_vieques(self):
		d = solicitudes.extraer("Cambio de conector F en el tap, casa en Vieques, urgente", CATALOGO, HOY)
		self.assertEqual(d["work_type"], "HFC-RECON")
		self.assertEqual(d["priority"], "Alta")
		self.assertIn("ferry", d["nota_isla"])
		n = territorio.normalizar
		self.assertEqual(
			solicitudes.prioridad(n("Hospital sin internet"), "Empresarial", "Reparación"), "Crítica"
		)
		self.assertEqual(solicitudes.prioridad(n("no urgente, cuando puedan"), "Residencial", None), "Baja")
		d = solicitudes.extraer("Instalación de internet por cable para casa en Humacao", CATALOGO, HOY)
		self.assertEqual(d["work_type"], "HFC-INST-RES")

	def test_etiquetas_en_una_sola_linea(self):
		texto = (
			"Ticket 55120. Cliente: Ferretería Boricua. Dirección: Carr. 2 km 5, Mayagüez. "
			"Tel 787-555-2211. Negocio sin servicio de fibra, mañana de 8 a 12"
		)
		d = solicitudes.extraer(texto, CATALOGO, HOY)
		self.assertEqual(d["subscriber_name"], "Ferretería Boricua")
		self.assertEqual(d["address"], "Carr. 2 km 5, Mayagüez")
		self.assertEqual(d["external_order_id"], "55120")
		self.assertEqual(d["municipality"], "Mayagüez")

	def test_anonimizar(self):
		t = solicitudes.anonimizar(TEXTO_EMPRESA)
		for dato in ("555-0142", "123456789", "Farmacia El Pueblo", "Muñoz Rivera"):
			self.assertNotIn(dato, t)
		self.assertIn("(Caguas)", t)


class ClienteFalso:
	"""Imita ``anthropic.Anthropic().beta.messages.create`` y guarda las llamadas."""

	def __init__(self, respuestas):
		self.respuestas = list(respuestas)
		self.llamadas = []
		self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

	def _create(self, **params):
		self.llamadas.append(json.loads(json.dumps(params, default=str)))
		return self.respuestas.pop(0)


def texto(t, stop="end_turn"):
	return SimpleNamespace(stop_reason=stop, content=[SimpleNamespace(type="text", text=t)])


class TestIA(unittest.TestCase):
	def test_sin_modelo_usa_reglas_y_plantillas(self):
		p = ia.proveedor(ia.ConfigIA())
		d = ia.interpretar_solicitud(TEXTO_EMPRESA, CATALOGO, p, HOY)
		self.assertEqual((d["work_type"], d["fuente"]), ("FTTH-REP-EMP", "Reglas"))
		b = ia.briefing({"kpis": {"sla_vencido": 2, "abiertas": 10}, "alertas": ["C1 sin señal"]}, p)
		self.assertIn("SLA vencido", b)
		self.assertIn("C1 sin señal", b)
		self.assertIn("necesita un modelo", ia.asistente("¿Cómo vamos?", [], p))

	def test_claude_parametros_validacion_y_privacidad(self):
		respuesta = json.dumps(
			{
				"work_type": "HFC-INST-RES",
				"priority": "Normal",
				"municipality": "caguas",
				"appointment_date": None,
				"window": None,
				"external_order_id": None,
				"resumen": "Instalación de internet",
			}
		)
		cliente = ClienteFalso([texto(respuesta)])
		p = ia.ProveedorClaude(ia.ConfigIA(proveedor=ia.CLAUDE, api_key="x"), cliente=cliente)
		d = ia.interpretar_solicitud(
			"Instalar internet en casa en el pueblo; tel 787-555-9999", CATALOGO, p, HOY
		)
		self.assertEqual(d["work_type"], "HFC-INST-RES")
		self.assertEqual(d["municipality"], "Caguas")
		self.assertEqual(d["phone"], "787-555-9999")
		self.assertEqual(d["fuente"], "Reglas + IA")
		llamada = cliente.llamadas[0]
		self.assertEqual(llamada["model"], "claude-opus-5-5")
		self.assertEqual(llamada["fallbacks"], "default")
		self.assertEqual(llamada["betas"], ["server-side-fallback-2026-07-01"])
		self.assertEqual(llamada["output_config"]["effort"], "low")
		self.assertEqual(llamada["output_config"]["format"]["type"], "json_schema")
		self.assertNotIn("temperature", llamada)
		self.assertNotIn("787-555-9999", json.dumps(llamada["messages"]))

	def test_claude_respuesta_invalida_vuelve_a_reglas(self):
		p = ia.ProveedorClaude(
			ia.ConfigIA(api_key="x"), cliente=ClienteFalso([texto('{"work_type": "INVENTADO"}')])
		)
		d = ia.interpretar_solicitud(TEXTO_EMPRESA, CATALOGO, p, HOY)
		self.assertEqual(d["work_type"], "FTTH-REP-EMP")
		p = ia.ProveedorClaude(ia.ConfigIA(api_key="x"), cliente=ClienteFalso([texto("", stop="refusal")]))
		self.assertIn("aviso_ia", ia.interpretar_solicitud(TEXTO_EMPRESA, CATALOGO, p, HOY))

	def test_claude_con_herramientas(self):
		uso = SimpleNamespace(type="tool_use", id="t1", name="resumen", input={})
		cliente = ClienteFalso(
			[SimpleNamespace(stop_reason="tool_use", content=[uso]), texto("Hay 3 órdenes abiertas.")]
		)
		p = ia.ProveedorClaude(ia.ConfigIA(api_key="x"), cliente=cliente)
		h = ia.Herramienta("resumen", "Contadores del día", lambda _: {"abiertas": 3})
		self.assertEqual(ia.asistente("¿Cuántas abiertas?", [h], p), "Hay 3 órdenes abiertas.")
		segunda = cliente.llamadas[1]["messages"]
		self.assertEqual(segunda[-1]["content"][0]["type"], "tool_result")
		self.assertIn('"abiertas": 3', segunda[-1]["content"][0]["content"])
		self.assertTrue(cliente.llamadas[0]["tools"][0]["strict"])

	def test_ollama_local_con_herramientas(self):
		respuestas = [
			{
				"message": {
					"role": "assistant",
					"content": "",
					"tool_calls": [{"function": {"name": "resumen", "arguments": {}}}],
				}
			},
			{"message": {"role": "assistant", "content": "Todo en orden."}},
		]
		enviados = []

		def transporte(url, cuerpo, timeout):
			enviados.append((url, cuerpo))
			return respuestas.pop(0)

		p = ia.ProveedorOllama(
			ia.ConfigIA(proveedor=ia.OLLAMA, base_url="http://ollama:11434"), transporte=transporte
		)
		h = ia.Herramienta("resumen", "Contadores", lambda _: {"abiertas": 0})
		self.assertEqual(ia.asistente("¿Cómo vamos?", [h], p), "Todo en orden.")
		self.assertEqual(enviados[0][0], "http://ollama:11434/api/chat")
		self.assertEqual(enviados[1][1]["messages"][-1]["role"], "tool")
		# Local: el texto se envía completo (no sale del servidor)
		self.assertFalse(p.externo)


if __name__ == "__main__":
	unittest.main()
