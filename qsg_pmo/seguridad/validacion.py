# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Validación y limpieza de lo que llega por la API."""

import base64
import ipaddress
import re

import frappe
from frappe.utils import flt
from frappe.utils.html_utils import clean_html

from qsg_pmo.seguridad.eventos import denegar, rechazar

TAG_RE = re.compile(r"<[^>]*>")
CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
SIGNATURE_RE = re.compile(r"^data:image/png;base64,[A-Za-z0-9+/=]+$")
MAX_SIGNATURE_BYTES = 300 * 1024


def texto(value, max_len=500):
	"""Texto plano: sin etiquetas HTML, sin caracteres de control y con largo máximo."""
	if value is None:
		return None
	value = str(value)
	if "<" in value or "&lt;" in value:
		value = TAG_RE.sub("", clean_html(value))
		value = TAG_RE.sub("", value.replace("&lt;", "<").replace("&gt;", ">"))
	value = CONTROL_RE.sub("", value).strip()
	return value[:max_len]


def coordenadas(lat, lng, reference_name=None):
	"""Devuelve (lat, lng) válidos o (None, None). Rechaza coordenadas imposibles."""
	if lat in (None, "") or lng in (None, ""):
		return None, None
	try:
		lat, lng = float(lat), float(lng)
	except TypeError, ValueError:
		rechazar("Coordenadas GPS no válidas.", f"lat={lat!r} lng={lng!r}", "QSG Orden", reference_name)
	if not (-90 <= lat <= 90 and -180 <= lng <= 180):
		rechazar("Coordenadas GPS fuera de rango.", f"lat={lat} lng={lng}", "QSG Orden", reference_name)
	return lat, lng


def firma(value, reference_name=None):
	"""La firma solo puede ser una imagen PNG en data URL y de tamaño razonable."""
	if not value:
		return None
	value = str(value).strip()
	if not SIGNATURE_RE.match(value) or len(value) > MAX_SIGNATURE_BYTES * 4 / 3 + 30:
		rechazar(
			"La firma no es una imagen válida.",
			f"firma rechazada ({len(value)} caracteres)",
			"QSG Orden",
			reference_name,
		)
	try:
		raw = base64.b64decode(value.split(",", 1)[1])
	except ValueError:
		raw = b""
	if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
		rechazar(
			"La firma no es una imagen PNG.", "firma con contenido que no es PNG", "QSG Orden", reference_name
		)
	return value


NUMBER_RE = re.compile(r"^\s*-?\d+([.,]\d+)?\s*$")


def numero(value, reference_name=None):
	"""Medición numérica (acepta coma o punto decimal)."""
	if value in (None, ""):
		return value
	if not NUMBER_RE.match(str(value)):
		rechazar("La medición debe ser un número.", f"medición {value!r}", "QSG Orden", reference_name)
	return str(flt(str(value).strip().replace(",", "."), 6))


def foto_de_la_orden(file_url, order_name):
	"""La foto de evidencia tiene que ser un archivo de imagen subido a esta misma orden."""
	if not file_url:
		return None
	f = frappe.db.get_value(
		"File",
		{"file_url": file_url, "attached_to_doctype": "QSG Orden", "attached_to_name": order_name},
		["name", "file_url"],
		as_dict=True,
	)
	if not f:
		rechazar(
			"La foto no pertenece a esta orden. Tómela de nuevo desde la app.",
			f"foto ajena o inexistente: {file_url}",
			"QSG Orden",
			order_name,
		)
	return f.file_url


def ip_permitida_para_integracion():
	"""Si QSG Configuracion tiene una lista de IPs o redes, solo esas pueden usar la integración."""
	allowed = (frappe.db.get_single_value("QSG Configuracion", "integration_allowed_ips") or "").strip()
	if not allowed:
		return
	ip = getattr(frappe.local, "request_ip", None)
	if not ip:
		return  # llamada interna (bench, pruebas, tareas programadas)
	try:
		addr = ipaddress.ip_address(ip)
	except ValueError:
		denegar("IP no permitida.", f"IP inválida {ip}", event_type="IP no permitida")
	for item in re.split(r"[\s,;]+", allowed):
		if not item:
			continue
		try:
			if addr in ipaddress.ip_network(item, strict=False):
				return
		except ValueError:
			continue
	denegar(
		"Esta IP no está autorizada para la integración.",
		f"IP {ip} fuera de la lista permitida",
		event_type="IP no permitida",
	)
