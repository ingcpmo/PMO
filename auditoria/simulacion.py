#!/usr/bin/env python3
"""Simulación de una petición de Liberty de inicio a fin, por HTTP, con cada usuario real.

    python3 auditoria/simulacion.py --base http://localhost:8080 --datos datos.json --salida simulacion.json

1. Liberty envía la orden (token de API)               → Recibida
2. Despacho genera y aprueba el plan del día           → Programada, con cuadrilla y hora estimada
3. El técnico la ve en su ruta, sale y llega (GPS)     → En ruta → En sitio
4. El técnico sube fotos, llena el checklist y cierra  → Completada, con firma
5. Liberty consulta el estado                          → Completada
6. Despacho registra la encuesta del cliente
7. Gerencia evalúa al contratista y saca la liquidación
8. Gerencia revisa el estado de seguridad y los eventos

Cada petición queda registrada (método, ruta, datos, respuesta y tiempo) en el JSON de salida.
"""

import argparse
import base64
import io
import json
import struct
import sys
import time
import zlib

import requests

LOG = []
STEPS = []


def jpeg_bytes():
	"""Foto JPEG real y pequeña (sin depender de Pillow)."""
	try:
		from PIL import Image

		buf = io.BytesIO()
		Image.new("RGB", (64, 48), (30, 120, 200)).save(buf, "JPEG")
		return buf.getvalue()
	except ImportError:
		return base64.b64decode(
			"/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/wAALCAABAAEBAREA/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/2gAIAQEAAD8AKp//2Q=="
		)


def png_signature():
	"""Firma: PNG válido de 120x40 con un trazo."""
	w, h = 120, 40
	rows = b""
	for y in range(h):
		row = bytearray([0])
		for x in range(w):
			ink = abs(y - (20 + int(10 * __import__("math").sin(x / 12)))) < 2
			row += b"\x00\x00\x00\xff" if ink else b"\xff\xff\xff\x00"
		rows += bytes(row)

	def chunk(t, d):
		return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

	png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
	png += chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")
	return "data:image/png;base64," + base64.b64encode(png).decode()


def mask(value):
	if isinstance(value, dict):
		return {k: ("***" if k in ("pwd", "Authorization") else mask(v)) for k, v in value.items()}
	if isinstance(value, str) and value.startswith("data:image"):
		return value[:40] + f"… ({len(value)} caracteres)"
	return value


class Actor:
	def __init__(self, base, quien):
		self.base, self.quien = base.rstrip("/"), quien
		self.s = requests.Session()
		self.csrf = None

	def login(self, usr, pwd):
		r = self.call("POST", "/api/method/login", data={"usr": usr, "pwd": pwd})
		page = self.s.get(self.base + "/campo")
		import re

		m = re.search(r'data-csrf="([^"]+)"', page.text)
		self.csrf = m.group(1) if m else None
		return r

	def token(self, token):
		self.s.headers["Authorization"] = f"token {token}"

	def call(self, method, path, paso=None, **kw):
		headers = kw.pop("headers", {})
		if self.csrf and method != "GET":
			headers["X-Frappe-CSRF-Token"] = self.csrf
		t0 = time.time()
		r = self.s.request(method, self.base + path, headers=headers, **kw)
		ms = int((time.time() - t0) * 1000)
		try:
			body = r.json()
		except ValueError:
			body = r.text[:300]
		payload = kw.get("json") or kw.get("data") or kw.get("params")
		if "files" in kw:
			payload = {**(payload or {}), "file": f"<{len(kw['files']['file'][1])} bytes JPEG>"}
		LOG.append(
			{
				"n": len(LOG) + 1,
				"paso": paso or (STEPS[-1]["paso"] if STEPS else ""),
				"actor": self.quien,
				"metodo": method,
				"ruta": path,
				"datos": mask(payload),
				"http": r.status_code,
				"ms": ms,
				"respuesta": mask(
					body.get("message", body.get("data", body)) if isinstance(body, dict) else body
				),
			}
		)
		if not r.ok:
			raise RuntimeError(f"{self.quien} {method} {path} → {r.status_code}: {str(body)[:400]}")
		return body.get("message", body.get("data")) if isinstance(body, dict) else body


def paso(n, titulo):
	STEPS.append({"paso": n, "titulo": titulo, "inicio": len(LOG)})
	print(f"\n== {n}. {titulo}")


def ok(msg):
	STEPS[-1].setdefault("resultados", []).append(msg)
	print("   ✓", msg)


