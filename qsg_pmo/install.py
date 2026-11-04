"""Datos semilla de QSG PMO.

Los rangos de medición son valores típicos de la industria y deben
validarse contra el manual de instalación de Liberty antes de producción.
"""

import frappe

SKILLS = {
	"FTTH-RES": "Instalación y reparación FTTH residencial",
	"FTTH-EMP": "Instalación y reparación FTTH empresarial",
	"HFC-RES": "Instalación y reparación HFC/DOCSIS residencial",
	"HFC-EMP": "Instalación y reparación HFC/DOCSIS empresarial",
	"FUSION": "Empalme por fusión",
	"OTDR": "Pruebas con OTDR",
	"ALTURA": "Trabajo en altura (poste / escalera)",
	"RECONECT": "Reconectorización de drop y acometida",
}

# Zonas operativas de Puerto Rico (agrupación inicial, ajustable)
ZONES = {
	"Metro": (18.4271, -66.0634, ["San Juan", "Bayamón", "Guaynabo", "Carolina", "Cataño", "Trujillo Alto"]),
	"Este": (
		18.2208,
		-65.8000,
		[
			"Caguas",
			"Humacao",
			"Fajardo",
			"Gurabo",
			"Juncos",
			"Las Piedras",
			"Río Grande",
			"Canóvanas",
			"Loíza",
		],
	),
	"Norte": (
		18.4545,
		-66.4000,
		[
			"Arecibo",
			"Manatí",
			"Vega Baja",
			"Vega Alta",
			"Dorado",
			"Toa Baja",
			"Toa Alta",
			"Barceloneta",
			"Hatillo",
		],
	),
	"Oeste": (
		18.2013,
		-67.1397,
		["Mayagüez", "Aguadilla", "Isabela", "Cabo Rojo", "San Germán", "Moca", "Añasco", "Rincón", "Aguada"],
	),
	"Sur": (
		18.0111,
		-66.6141,
		["Ponce", "Guayama", "Juana Díaz", "Santa Isabel", "Salinas", "Coamo", "Yauco", "Peñuelas"],
	),
	"Centro": (
		18.2208,
		-66.4000,
		["Cayey", "Cidra", "Aibonito", "Barranquitas", "Comerío", "Orocovis", "Utuado", "Jayuya", "Ciales"],
	),
}

CLOSURE_CODES = [
	# code, description, result, cause, stops_sla, billable, requires_reschedule
	("COMP-OK", "Trabajo completado", "Completada", "", 0, 1, 0),
	("COMP-PARCIAL", "Completado parcial, pendiente segundo equipo", "Completada", "", 0, 1, 0),
	("CLI-AUS", "Cliente ausente", "No completada", "Cliente", 1, 1, 1),
	("CLI-RECH", "Cliente rechaza el servicio", "No completada", "Cliente", 1, 1, 0),
	("CLI-REPROG", "Cliente solicita otra fecha", "No completada", "Cliente", 1, 0, 1),
	("CLI-DIR", "Dirección incorrecta o no localizada", "No completada", "Cliente", 1, 0, 1),
	("RED-SINPUERTO", "CTO / tap sin capacidad", "No completada", "Red", 0, 0, 1),
	("RED-SINSENAL", "Sin señal en el punto de acceso", "No completada", "Red", 0, 0, 1),
	("RED-AVERIA", "Avería de planta, escalada", "No completada", "Red", 0, 0, 1),
	("RED-CONSTR", "Requiere construcción u obra", "No completada", "Red", 0, 0, 1),
	("PERM", "Falta permiso o servidumbre", "No completada", "Otro", 1, 0, 1),
	("CLIMA", "Condiciones climáticas", "No completada", "Otro", 1, 0, 1),
	("SEG", "Riesgo de seguridad", "No completada", "Otro", 1, 0, 1),
	("MAT", "Falta material o equipo", "No completada", "Otro", 0, 0, 1),
]

# item: (description, type, mandatory, unit, min, max)
COMMON_PHOTOS = [
	("Foto de fachada / número de la dirección", "Foto", 1, None, None, None),
	("Foto del área de trabajo limpia al terminar", "Foto", 1, None, None, None),
]
CHECKLISTS = {
	"Instalación FTTH": [
		("Inspección y limpieza de conectores realizada", "Sí/No", 1, None, None, None),
		("Foto de CTO / splitter antes", "Foto", 1, None, None, None),
		("Foto de CTO / splitter después", "Foto", 1, None, None, None),
		("Foto del recorrido del drop", "Foto", 1, None, None, None),
		("Foto de roseta / punto de terminación óptica", "Foto", 1, None, None, None),
		("Potencia recibida en ONT a 1490 nm", "Medición", 1, "dBm", -25, -8),
		("Foto de la ONT con serial visible", "Foto", 1, None, None, None),
		("Prueba de velocidad (Mbps de bajada)", "Medición", 1, "Mbps", None, None),
		("Foto de la prueba de velocidad", "Foto", 0, None, None, None),
		*COMMON_PHOTOS,
	],
	"Instalación HFC": [
		("Foto del tap antes", "Foto", 1, None, None, None),
		("Foto del tap después", "Foto", 1, None, None, None),
		("Tierra del drop instalada", "Sí/No", 1, None, None, None),
		("Conectores F comprimidos y ajustados", "Sí/No", 1, None, None, None),
		("Nivel downstream en el módem", "Medición", 1, "dBmV", -7, 7),
		("MER / SNR downstream", "Medición", 1, "dB", 35, None),
		("Nivel de transmisión upstream", "Medición", 1, "dBmV", 35, 51),
		("Foto del módem con MAC / serial visible", "Foto", 1, None, None, None),
		("Prueba de velocidad (Mbps de bajada)", "Medición", 1, "Mbps", None, None),
		*COMMON_PHOTOS,
	],
	"Reconectorización": [
		("Foto del conector dañado antes", "Foto", 1, None, None, None),
		("Foto del conector nuevo instalado", "Foto", 1, None, None, None),
		("Medición después del cambio (dBm o dBmV)", "Medición", 1, "", None, None),
		("Servicio verificado con el cliente", "Sí/No", 1, None, None, None),
		*COMMON_PHOTOS,
	],
	"Reparación": [
		("Descripción de la falla encontrada", "Texto", 1, None, None, None),
		("Foto de la falla", "Foto", 1, None, None, None),
		("Foto de la corrección", "Foto", 1, None, None, None),
		("Medición final (dBm o dBmV)", "Medición", 1, "", None, None),
		("Servicio verificado con el cliente", "Sí/No", 1, None, None, None),
		*COMMON_PHOTOS,
	],
}

