# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Límite de peticiones por usuario (o IP sin sesión) y por método, con ventana de un minuto."""

from functools import wraps

import frappe
from frappe.utils import cint, now_datetime

from qsg_pmo.seguridad.eventos import registrar

DEFAULT_PER_MINUTE = 120


class LimiteExcedido(frappe.RateLimitExceededError):
	http_status_code = 429


def _configured_limit():
	try:
		return (
			cint(frappe.db.get_single_value("QSG Configuracion", "rate_limit_per_minute"))
			or DEFAULT_PER_MINUTE
		)
	except Exception:
		return DEFAULT_PER_MINUTE


def limitar(por_minuto=None, factor=1.0):
	"""Decorador. ``por_minuto`` fijo, o el valor de QSG Configuracion multiplicado por ``factor``."""

	def decorator(fn):
		@wraps(fn)
		def wrapper(*args, **kwargs):
			if getattr(frappe.local, "request", None) is not None:
				limit = por_minuto or max(1, int(_configured_limit() * factor))
				identity = frappe.session.user
				if identity == "Guest":
					identity = getattr(frappe.local, "request_ip", None) or "Guest"
				window = now_datetime().strftime("%Y%m%d%H%M")
				key = frappe.cache.make_key(f"qsg_rl:{fn.__name__}:{identity}:{window}")
				count = frappe.cache.incrby(key, 1)
				if count == 1:
					frappe.cache.expire(key, 70)
				if count > limit:
					if count == limit + 1:
						registrar(
							"Límite de peticiones", f"{fn.__name__}: más de {limit} peticiones por minuto"
						)
					frappe.throw(
						"Demasiadas peticiones seguidas. Espere un minuto y vuelva a intentar.",
						LimiteExcedido,
					)
			return fn(*args, **kwargs)

		return wrapper

	return decorator
