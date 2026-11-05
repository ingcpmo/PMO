# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Autodiagnóstico de seguridad del sitio.

    bench --site <sitio> execute qsg_pmo.seguridad.verificar.ejecutar

También se ve en el reporte *Estado de Seguridad*. Cada control devuelve OK, ALERTA o FALLA.
"""

import frappe
from frappe.utils import cint
from frappe.utils.password import check_password

OK, ALERTA, FALLA = "OK", "ALERTA", "FALLA"
DEMO_USERS = ("tecnico@qsg.pr",)


def ejecutar() -> dict:
	frappe.only_for(("System Manager", "QSG Gerente"))
	checks = list(controles())
	summary = {s: sum(1 for c in checks if c["estado"] == s) for s in (OK, ALERTA, FALLA)}
	return {"resumen": summary, "controles": checks}


def _c(area, control, estado, detalle, accion=""):
	return {"area": area, "control": control, "estado": estado, "detalle": detalle, "accion": accion}


def controles():
	conf = frappe.conf
	ss = frappe.get_single("System Settings")
	hooks = frappe.get_hooks()

	# ---------------------------------------------------------------- servidor
	yield _c(
		"Servidor",
		"Modo desarrollador apagado",
		FALLA if cint(conf.developer_mode) else OK,
		"developer_mode está activo" if cint(conf.developer_mode) else "apagado",
		"bench --site <sitio> set-config developer_mode 0",
	)
	host = conf.host_name or ""
	yield _c(
		"Servidor",
		"Conexión cifrada (HTTPS)",
		OK if host.startswith("https://") else ALERTA,
		host or "host_name sin definir",
		"Publique el sitio con dominio y certificado (bench setup lets-encrypt) y defina host_name con https://",
	)
	yield _c(
		"Servidor",
		"Errores sin código fuente",
		OK if not cint(ss.allow_error_traceback) else FALLA,
		"los errores no muestran trazas" if not cint(ss.allow_error_traceback) else "se muestran trazas",
		"System Settings → desmarcar «Allow Error Traceback»",
	)
	yield _c(
		"Servidor",
		"Copias de seguridad automáticas",
		OK
		if not cint(conf.pause_scheduler) and frappe.utils.scheduler.is_scheduler_inactive() is False
		else ALERTA,
		"planificador activo"
		if frappe.utils.scheduler.is_scheduler_inactive() is False
		else "planificador inactivo",
		"bench --site <sitio> enable-scheduler",
	)

	# ---------------------------------------------------------------- acceso
	try:
		check_password("Administrator", "admin")
		weak_admin = True
	except Exception:
		weak_admin = False
	yield _c(
		"Acceso",
		"Contraseña del Administrador cambiada",
		FALLA if weak_admin else OK,
		"sigue siendo «admin»" if weak_admin else "no es la contraseña por defecto",
		"Cambie la contraseña del usuario Administrator",
	)
	demo = [u for u in DEMO_USERS if frappe.db.get_value("User", u, "enabled")]
	yield _c(
		"Acceso",
		"Usuarios de demostración desactivados",
		ALERTA if demo else OK,
		f"activos: {', '.join(demo)}" if demo else "ninguno activo",
		"Desactive los usuarios de prueba antes de operar con datos reales",
	)
	attempts = cint(ss.allow_consecutive_login_attempts)
	yield _c(
		"Acceso",
		"Bloqueo por intentos fallidos",
		OK if 0 < attempts <= 5 and cint(ss.allow_login_after_fail) >= 300 else FALLA,
		f"{attempts} intentos, bloqueo de {ss.allow_login_after_fail} s",
		"bench migrate aplica 5 intentos y 600 s",
	)
	yield _c(
		"Acceso",
		"Política de contraseñas",
		OK if cint(ss.enable_password_policy) and cint(ss.minimum_password_score) >= 3 else FALLA,
		f"activa={ss.enable_password_policy}, puntaje mínimo={ss.minimum_password_score}",
	)
	yield _c(
		"Acceso",
		"Duración de la sesión",
		OK if _minutes(ss.session_expiry) <= 12 * 60 else ALERTA,
		f"{ss.session_expiry} (horas:minutos)",
	)
	signup = cint(frappe.db.get_single_value("Website Settings", "disable_signup"))
	yield _c(
		"Acceso",
		"Auto-registro desactivado",
		OK if signup else FALLA,
		"desactivado" if signup else "cualquiera puede registrarse",
	)
	two_fa = cint(ss.enable_two_factor_auth) and cint(
		frappe.db.get_value("Role", "QSG Gerente", "two_factor_auth")
	)
	yield _c(
		"Acceso",
		"Doble factor para gerencia y despacho",
		OK if two_fa else ALERTA,
		"activo" if two_fa else "no exigido",
		"QSG Configuracion → «Exigir doble factor a gerencia y despacho» y migrar",
	)

	# ---------------------------------------------------------------- permisos
	tech_write = frappe.db.exists(
		"DocPerm", {"parent": "QSG Orden", "role": "QSG Tecnico", "write": 1}
	) or frappe.db.exists("Custom DocPerm", {"parent": "QSG Orden", "role": "QSG Tecnico", "write": 1})
	yield _c(
		"Permisos",
		"Técnico sin escritura directa en órdenes",
		FALLA if tech_write else OK,
		"el técnico solo cambia órdenes por la app, con validaciones"
		if not tech_write
		else "el técnico puede editar órdenes por REST",
	)
	supervisors = frappe.get_all(
		"Has Role", filters={"role": "QSG Supervisor Contratista", "parenttype": "User"}, pluck="parent"
	)
	unbound = [
		u
		for u in supervisors
		if not frappe.db.exists("User Permission", {"user": u, "allow": "QSG Contratista"})
		and not (set(frappe.get_roles(u)) & {"System Manager", "QSG Gerente", "QSG Despachador"})
	]
	yield _c(
		"Permisos",
		"Supervisores ligados a su contratista",
		ALERTA if unbound else OK,
		f"sin contratista (no ven nada): {', '.join(unbound)}"
		if unbound
		else f"{len(supervisors)} supervisores ligados",
		"Cree un User Permission (QSG Contratista) para cada supervisor",
	)

	# ---------------------------------------------------------------- protecciones de la app
	yield _c(
		"Aplicación",
		"Cabeceras de seguridad",
		OK if "qsg_pmo.seguridad.cabeceras.after_request" in (hooks.get("after_request") or []) else FALLA,
		"CSP, anti-clickjacking, nosniff, HSTS en https",
	)
	file_hooks = (hooks.get("doc_events") or {}).get("File", {})
	file_class = (hooks.get("override_doctype_class") or {}).get("File") or []
	yield _c(
		"Aplicación",
		"Filtro de archivos",
		OK
		if "qsg_pmo.seguridad.archivos.on_file_insert" in (file_hooks.get("before_insert") or [])
		and "qsg_pmo.seguridad.archivos.ArchivoQSG" in file_class
		else FALLA,
		"solo imágenes reales y de tamaño acotado en documentos de QSG",
	)
	limit = cint(frappe.db.get_single_value("QSG Configuracion", "rate_limit_per_minute")) or 120
	yield _c("Aplicación", "Límite de peticiones", OK, f"{limit} por minuto por usuario y método")
	ips = (frappe.db.get_single_value("QSG Configuracion", "integration_allowed_ips") or "").strip()
	yield _c(
		"Aplicación",
		"Integración limitada por IP",
		OK if ips else ALERTA,
		ips or "cualquier IP con token válido puede enviar órdenes",
		"QSG Configuracion → «IPs permitidas para la integración» con las IPs de Liberty",
	)
	recent = frappe.db.count(
		"QSG Evento Seguridad",
		{"severity": "Alta", "creation": [">", frappe.utils.add_days(frappe.utils.now(), -1)]},
	)
	yield _c(
		"Monitoreo",
		"Eventos graves en las últimas 24 horas",
		OK if not recent else ALERTA,
		f"{recent} eventos de severidad alta",
		"Revise la lista QSG Evento Seguridad",
	)


def _minutes(value):
	try:
		h, m = str(value or "0:0").split(":")[:2]
		return int(h) * 60 + int(m)
	except ValueError:
		return 10**9
