#!/usr/bin/env python3
"""Pruebas de ataque contra un servidor de QSG PMO (solo sitios de prueba).

Simula lo que intentaría un atacante o un usuario malintencionado desde fuera, por HTTP:
acceso sin sesión, robo de órdenes de otra cuadrilla, cambios por la API REST saltándose la
app, inyección SQL y HTML, archivos maliciosos, fuerza bruta, abuso de la API, etc.

    python3 auditoria/ataques.py --base http://localhost:8080 --datos datos.json --salida resultado.json

``datos.json`` sale de ``bench --site <sitio> execute qsg_pmo.seguridad.auditoria.preparar``.
Cada prueba dice qué se intentó, qué se esperaba (el ataque bloqueado) y qué pasó.
"""

import argparse
import base64
import json
import re
import sys
import time

import requests

PNG_1PX = base64.b64decode(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)
RESULTS = []


class Client:
	def __init__(self, base, host=None):
		self.base = base.rstrip("/")
		self.s = requests.Session()
		self.csrf = None
		if host:
			self.s.headers["Host"] = host

	def login(self, usr, pwd):
		r = self.s.post(self.base + "/api/method/login", data={"usr": usr, "pwd": pwd})
		if r.status_code == 200:
			page = self.s.get(self.base + "/campo")
			m = re.search(r'data-csrf="([^"]+)"', page.text) or re.search(r'QSG_CSRF = "([^"]+)"', page.text)
			self.csrf = m.group(1) if m else None
		return r

	def get(self, path, **kw):
		return self.s.get(self.base + path, **kw)

	def post(self, path, json_body=None, csrf=True, **kw):
		headers = kw.pop("headers", {})
		if csrf and self.csrf:
			headers["X-Frappe-CSRF-Token"] = self.csrf
		return self.s.post(self.base + path, json=json_body, headers=headers, **kw)

	def put(self, path, json_body, **kw):
		headers = {"X-Frappe-CSRF-Token": self.csrf} if self.csrf else {}
		return self.s.put(self.base + path, json=json_body, headers=headers, **kw)

	def delete(self, path):
		headers = {"X-Frappe-CSRF-Token": self.csrf} if self.csrf else {}
		return self.s.delete(self.base + path, headers=headers)


def check(cid, categoria, nombre, bloqueado, evidencia):
	RESULTS.append(
		{
			"id": cid,
			"categoria": categoria,
			"ataque": nombre,
			"resultado": "BLOQUEADO" if bloqueado else "VULNERABLE",
			"evidencia": evidencia,
		}
	)
	mark = "OK " if bloqueado else "!! "
	print(f"{mark}{cid:>3}  {categoria:<22} {nombre}  →  {evidencia}")


def short(r):
	body = r.text[:160].replace("\n", " ")
	return f"HTTP {r.status_code} {body}"