# code, name, technology, segment, category, minutes, sla_hours, skills, checklist
WORK_TYPES = [
	(
		"FTTH-INST-RES",
		"Instalación FTTH residencial",
		"FTTH",
		"Residencial",
		"Instalación",
		120,
		72,
		["FTTH-RES"],
		"Instalación FTTH",
	),
	(
		"FTTH-INST-EMP",
		"Instalación FTTH empresarial",
		"FTTH",
		"Empresarial",
		"Instalación",
		180,
		48,
		["FTTH-EMP"],
		"Instalación FTTH",
	),
	(
		"FTTH-REP-RES",
		"Reparación FTTH residencial",
		"FTTH",
		"Residencial",
		"Reparación",
		90,
		24,
		["FTTH-RES"],
		"Reparación",
	),
	(
		"FTTH-REP-EMP",
		"Reparación FTTH empresarial",
		"FTTH",
		"Empresarial",
		"Reparación",
		120,
		8,
		["FTTH-EMP"],
		"Reparación",
	),
	(
		"FTTH-RECON",
		"Reconectorización FTTH",
		"FTTH",
		"Residencial",
		"Reconectorización",
		60,
		24,
		["FTTH-RES", "RECONECT"],
		"Reconectorización",
	),
	(
		"HFC-INST-RES",
		"Instalación HFC residencial",
		"HFC",
		"Residencial",
		"Instalación",
		90,
		72,
		["HFC-RES"],
		"Instalación HFC",
	),
	(
		"HFC-INST-EMP",
		"Instalación HFC empresarial",
		"HFC",
		"Empresarial",
		"Instalación",
		150,
		48,
		["HFC-EMP"],
		"Instalación HFC",
	),
	(
		"HFC-REP-RES",
		"Reparación HFC residencial",
		"HFC",
		"Residencial",
		"Reparación",
		75,
		24,
		["HFC-RES"],
		"Reparación",
	),
	(
		"HFC-RECON",
		"Reconectorización HFC",
		"HFC",
		"Residencial",
		"Reconectorización",
		45,
		24,
		["HFC-RES", "RECONECT"],
		"Reconectorización",
	),
]


ROLES = ["QSG Gerente", "QSG Despachador", "QSG Supervisor Contratista", "QSG Tecnico", "QSG Bodega"]


def before_install():
	create_roles()


def after_install():
	create_roles()
	seed()


def create_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(
				ignore_permissions=True
			)


def seed():
	for code, desc in SKILLS.items():
		if not frappe.db.exists("QSG Habilidad", code):
			frappe.get_doc({"doctype": "QSG Habilidad", "skill_name": code, "description": desc}).insert()

	for zone, (lat, lng, municipalities) in ZONES.items():
		if not frappe.db.exists("QSG Zona", zone):
			frappe.get_doc(
				{
					"doctype": "QSG Zona",
					"zone_name": zone,
					"latitude": lat,
					"longitude": lng,
					"municipalities": [{"municipality": m} for m in municipalities],
				}
			).insert()

	for code, desc, result, cause, stops, billable, resched in CLOSURE_CODES:
		if not frappe.db.exists("QSG Codigo de Cierre", code):
			frappe.get_doc(
				{
					"doctype": "QSG Codigo de Cierre",
					"code": code,
					"description": desc,
					"result": result,
					"cause": cause,
					"stops_sla": stops,
					"billable": billable,
					"requires_reschedule": resched,
				}
			).insert()

	for name, items in CHECKLISTS.items():
		if not frappe.db.exists("QSG Plantilla Checklist", name):
			frappe.get_doc(
				{
					"doctype": "QSG Plantilla Checklist",
					"template_name": name,
					"items": [
						{
							"description": d,
							"item_type": t,
							"mandatory": m,
							"unit": u,
							"min_value": lo,
							"max_value": hi,
						}
						for d, t, m, u, lo, hi in items
					],
				}
			).insert()

	for code, name, tech, seg, cat, minutes, sla, skills, checklist in WORK_TYPES:
		if not frappe.db.exists("QSG Tipo de Trabajo", code):
			frappe.get_doc(
				{
					"doctype": "QSG Tipo de Trabajo",
					"work_type_code": code,
					"work_type_name": name,
					"technology": tech,
					"segment": seg,
					"category": cat,
					"duration_minutes": minutes,
					"sla_hours": sla,
					"checklist_template": checklist,
					"required_skills": [{"skill": s} for s in skills],
				}
			).insert()
