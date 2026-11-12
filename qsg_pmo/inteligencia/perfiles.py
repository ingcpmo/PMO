# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Perfiles de la aplicación y alta del equipo desde el tablero.

Una sola app (y un solo APK) sirve a todos: el servidor decide qué ve cada usuario según su perfil.

- **Administrador** (rol QSG Gerente): ve todo, asigna, configura las reglas y el equipo.
- **Despachador** (QSG Despachador): ve todo y asigna; no configura.
- **Supervisor** (QSG Supervisor Contratista): solo las cuadrillas y órdenes de su empresa.
- **Contratista** (QSG Tecnico): solo las órdenes de su cuadrilla; no ve a nadie más.

Solo gerencia puede dar de alta o cambiar usuarios, y nunca a un administrador del sistema.
"""

import json
import re
import secrets

import frappe
from frappe import _
from frappe.sessions import clear_sessions
from frappe.utils import cint, get_datetime, now_datetime, nowdate

from qsg_pmo.inteligencia import territorio

ADMINISTRADOR, DESPACHADOR, SUPERVISOR, CONTRATISTA = (
	"Administrador",
	"Despachador",
	"Supervisor",
	"Contratista",
)
ROL = {
	ADMINISTRADOR: "QSG Gerente",
	DESPACHADOR: "QSG Despachador",
	SUPERVISOR: "QSG Supervisor Contratista",
	CONTRATISTA: "QSG Tecnico",
}
GERENCIA = ("System Manager", "QSG Gerente")
INTOCABLES = ("Administrator", "Guest")


# ---------------------------------------------------------------------- perfil del usuario
def perfil(user: str | None = None) -> str | None:
	roles = set(frappe.get_roles(user or frappe.session.user))
	if roles & set(GERENCIA):
		return ADMINISTRADOR
	for nombre in (DESPACHADOR, SUPERVISOR, CONTRATISTA):
		if ROL[nombre] in roles:
			return nombre
	return None


def mi_perfil() -> dict:
	from qsg_pmo.api import mis_cuadrillas

	user = frappe.session.user
	p = perfil(user)
	return {
		"usuario": user,
		"nombre": frappe.utils.get_fullname(user),
		"perfil": p,
		"inicio": "/campo" if p in (CONTRATISTA, None) else "/despacho",
		"gerencia": p == ADMINISTRADOR,
		"cuadrillas": mis_cuadrillas(user),
	}


# ---------------------------------------------------------------------- equipo
def _exigir_gerencia():
	frappe.only_for(GERENCIA)


def _puede_gestionar(correo: str, cambiar: bool = True):
	"""Gerencia gestiona despachadores, supervisores y contratistas, y los administradores que ella
	misma creó. Nadie gestiona desde aquí a un administrador del sistema ni a sí mismo."""
	if correo in INTOCABLES:
		frappe.throw(_("Ese usuario no se gestiona desde aquí."), frappe.PermissionError)
	roles = set(frappe.get_roles(correo))
	if "System Manager" in roles:
		frappe.throw(
			_("{0} es administrador del sistema; se gestiona en el escritorio.").format(correo),
			frappe.PermissionError,
		)
	if cambiar and correo == frappe.session.user:
		frappe.throw(_("No puede cambiar su propio usuario desde aquí."), frappe.PermissionError)
	if "System Manager" in frappe.get_roles():
		return
	if "QSG Gerente" in roles and frappe.db.get_value("User", correo, "owner") != frappe.session.user:
		frappe.throw(_("Solo quien creó a ese administrador puede cambiarlo."), frappe.PermissionError)


def _clave() -> str:
	return f"Qsg-{secrets.token_hex(4)}"


def _lista(valor) -> list[str]:
	if isinstance(valor, str):
		try:
			valor = json.loads(valor)
		except ValueError:
			valor = re.split(r"[,;\n]+", valor)
	return [str(x).strip() for x in (valor or []) if str(x).strip()]


def equipo() -> dict:
	"""Usuarios con perfil de QSG, sus cuadrillas, y los catálogos para dar de alta a uno nuevo."""
	_exigir_gerencia()
	roles = frappe.get_all(
		"Has Role",
		filters={"role": ("in", list(ROL.values())), "parenttype": "User", "parent": ("not in", INTOCABLES)},
		fields=["parent", "role"],
	)
	correos = sorted({r.parent for r in roles})
	usuarios = {
		u.name: u
		for u in frappe.get_all(
			"User",
			filters={"name": ("in", correos or [""])},
			fields=["name", "full_name", "enabled", "mobile_no", "owner", "last_active"],
		)
	}
	miembros = frappe.get_all(
		"QSG Cuadrilla Miembro",
		filters={"user": ("in", correos or [""]), "parenttype": "QSG Cuadrilla"},
		fields=["user", "parent"],
	)
	cuadrillas = {
		c.name: c
		for c in frappe.get_all(
			"QSG Cuadrilla", fields=["name", "contractor", "base_zone", "active"], limit=2000
		)
	}
	ultimo = {}
	for p in frappe.get_all(
		"QSG Ubicacion",
		filters={"ping_time": (">=", nowdate())},
		fields=["crew", "ping_time"],
		order_by="ping_time desc",
		limit=5000,
	):
		ultimo.setdefault(p.crew, p.ping_time)
	ahora = now_datetime()
	demo = _usuarios_demo()
	lista = []
	for correo in correos:
		u = usuarios.get(correo)
		if not u:
			continue
		crews = [m.parent for m in miembros if m.user == correo and m.parent in cuadrillas]
		c = cuadrillas.get(crews[0]) if crews else None
		ping = ultimo.get(crews[0]) if crews else None
		lista.append(
			{
				"usuario": correo,
				"nombre": u.full_name,
				"perfil": perfil(correo),
				"activo": cint(u.enabled),
				"telefono": u.mobile_no,
				"cuadrilla": crews[0] if crews else None,
				"contratista": c.contractor if c else None,
				"zona": c.base_zone if c else None,
				"gps_hace_min": int((ahora - get_datetime(ping)).total_seconds() // 60) if ping else None,
				"demo": correo in demo,
				"yo": correo == frappe.session.user,
			}
		)
	orden = {ADMINISTRADOR: 0, DESPACHADOR: 1, SUPERVISOR: 2, CONTRATISTA: 3}
	lista.sort(key=lambda x: (orden.get(x["perfil"], 9), x["nombre"] or ""))
	return {
		"usuarios": lista,
		"contratistas": frappe.get_all(
			"QSG Contratista",
			fields=["name", "status", "current_grade", "current_score", "active_crews"],
			order_by="name asc",
		),
		"habilidades": frappe.get_all("QSG Habilidad", pluck="name", order_by="name asc"),
		"municipios": frappe.get_all(
			"QSG Zona Municipio",
			filters={"parenttype": "QSG Zona"},
			fields=["municipality as municipio", "parent as zona"],
			order_by="municipality asc",
		),
		"perfiles": list(ROL),
	}


def guardar_usuario(
	perfil_nuevo: str,
	correo: str,
	nombre: str | None = None,
	telefono: str | None = None,
	contratista: str | None = None,
	municipio: str | None = None,
	habilidades=None,
	cupo: int | None = None,
	turno_desde: str | None = None,
	turno_hasta: str | None = None,
) -> dict:
	"""Da de alta un usuario con su perfil, o cambia el de uno existente. Un contratista queda con su
	empresa y su cuadrilla (punto de salida, zona y habilidades), listo para recibir órdenes."""
	_exigir_gerencia()
	if perfil_nuevo not in ROL:
		frappe.throw(_("Perfil no válido."))
	correo = (correo or "").strip().lower()
	if not frappe.utils.validate_email_address(correo):
		frappe.throw(_("El correo {0} no es válido.").format(correo or "(vacío)"))
	nombre = (nombre or "").strip()[:80]
	telefono = (telefono or "").strip()[:30] or None
	nuevo = not frappe.db.exists("User", correo)
	if nuevo and not nombre:
		frappe.throw(_("Escriba el nombre."))
	if not nuevo:
		_puede_gestionar(correo)
	# Se valida todo antes de crear nada: un alta a medias no deja un usuario suelto
	cuadrilla = _datos_de_cuadrilla(correo, municipio, habilidades) if perfil_nuevo == CONTRATISTA else None
	turno = _turno(turno_desde, turno_hasta)
	if perfil_nuevo == SUPERVISOR and not (contratista or "").strip():
		frappe.throw(_("Indique el contratista (empresa) que supervisa."))

	if nuevo:
		frappe.get_doc(
			{
				"doctype": "User",
				"email": correo,
				"first_name": nombre,
				"mobile_no": None,
				"send_welcome_email": 0,
				"language": "es",
			}
		).insert(ignore_permissions=True)
	u = frappe.get_doc("User", correo)
	if nombre and not nuevo:
		u.first_name, u.last_name = nombre, None
	actuales = {r.role for r in u.roles}
	for r in list(u.roles):
		if r.role in ROL.values() and r.role != ROL[perfil_nuevo]:
			u.remove(r)
	if ROL[perfil_nuevo] not in actuales:
		u.append("roles", {"role": ROL[perfil_nuevo]})
	u.enabled = 1
	contrasena = None
	if nuevo:
		contrasena = _clave()
		u.new_password = contrasena
	u.save(ignore_permissions=True)

	resultado = {"usuario": correo, "perfil": perfil_nuevo, "contrasena": contrasena, "nuevo": nuevo}
	nombre = nombre or u.full_name
	if perfil_nuevo == CONTRATISTA:
		resultado.update(
			_cuadrilla_del_contratista(correo, nombre, telefono, contratista, cuadrilla, cupo, turno)
		)
	elif perfil_nuevo == SUPERVISOR:
		empresa = _empresa(contratista, None, telefono, correo)
		if not frappe.db.exists(
			"User Permission", {"user": correo, "allow": "QSG Contratista", "for_value": empresa}
		):
			frappe.get_doc(
				{
					"doctype": "User Permission",
					"user": correo,
					"allow": "QSG Contratista",
					"for_value": empresa,
				}
			).insert(ignore_permissions=True)
		resultado["contratista"] = empresa
	return resultado


def _empresa(contratista, nombre, telefono, correo) -> str:
	empresa = (contratista or nombre or "").strip()[:120]
	if not empresa:
		frappe.throw(_("Indique el contratista (empresa)."))
	if not frappe.db.exists("QSG Contratista", empresa):
		frappe.get_doc(
			{
				"doctype": "QSG Contratista",
				"contractor_name": empresa,
				"status": "Activo",
				"contact_name": nombre,
				"phone": telefono,
				"email": correo,
			}
		).insert(ignore_permissions=True)
	return empresa


def _codigo_nuevo() -> str:
	n = frappe.db.count("QSG Cuadrilla") + 1
	while frappe.db.exists("QSG Cuadrilla", f"CUA-{n:03d}"):
		n += 1
	return f"CUA-{n:03d}"


def _datos_de_cuadrilla(correo, municipio, habilidades) -> dict:
	"""Punto de salida, zona y habilidades; obligatorios si el contratista aún no tiene cuadrilla."""
	from qsg_pmo.api import mis_cuadrillas

	habilidades = [h for h in _lista(habilidades) if frappe.db.exists("QSG Habilidad", h)]
	muni = territorio.municipio(municipio) if municipio else None
	punto = territorio.ubicacion(muni) if muni else None
	propias = mis_cuadrillas(correo)
	if not propias:
		if not punto:
			frappe.throw(_("Elija el municipio de salida del contratista."))
		if not habilidades:
			frappe.throw(_("Marque al menos una habilidad (qué trabajos puede hacer)."))
	zona = (
		frappe.db.get_value("QSG Zona Municipio", {"municipality": muni, "parenttype": "QSG Zona"}, "parent")
		if muni
		else None
	)
	return {
		"propia": propias[0] if propias else None,
		"punto": punto,
		"zona": zona,
		"habilidades": habilidades,
	}


def _turno(desde, hasta) -> tuple[str, str] | None:
	"""Horario de trabajo de la cuadrilla (HH:MM). Fuera de él no se le recomiendan órdenes."""
	if not (desde or hasta):
		return None
	valores = []
	for v in (desde, hasta):
		m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?", (v or "").strip())
		if not m or int(m[1]) > 23 or int(m[2]) > 59:
			frappe.throw(_("Escriba el turno como HH:MM, por ejemplo 07:00 y 17:00."))
		valores.append(f"{int(m[1]):02d}:{m[2]}:00")
	if valores[0] >= valores[1]:
		frappe.throw(_("La hora de salida del turno debe ser posterior a la de entrada."))
	return valores[0], valores[1]


def _cuadrilla_del_contratista(correo, nombre, telefono, contratista, datos, cupo, turno=None) -> dict:
	if datos["propia"]:
		crew = frappe.get_doc("QSG Cuadrilla", datos["propia"])
	else:
		crew = frappe.get_doc(
			{
				"doctype": "QSG Cuadrilla",
				"crew_code": _codigo_nuevo(),
				"contractor": _empresa(contratista, nombre, telefono, correo),
				"leader_name": nombre,
				"active": 1,
				"shift_start": "07:00:00",
				"shift_end": "17:00:00",
				"max_orders_per_day": 5,
			}
		)
		crew.append(
			"members", {"member_name": nombre, "user": correo, "role_in_crew": "Líder", "phone": telefono}
		)
	if datos["punto"]:
		crew.start_latitude, crew.start_longitude = datos["punto"]
		crew.base_zone = datos["zona"] or crew.base_zone
	if datos["habilidades"]:
		crew.set("skills", [{"skill": h} for h in datos["habilidades"]])
	if cint(cupo):
		crew.max_orders_per_day = min(max(cint(cupo), 1), 20)
	if turno:
		crew.shift_start, crew.shift_end = turno
	crew.active = 1
	crew.save(ignore_permissions=True)
	return {"cuadrilla": crew.name, "contratista": crew.contractor, "zona": crew.base_zone}


def estado_usuario(correo: str, activo: int) -> dict:
	"""Activa o desactiva un usuario. Si es el único usuario de su cuadrilla, la cuadrilla deja de
	recibir recomendaciones mientras esté desactivado."""
	_exigir_gerencia()
	correo = (correo or "").strip().lower()
	if not frappe.db.exists("User", correo):
		frappe.throw(_("No existe el usuario {0}.").format(correo))
	_puede_gestionar(correo)
	activo = 1 if cint(activo) else 0
	frappe.db.set_value("User", correo, "enabled", activo)
	if not activo:
		clear_sessions(user=correo, force=True)
	for crew in frappe.get_all(
		"QSG Cuadrilla Miembro", filters={"user": correo, "parenttype": "QSG Cuadrilla"}, pluck="parent"
	):
		otros = frappe.db.count(
			"QSG Cuadrilla Miembro",
			{"parent": crew, "parenttype": "QSG Cuadrilla", "user": ("not in", (correo, ""))},
		)
		if not otros:
			frappe.db.set_value("QSG Cuadrilla", crew, "active", activo)
	return {"usuario": correo, "activo": activo}


def nueva_clave(correo: str) -> dict:
	_exigir_gerencia()
	correo = (correo or "").strip().lower()
	if not frappe.db.exists("User", correo):
		frappe.throw(_("No existe el usuario {0}.").format(correo))
	_puede_gestionar(correo, cambiar=False)
	u = frappe.get_doc("User", correo)
	contrasena = _clave()
	u.new_password = contrasena
	u.save(ignore_permissions=True)
	return {"usuario": correo, "contrasena": contrasena}


# ---------------------------------------------------------------------- demostración
def _usuarios_demo() -> set[str]:
	from qsg_pmo.demo import TECH_EMAIL
	from qsg_pmo.inteligencia.demo_vivo import USUARIOS_DEMO

	return {*USUARIOS_DEMO, TECH_EMAIL}


def desactivar_demo(cuadrillas: int = 0) -> None:
	"""Para ``qsg-servidor.sh asegurar``: desactiva los usuarios de demostración (sus contraseñas son
	públicas) y, si se pide, las cuadrillas de demostración para que no se recomienden."""
	from qsg_pmo.demo import CREWS

	n = 0
	for correo in _usuarios_demo():
		if frappe.db.exists("User", correo) and cint(frappe.db.get_value("User", correo, "enabled")):
			frappe.db.set_value("User", correo, "enabled", 0)
			clear_sessions(user=correo, force=True)
			n += 1
	print(f"USUARIOS: {n}")
	if cint(cuadrillas):
		k = 0
		for code, *_resto in CREWS:
			if frappe.db.exists("QSG Cuadrilla", code) and cint(
				frappe.db.get_value("QSG Cuadrilla", code, "active")
			):
				frappe.db.set_value("QSG Cuadrilla", code, "active", 0)
				k += 1
		print(f"CUADRILLAS: {k}")