def denied(r):
	"""Rechazado por el servidor (y no porque el método no exista)."""
	if "has no attribute" in r.text or "Fallo al obtener el método" in r.text:
		return False
	return r.status_code in (401, 403, 417, 400, 429) or '"exc_type": "PermissionError"' in r.text


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--base", default="http://localhost:8080")
	ap.add_argument("--host", default=None, help="Cabecera Host, si el servidor atiende varios sitios")
	ap.add_argument("--datos", required=True)
	ap.add_argument("--salida", default="resultado-ataques.json")
	a = ap.parse_args()
	d = json.load(open(a.datos))
	B, H = a.base, a.host
	own, other, closed = d["orden_propia"], d["orden_ajena"], d["orden_cerrada"]
	api = "/api/method/qsg_pmo.api."

	guest = Client(B, H)
	tech = Client(B, H)
	tech.login(d["tecnico"]["user"], d["tecnico"]["password"])
	disp = Client(B, H)
	disp.login(d["users"]["despachador"], d["password"])
	sup = Client(B, H)
	sup.login(d["users"]["supervisor"], d["password"])
	for who, c in (("técnico", tech), ("despachador", disp), ("supervisor", sup)):
		if not c.csrf:
			sys.exit(f"No se pudo iniciar sesión como {who}; revise datos.json")
	liberty = requests.Session()
	liberty.headers["Authorization"] = "token " + d["liberty_token"]
	if H:
		liberty.headers["Host"] = H

	# ------------------------------------------------------------------ autenticación
	r = guest.get(api + "mis_ordenes")
	check(1, "Autenticación", "Leer órdenes sin iniciar sesión", denied(r), short(r))
	r = guest.get("/api/resource/QSG Orden")
	check(2, "Autenticación", "Listar órdenes por REST sin sesión", denied(r), short(r))
	r = guest.post(
		"/api/method/frappe.core.doctype.user.user.sign_up",
		data={"email": "intruso@mail.com", "full_name": "Intruso", "redirect_to": "/app"},
	)
	created = "Please check your email" in r.text or "verification" in r.text.lower()
	check(3, "Autenticación", "Auto-registrarse como usuario nuevo", not created, short(r))

	# ------------------------------------------------------------------ CSRF
	r = tech.post(api + "cambiar_estado", {"name": own, "estado": "En ruta"}, csrf=False)
	check(4, "CSRF", "Cambiar estado sin token CSRF (petición forjada)", denied(r), short(r))

	# ------------------------------------------------------------------ control de acceso (IDOR)
	r = tech.get(api + "orden", params={"name": other})
	check(5, "Control de acceso", "Técnico lee orden de otra cuadrilla (app)", denied(r), short(r))
	r = tech.get(f"/api/resource/QSG Orden/{other}")
	check(6, "Control de acceso", "Técnico lee orden de otra cuadrilla (REST)", denied(r), short(r))
	r = tech.get("/api/resource/QSG Orden", params={"fields": '["name","crew"]', "limit": 500})
	crews = {x.get("crew") for x in r.json().get("data", [])} if r.ok else set()
	check(
		7,
		"Control de acceso",
		"Técnico lista todas las órdenes (REST)",
		crews <= {"CUA-FTTH-01"},
		f"cuadrillas visibles: {sorted(c for c in crews if c)}",
	)
	r = tech.put(f"/api/resource/QSG Orden/{own}", {"customer_rating": "1", "priority": "Baja"})
	check(8, "Control de acceso", "Técnico edita su orden por REST saltándose la app", denied(r), short(r))
	r = tech.delete(f"/api/resource/QSG Orden/{d['orden_borrable']}")
	still = disp.get(f"/api/resource/QSG Orden/{d['orden_borrable']}").status_code == 200
	check(9, "Control de acceso", "Técnico borra una orden", denied(r) and still, short(r))
	r = tech.put("/api/resource/QSG Codigo de Cierre/CLI-AUS", {"billable": 0})
	check(10, "Control de acceso", "Técnico cambia un código de cierre (catálogo)", denied(r), short(r))
	r = tech.post(api + "recibir_orden", {"external_order_id": "HACK-1", "work_type": "FTTH-RECON"})
	check(11, "Control de acceso", "Técnico crea órdenes por la API de integración", denied(r), short(r))
	r = sup.get(f"/api/resource/QSG Orden/{other}")
	check(12, "Control de acceso", "Supervisor lee orden de otro contratista", denied(r), short(r))
	r = sup.post(
		"/api/resource/QSG Evaluacion Contratista",
		{
			"contractor": "Fibra Boricua LLC",
			"period_start": "2026-10-01",
			"period_end": "2026-10-31",
			"score": 100,
		},
	)
	check(13, "Control de acceso", "Supervisor se califica a sí mismo", denied(r), short(r))
	r = disp.put(f"/api/resource/QSG Orden/{closed}", {"closure_code": "COMP-OK", "status": "Completada"})
	check(14, "Integridad", "Cambiar el cierre de una orden ya cerrada", denied(r), short(r))
	r = tech.put("/api/resource/QSG Configuracion/QSG Configuracion", {"warranty_days": 0})
	check(15, "Control de acceso", "Técnico cambia la configuración (garantía)", denied(r), short(r))

	# ------------------------------------------------------------------ inyección
	r = tech.get(api + "mis_ordenes", params={"cuadrilla": "x' OR '1'='1"})
	check(
		16,
		"Inyección SQL",
		"Parámetro con inyección SQL en la app",
		denied(r) or r.json().get("message") == [],
		short(r),
	)
	r = tech.get(
		"/api/resource/QSG Orden",
		params={"filters": '[["name","like","%\' OR 1=1 -- "]]', "fields": '["name"]'},
	)
	leaked = r.ok and len(r.json().get("data", [])) > 0
	check(17, "Inyección SQL", "Inyección SQL en filtros REST", not leaked, short(r))
	payload = '<img src=x onerror="alert(document.cookie)">Ana'
	r = liberty.post(
		B + api + "recibir_orden",
		json={
			"customer": d["cliente"],
			"external_order_id": f"XSS-{int(time.time())}",
			"work_type": "FTTH-RECON",
			"subscriber_name": payload,
			"address": "<script>alert(1)</script>",
			"municipality": "San Juan",
			"zone": "Metro",
		},
	)
	stored = ""
	if r.ok:
		name = r.json()["message"]["name"]
		stored = disp.get(f"/api/resource/QSG Orden/{name}").json().get("data", {}).get("subscriber_name", "")
	check(
		18,
		"Inyección HTML/XSS",
		"Orden con código JavaScript en nombre y dirección",
		r.ok and "<" not in stored,
		f"guardado: {stored!r}" if r.ok else short(r),
	)

	# ------------------------------------------------------------------ evidencia y archivos
	files = {
		"file": (
			"evil.html",
			b"<script>fetch('/api/method/frappe.auth.get_logged_user')</script>",
			"text/html",
		)
	}
	r = disp.s.post(
		B + "/api/method/upload_file",
		files=files,
		data={"doctype": "QSG Orden", "docname": own, "is_private": "1"},
		headers={"X-Frappe-CSRF-Token": disp.csrf or ""},
	)
	check(19, "Archivos", "Subir un HTML con script como evidencia", denied(r), short(r))
	svg = b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"></svg>'
	r = disp.s.post(
		B + "/api/method/upload_file",
		files={"file": ("foto.svg", svg, "image/svg+xml")},
		data={"doctype": "QSG Orden", "docname": own, "is_private": "1"},
		headers={"X-Frappe-CSRF-Token": disp.csrf or ""},
	)
	check(20, "Archivos", "Subir un SVG con script disfrazado de foto", denied(r), short(r))
	r = tech.s.post(
		B + api + "subir_foto",
		files={"file": ("fake.jpg", b"MZ\x90\x00 esto es un ejecutable", "image/jpeg")},
		data={"name": own},
		headers={"X-Frappe-CSRF-Token": tech.csrf or ""},
	)
	check(21, "Archivos", "Subir un ejecutable renombrado a .jpg", denied(r), short(r))
	big = PNG_1PX + b"\0" * (12 * 1024 * 1024)
	r = tech.s.post(
		B + api + "subir_foto",
		files={"file": ("grande.png", big, "image/png")},
		data={"name": own},
		headers={"X-Frappe-CSRF-Token": tech.csrf or ""},
	)
	check(22, "Archivos", "Subir una foto de 12 MB (agotar disco)", denied(r), short(r))
	r = tech.s.post(
		B + api + "subir_foto",
		files={"file": ("ok.png", PNG_1PX, "image/png")},
		data={"name": other},
		headers={"X-Frappe-CSRF-Token": tech.csrf or ""},
	)
	check(23, "Archivos", "Subir foto a una orden de otra cuadrilla", denied(r), short(r))
	# foto de otra orden reutilizada como evidencia propia
	tech.post(api + "cambiar_estado", {"name": own, "estado": "En sitio", "lat": 18.45, "lng": -66.07})
	o = tech.get(api + "orden", params={"name": own}).json().get("message", {})
	photo_row = next((x["name"] for x in o.get("checklist", []) if x["item_type"] == "Foto"), None)
	foreign = "/private/files/evidencia-de-otra-orden.jpg"
	r = tech.post(api + "guardar_checklist", {"name": own, "filas": [{"name": photo_row, "photo": foreign}]})
	saved = r.ok and any(x.get("photo") == foreign for x in r.json()["message"]["checklist"])
	check(
		24,
		"Integridad",
		"Usar como evidencia una foto que no es de la orden",
		not saved,
		short(r) if not saved else "la foto ajena quedó guardada",
	)
	r = tech.post(api + "cambiar_estado", {"name": own, "estado": "En sitio", "lat": 999, "lng": -999})
	check(
		25,
		"Validación",
		"GPS imposible (lat 999)",
		denied(r) or r.json()["message"].get("arrival_latitude") != 999,
		short(r),
	)
	r = tech.post(api + "cerrar", {"name": own, "codigo": "CLI-AUS", "firma": "javascript:alert(1)"})
	check(26, "Validación", "Firma con contenido no válido", denied(r), short(r))

	# ------------------------------------------------------------------ abuso y fuerza bruta
	codes = []
	for _ in range(130):
		codes.append(tech.get(api + "codigos_cierre").status_code)
		if codes[-1] == 429:
			break
	check(
		27,
		"Abuso de API",
		"130 peticiones seguidas (bot o script)",
		429 in codes,
		f"{len(codes)} peticiones, códigos: {sorted(set(codes))}",
	)
	victim = Client(B, H)
	for _ in range(7):
		victim.login(d["users"]["victima"], "adivinando123")
	r = victim.login(d["users"]["victima"], d["password"])
	check(28, "Fuerza bruta", "7 contraseñas erróneas y luego la correcta", r.status_code != 200, short(r))

	# ------------------------------------------------------------------ servidor
	r = tech.get("/campo")
	h = {k.lower(): v for k, v in r.headers.items()}
	needed = [
		"x-frame-options",
		"x-content-type-options",
		"content-security-policy",
		"referrer-policy",
		"permissions-policy",
	]
	missing = [x for x in needed if x not in h]
	check(
		29,
		"Cabeceras",
		"Cabeceras de seguridad en la app de campo",
		not missing,
		f"faltan: {missing}" if missing else "todas presentes",
	)
	r = tech.get(f"/api/resource/QSG Orden/{other}")
	check(
		30,
		"Fuga de información",
		"Los errores muestran código fuente (traceback)",
		"Traceback" not in r.text,
		short(r),
	)

	# ------------------------------------------------------------------ más control de acceso
	bodega = Client(B, H)
	bodega.login(d["users"]["bodega"], d["password"])
	r = bodega.post(api + "cerrar", {"name": own, "codigo": "CLI-AUS"})
	check(31, "Control de acceso", "Bodega cierra una orden desde la API de campo", denied(r), short(r))
	r = sup.get(api + "orden", params={"name": other})
	check(32, "Control de acceso", "Supervisor abre orden de otro contratista en la app", denied(r), short(r))
	r = liberty.post(
		B + api + "recibir_orden",
		json={
			"customer": d["cliente"],
			"external_order_id": f"MASS-{int(time.time())}",
			"work_type": "FTTH-RECON",
			"subscriber_name": "Prueba masiva",
			"status": "Completada",
			"closure_code": "COMP-OK",
			"customer_rating": "1",
			"is_rework": 1,
			"crew": "CUA-HFC-01",
		},
	)
	ok_mass = False
	if r.ok:
		n = r.json()["message"]["name"]
		doc = disp.get(f"/api/resource/QSG Orden/{n}").json().get("data", {})
		ok_mass = (
			doc.get("status") == "Recibida"
			and not doc.get("closure_code")
			and not doc.get("crew")
			and not doc.get("is_rework")
		)
	check(
		33,
		"Integridad",
		"Integración intenta fijar estado, cierre y cuadrilla",
		ok_mass,
		"campos ignorados" if ok_mass else short(r),
	)
	r = tech.get(api + "mis_ordenes", params={"cuadrilla": "CUA-HFC-01"})
	leak = r.ok and any(x.get("crew") == "CUA-HFC-01" for x in r.json().get("message", []))
	check(34, "Control de acceso", "Técnico pide la ruta de otra cuadrilla", not leak, short(r))

	ok = sum(1 for x in RESULTS if x["resultado"] == "BLOQUEADO")
	print(f"\n{ok} de {len(RESULTS)} ataques bloqueados")
	json.dump(
		{"base": B, "fecha": time.strftime("%Y-%m-%d %H:%M"), "resultados": RESULTS},
		open(a.salida, "w"),
		ensure_ascii=False,
		indent=1,
	)
	sys.exit(0 if ok == len(RESULTS) else 1)


if __name__ == "__main__":
	main()