def main():
	ap = argparse.ArgumentParser()
	ap.add_argument("--base", default="http://localhost:8080")
	ap.add_argument("--datos", required=True)
	ap.add_argument("--salida", default="simulacion.json")
	a = ap.parse_args()
	d = json.load(open(a.datos))
	B, pw = a.base, d["password"]
	ext = f"LIB-SIM-{time.strftime('%Y%m%d-%H%M%S')}"
	result = {"base": B, "orden_liberty": ext, "inicio": time.strftime("%Y-%m-%d %H:%M:%S")}

	liberty = Actor(B, "Liberty (integración)")
	liberty.token(d["liberty_token"])
	disp, tech, ger = Actor(B, "Despachador"), Actor(B, "Técnico"), Actor(B, "Gerente")

	try:
		# 1 ---------------------------------------------------------------------------------
		paso(1, "Liberty envía la orden de trabajo")
		hoy = liberty.call("GET", "/api/method/qsg_pmo.api.yo")["hoy"]
		r = liberty.call(
			"POST",
			"/api/method/qsg_pmo.api.recibir_orden",
			json={
				"customer": d["cliente"],
				"external_order_id": ext,
				"work_type": "FTTH-RECON",
				"subscriber_name": "María Rivera (simulación)",
				"phone": "787-555-0142",
				"address": "Calle Loíza 1500",
				"municipality": "San Juan",
				"zone": "Metro",
				"latitude": 18.4655,
				"longitude": -66.1057,
				"appointment_date": hoy,
				"window_start": "07:00:00",
				"window_end": "23:59:00",
				"priority": "Alta",
			},
		)
		order = r["name"]
		result["orden"] = order
		ok(f"Orden {order} creada en estado «{r['status']}», vence SLA {r['sla_due']}")
		r = liberty.call(
			"POST",
			"/api/method/qsg_pmo.api.recibir_orden",
			json={"customer": d["cliente"], "external_order_id": ext, "phone": "787-555-0199"},
		)
		ok(f"Reenvío de la misma orden: actualizada, no duplicada (created={r['created']})")

		# 2 ---------------------------------------------------------------------------------
		paso(2, "Despacho planifica y aprueba la ruta del día")
		disp.login(d["users"]["despachador"], pw)
		plan = disp.call(
			"POST",
			"/api/resource/QSG Plan de Despacho",
			json={"plan_date": hoy, "zone": "Metro", "engine": "Reglas"},
		)
		r = disp.call(
			"POST",
			"/api/method/run_doc_method",
			json={"dt": "QSG Plan de Despacho", "dn": plan["name"], "method": "generate_proposal"},
		)
		ok(f"Plan {plan['name']}: propuesta generada")
		p = disp.call("GET", f"/api/resource/QSG Plan de Despacho/{plan['name']}")
		row = next((x for x in p["assignments"] if x["order"] == order), None)
		if not row:
			raise RuntimeError(
				f"El motor no asignó la orden: {[u for u in p.get('unassigned', []) if u.get('order') == order]}"
			)
		ok(
			f"El motor asignó {order} a {row['crew']} (visita #{row['sequence']}, llegada estimada {row['estimated_arrival']})"
		)
		disp.call(
			"POST",
			"/api/method/run_doc_method",
			json={"dt": "QSG Plan de Despacho", "dn": plan["name"], "method": "approve"},
		)
		o = disp.call("GET", f"/api/resource/QSG Orden/{order}")
		ok(f"Plan aprobado: orden en «{o['status']}», cuadrilla {o['crew']} de {o['contractor']}")
		if o["crew"] != "CUA-FTTH-01":
			disp.call(
				"PUT",
				f"/api/resource/QSG Orden/{order}",
				json={"crew": "CUA-FTTH-01", "contractor": "Fibra Boricua LLC"},
			)
			ok("Despacho reasignó la orden a CUA-FTTH-01 (cuadrilla del técnico de prueba)")

		# 3 ---------------------------------------------------------------------------------
		paso(3, "El técnico ve la orden en su ruta, sale y llega")
		tech.login(d["tecnico"]["user"], d["tecnico"]["password"])
		ruta = tech.call("GET", "/api/method/qsg_pmo.api.mis_ordenes", params={"fecha": hoy})
		if order not in [x["name"] for x in ruta]:
			raise RuntimeError("La orden no aparece en la ruta del técnico")
		ok(f"La orden aparece en la ruta del técnico ({len(ruta)} órdenes hoy)")
		tech.call("POST", "/api/method/qsg_pmo.api.cambiar_estado", json={"name": order, "estado": "En ruta"})
		r = tech.call(
			"POST",
			"/api/method/qsg_pmo.api.cambiar_estado",
			json={"name": order, "estado": "En sitio", "lat": 18.46552, "lng": -66.10571},
		)
		ok(f"En sitio con GPS; fuera de rango = {r['arrival_out_of_range']}")

		# 4 ---------------------------------------------------------------------------------
		paso(4, "Evidencia, checklist y cierre con firma")
		filas = []
		for c in r["checklist"]:
			if c["item_type"] == "Foto":
				f = tech.call(
					"POST",
					"/api/method/qsg_pmo.api.subir_foto",
					data={"name": order},
					files={"file": ("evidencia.jpg", jpeg_bytes(), "image/jpeg")},
				)
				filas.append({"name": c["name"], "photo": f["file_url"]})
			elif c["item_type"] == "Sí/No":
				filas.append({"name": c["name"], "value": "Sí"})
			elif c["item_type"] == "Medición":
				lo, hi = c.get("min_value"), c.get("max_value")
				val = (lo + hi) / 2 if lo is not None and hi is not None and (lo or hi) else (lo or 0) + 1
				filas.append({"name": c["name"], "value": str(round(val, 2))})
			else:
				filas.append({"name": c["name"], "value": "Conforme"})
		ok(f"{sum(1 for x in filas if 'photo' in x)} fotos subidas (validadas por contenido)")
		r = tech.call(
			"POST",
			"/api/method/qsg_pmo.api.guardar_checklist",
			json={"name": order, "filas": json.dumps(filas)},
		)
		ok(
			f"Checklist guardado: {sum(1 for c in r['checklist'] if c['compliant'])}/{len(r['checklist'])} puntos conformes"
		)
		r = tech.call(
			"POST",
			"/api/method/qsg_pmo.api.cerrar",
			json={
				"name": order,
				"codigo": "COMP-OK",
				"notas": "Servicio reconectado, señal verificada con el cliente.",
				"firma": png_signature(),
				"lat": 18.46552,
				"lng": -66.10571,
			},
		)
		ok(f"Orden cerrada: «{r['status']}», firma = {bool(r['has_signature'])}")

		# 5 ---------------------------------------------------------------------------------
		paso(5, "Liberty consulta el estado")
		r = liberty.call(
			"GET",
			"/api/method/qsg_pmo.api.estado_orden",
			params={"external_order_id": ext, "customer": d["cliente"]},
		)
		result["estado_final"] = r
		ok(
			f"Liberty ve «{r['status']}», SLA «{r['sla_status']}», cierre {r['closure_code']}, terminada {r['finished_on']}"
		)

		# 6 ---------------------------------------------------------------------------------
		paso(6, "Encuesta de satisfacción del cliente")
		e = disp.call(
			"POST",
			"/api/resource/QSG Encuesta",
			json={"order": order, "rating": "5", "nps": 9, "channel": "Llamada", "comments": "Muy puntual."},
		)
		ok(f"Encuesta {e['name']}: 5 estrellas, recomendación 9/10")

		# 7 ---------------------------------------------------------------------------------
		paso(7, "Gerencia evalúa al contratista y liquida")
		ger.login(d["users"]["gerente"], pw)
		periodo = {"contractor": "Fibra Boricua LLC", "period_start": hoy, "period_end": hoy}
		prev = ger.call(
			"GET", "/api/resource/QSG Evaluacion Contratista", params={"filters": json.dumps(periodo)}
		)
		if prev:  # la simulación se puede repetir: se recalcula la del día
			ev = ger.call("PUT", f"/api/resource/QSG Evaluacion Contratista/{prev[0]['name']}", json=periodo)
		else:
			ev = ger.call("POST", "/api/resource/QSG Evaluacion Contratista", json=periodo)
		ok(
			f"Evaluación {ev['name']}: puntaje {ev['score']} ({ev['grade']}), {ev['orders_total']} órdenes, cumplimiento de ventana {ev['window_compliance']}%"
		)
		rep = ger.call(
			"POST",
			"/api/method/frappe.desk.query_report.run",
			json={
				"report_name": "Liquidacion de Contratistas",
				"filters": {"from_date": hoy, "to_date": hoy, "contractor": "Fibra Boricua LLC"},
			},
		)
		filas = [x for x in rep["result"] if isinstance(x, dict)]
		ok(f"Liquidación del día: {len(filas)} filas")
		result["liquidacion"] = filas[:10]

		# 8 ---------------------------------------------------------------------------------
		paso(8, "Gerencia revisa la seguridad")
		rep = ger.call(
			"POST",
			"/api/method/frappe.desk.query_report.run",
			json={"report_name": "Estado de Seguridad", "filters": {}},
		)
		result["estado_seguridad"] = [x for x in rep["result"] if isinstance(x, dict)]
		res = {}
		for x in result["estado_seguridad"]:
			res[x.get("estado")] = res.get(x.get("estado"), 0) + 1
		ok(f"Autodiagnóstico: {res}")
		ev = ger.call(
			"GET",
			"/api/resource/QSG Evento Seguridad",
			params={"fields": json.dumps(["event_type", "severity"]), "limit_page_length": 500},
		)
		ok(f"{len(ev)} eventos de seguridad registrados visibles para gerencia")
		result["ok"] = True
	except Exception as e:
		result["ok"] = False
		result["error"] = str(e)
		print("\n!! La simulación se detuvo:", e)

	result["fin"] = time.strftime("%Y-%m-%d %H:%M:%S")
	result["pasos"] = STEPS
	result["peticiones"] = LOG
	json.dump(result, open(a.salida, "w"), ensure_ascii=False, indent=1, default=str)
	print(
		f"\n{'Simulación completa' if result['ok'] else 'Simulación con error'}: {len(LOG)} peticiones → {a.salida}"
	)
	sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
	main()
