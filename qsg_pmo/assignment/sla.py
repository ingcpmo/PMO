"""Cálculo del estado de SLA de una orden (función pura)."""

from __future__ import annotations

from datetime import datetime, timedelta

OPEN = "En tiempo"
AT_RISK = "En riesgo"
OVERDUE = "Vencido"
MET = "Cumplido"
BREACHED = "Incumplido"

CLOSED_STATUSES = {"Completada", "No completada", "Cancelada"}


def sla_status(
	status: str,
	sla_due: datetime | None,
	now: datetime,
	finished_on: datetime | None = None,
	risk_minutes: int = 120,
	stops_sla: bool = False,
) -> str | None:
	"""Devuelve el estado del SLA.

	- Orden cerrada: Cumplido si terminó antes del vencimiento, o si el código
	  de cierre detiene el reloj (p. ej. cliente ausente); si no, Incumplido.
	- Orden abierta: Vencido, En riesgo (faltan menos de ``risk_minutes``) o En tiempo.
	"""
	if not sla_due:
		return None
	if status in CLOSED_STATUSES:
		if status == "Cancelada" or stops_sla:
			return MET
		end = finished_on or now
		return MET if end <= sla_due else BREACHED
	if now > sla_due:
		return OVERDUE
	if sla_due - now <= timedelta(minutes=risk_minutes):
		return AT_RISK
	return OPEN
