"""Materiales: qué recoger en bodega, qué devolver y qué consumo no cuadra.

La solicitud de materiales del plan de despacho pedía el kit completo de cada orden aunque el
camión ya tuviera material; así se acumula inventario en los camiones. Aquí se calcula el neto:

    recoger = objetivo - lo que ya hay en el camión
    objetivo = necesidad del día x (1 + margen), o el stock base que la cuadrilla siempre lleva

Los equipos con serial (ONT, módem, router) no se quedan de sobra en el camión: se lleva lo del día
más un repuesto y el resto se devuelve.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import date


def necesidades(
	asignaciones: list[tuple[str, str]], kits: dict[str, list[tuple[str, float]]]
) -> dict[str, dict[str, float]]:
	"""(cuadrilla, tipo de trabajo) por orden + kits por tipo -> cuadrilla -> artículo -> cantidad."""
	salida: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
	for cuadrilla, tipo in asignaciones:
		for item, qty in kits.get(tipo, []):
			salida[cuadrilla][item] += float(qty or 0)
	return {c: dict(items) for c, items in salida.items()}


def plan_bodega(
	necesidad: dict[str, dict[str, float]],
	stock_camion: dict[str, dict[str, float]],
	stock_central: dict[str, float] | None = None,
	margen_pct: float = 10.0,
	serializados: set[str] | None = None,
	repuesto_serializados: int = 1,
	stock_base: dict[str, float] | None = None,
	tolerancia_devolver_pct: float = 50.0,
) -> dict[str, dict]:
	"""Por cuadrilla: ``recoger``, ``devolver``, ``faltante_central`` y si ya está ``lista``."""
	serializados = serializados or set()
	stock_base = stock_base or {}
	cuadrillas = sorted(set(necesidad) | set(stock_camion))
	plan = {}
	pedido_total: dict[str, float] = defaultdict(float)
	for c in cuadrillas:
		nec = necesidad.get(c, {})
		camion = stock_camion.get(c, {})
		recoger, devolver = {}, {}
		for item in sorted(set(nec) | set(camion) | set(stock_base)):
			n = nec.get(item, 0.0)
			tiene = camion.get(item, 0.0)
			if item in serializados:
				objetivo = math.ceil(n) + (repuesto_serializados if n > 0 else 0)
			else:
				objetivo = max(math.ceil(n * (1 + margen_pct / 100)), stock_base.get(item, 0.0))
			if tiene < objetivo:
				recoger[item] = objetivo - tiene
				pedido_total[item] += objetivo - tiene
			elif item in serializados:
				if tiene > objetivo:
					devolver[item] = tiene - objetivo
			else:
				tolerancia = max(objetivo * tolerancia_devolver_pct / 100, 1)
				if tiene - objetivo > tolerancia:
					devolver[item] = math.floor(tiene - objetivo)
		plan[c] = {"recoger": recoger, "devolver": devolver, "faltante_central": {}, "lista": not recoger}

	if stock_central is not None:
		disponible = dict(stock_central)
		# Primero las cuadrillas que más necesitan, para no dejar a una sin nada
		for c in sorted(plan, key=lambda c: -sum(plan[c]["recoger"].values())):
			for item, qty in plan[c]["recoger"].items():
				dar = min(qty, max(disponible.get(item, 0.0), 0.0))
				disponible[item] = disponible.get(item, 0.0) - dar
				if dar < qty:
					plan[c]["faltante_central"][item] = qty - dar
	return plan


def conciliar(
	esperado: dict[str, float],
	real: list[tuple[str, float, str | None]],
	serializados: set[str] | None = None,
	tolerancia: float = 1.5,
) -> list[dict]:
	"""Compara el kit esperado de una orden con lo registrado (artículo, cantidad, serial)."""
	serializados = serializados or set()
	usado: dict[str, float] = defaultdict(float)
	hallazgos = []
	for item, qty, serial in real:
		usado[item] += float(qty or 0)
		if item in serializados and not serial:
			hallazgos.append(
				{
					"tipo": "Equipo sin serial",
					"item": item,
					"mensaje": f"{item} instalado sin número de serie.",
				}
			)
	for item, qty in usado.items():
		esperado_item = esperado.get(item, 0.0)
		if esperado_item and qty > esperado_item * tolerancia + 1:
			hallazgos.append(
				{
					"tipo": "Consumo mayor al kit",
					"item": item,
					"mensaje": f"Se registraron {qty:g} de {item}; el kit prevé {esperado_item:g}.",
				}
			)
	if esperado and not usado:
		hallazgos.append(
			{
				"tipo": "Consumo sin registrar",
				"item": None,
				"mensaje": "La orden no tiene materiales registrados.",
			}
		)
	return hallazgos


def consumo_por_cuadrilla(
	registros: list[tuple[str, str, float, float]], minimo_ordenes: int = 5
) -> list[dict]:
	"""(cuadrilla, artículo, esperado, real) por orden -> cuadrillas que gastan mucho más que el kit."""
	acumulado: dict[tuple[str, str], list[float]] = defaultdict(lambda: [0.0, 0.0, 0])
	for cuadrilla, item, esperado, real in registros:
		a = acumulado[(cuadrilla, item)]
		a[0] += esperado
		a[1] += real
		a[2] += 1
	salida = []
	for (cuadrilla, item), (esp, real, n) in sorted(acumulado.items()):
		if n >= minimo_ordenes and esp and real / esp >= 1.3:
			salida.append(
				{
					"cuadrilla": cuadrilla,
					"item": item,
					"ordenes": n,
					"veces_el_kit": round(real / esp, 2),
					"mensaje": f"{cuadrilla} usa {real / esp:.1f} veces el {item} previsto en {n} órdenes.",
				}
			)
	return salida


def equipos_estancados(equipos: list[tuple[str, str, str, date]], hoy: date, max_dias: int = 7) -> list[dict]:
	"""(serial, artículo, cuadrilla, fecha en que entró al camión) con más de ``max_dias`` sin instalar."""
	salida = []
	for serial, item, cuadrilla, desde in equipos:
		dias = (hoy - desde).days
		if dias > max_dias:
			salida.append(
				{
					"serial": serial,
					"item": item,
					"cuadrilla": cuadrilla,
					"dias": dias,
					"mensaje": f"{item} {serial} lleva {dias} días en el camión de {cuadrilla}: instalar o devolver.",
				}
			)
	return sorted(salida, key=lambda e: -e["dias"])
