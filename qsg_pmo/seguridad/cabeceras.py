# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Cabeceras HTTP de seguridad. Se aplican al final de cada petición (hook ``after_request``)."""

import frappe

from qsg_pmo.seguridad.eventos import guardar_pendientes

# La app de campo no usa scripts en línea ni recursos externos: política estricta.
CSP_CAMPO = "; ".join(
	[
		"default-src 'self'",
		"script-src 'self'",
		"style-src 'self' 'unsafe-inline'",
		"img-src 'self' data: blob:",
		"connect-src 'self'",
		"font-src 'self'",
		"manifest-src 'self'",
		"object-src 'none'",
		"base-uri 'self'",
		"form-action 'self'",
		"frame-ancestors 'self'",
	]
)
# Escritorio de Frappe: no se puede incrustar en otros sitios ni cargar plugins.
CSP_GENERAL = "object-src 'none'; base-uri 'self'; frame-ancestors 'self'"


def after_request(response=None, request=None):
	guardar_pendientes()
	if response is None or request is None:
		return
	h = response.headers
	h.setdefault("X-Frame-Options", "SAMEORIGIN")
	h.setdefault("X-Content-Type-Options", "nosniff")
	h.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
	h.setdefault("Permissions-Policy", "geolocation=(self), camera=(self), microphone=(), payment=(), usb=()")
	h.setdefault("Cross-Origin-Opener-Policy", "same-origin")
	path = request.path or ""
	if path == "/campo" or path.startswith("/campo/"):
		h["Content-Security-Policy"] = CSP_CAMPO
		h["Cache-Control"] = "no-store"
	elif "Content-Security-Policy" not in h:
		h["Content-Security-Policy"] = CSP_GENERAL
	if path.startswith("/api/"):
		h.setdefault("Cache-Control", "no-store")
	if _is_https(request):
		h.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")


def _is_https(request):
	return request.scheme == "https" or request.headers.get("X-Forwarded-Proto", "") == "https"
