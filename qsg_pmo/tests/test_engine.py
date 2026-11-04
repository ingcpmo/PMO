"""Pruebas del motor de asignación y del cálculo de SLA (sin base de datos)."""

import unittest
from datetime import datetime, timedelta

from qsg_pmo.assignment.engine import (
	REASON_NO_CAPACITY,
	REASON_NO_LOCATION,
	REASON_NO_SKILL,
	REASON_NO_WINDOW,
	Crew,
	Job,
	plan,
)
from qsg_pmo.assignment.sla import AT_RISK, BREACHED, MET, OPEN, OVERDUE, sla_status

DAY = datetime(2026, 11, 5)
# Coordenadas aproximadas en Puerto Rico
SAN_JUAN = (18.4655, -66.1057)
BAYAMON = (18.3985, -66.1557)
CAGUAS = (18.2341, -66.0485)
PONCE = (18.0111, -66.6141)


def at(h, m=0):
	return DAY + timedelta(hours=h, minutes=m)


def job(order, loc, start=8, end=12, skills=("FTTH-RES",), priority="Normal", duration=90, zone=None):
	return Job(
		order=order,
		latitude=loc[0] if loc else None,
		longitude=loc[1] if loc else None,
		window_start=at(start),
		window_end=at(end),
		duration_minutes=duration,
		skills=set(skills),
		priority=priority,
		zone=zone,
	)


def crew(name, loc, skills=("FTTH-RES",), max_orders=6, zone=None):
	return Crew(
		crew=name,
		latitude=loc[0],
		longitude=loc[1],
		shift_start=at(7),
		shift_end=at(17),
		skills=set(skills),
		max_orders=max_orders,
		zone=zone,
	)


class TestEngine(unittest.TestCase):
	def test_assigns_nearest_qualified_crew(self):
		jobs = [job("O1", CAGUAS)]
		crews = [crew("C-SJ", SAN_JUAN), crew("C-CAG", CAGUAS)]
		assigned, unassigned = plan(jobs, crews)
		self.assertEqual(unassigned, [])
		self.assertEqual(assigned[0].crew, "C-CAG")

	def test_respects_skills(self):
		jobs = [job("O1", CAGUAS, skills=("HFC-RES",))]
		crews = [crew("C-CAG", CAGUAS, skills=("FTTH-RES",)), crew("C-SJ", SAN_JUAN, skills=("HFC-RES",))]
		assigned, _ = plan(jobs, crews)
		self.assertEqual(assigned[0].crew, "C-SJ")

	def test_no_skill_reason(self):
		_, unassigned = plan([job("O1", CAGUAS, skills=("FTTH-EMP",))], [crew("C1", CAGUAS)])
		self.assertEqual(unassigned[0].reason, REASON_NO_SKILL)

	def test_capacity(self):
		jobs = [job("O1", CAGUAS, end=17), job("O2", CAGUAS, end=17)]
		assigned, unassigned = plan(jobs, [crew("C1", CAGUAS, max_orders=1)])
		self.assertEqual(len(assigned), 1)
		self.assertEqual(unassigned[0].reason, REASON_NO_CAPACITY)

	def test_window_cannot_be_met(self):
		# Ponce desde San Juan con ventana muy corta que ya pasó al terminar la primera
		jobs = [job("O1", SAN_JUAN, start=8, end=9, duration=480), job("O2", PONCE, start=8, end=9)]
		assigned, unassigned = plan(jobs, [crew("C1", SAN_JUAN)])
		self.assertEqual([a.order for a in assigned], ["O1"])
		self.assertEqual(unassigned[0].reason, REASON_NO_WINDOW)

	def test_missing_location(self):
		_, unassigned = plan([job("O1", None)], [crew("C1", CAGUAS)])
		self.assertEqual(unassigned[0].reason, REASON_NO_LOCATION)

	def test_priority_goes_first(self):
		jobs = [job("NORMAL", BAYAMON), job("CRIT", BAYAMON, priority="Crítica")]
		assigned, _ = plan(jobs, [crew("C1", SAN_JUAN)])
		self.assertEqual(assigned[0].order, "CRIT")
		self.assertEqual(assigned[0].sequence, 1)

	def test_waits_for_window_and_sequences(self):
		jobs = [job("AM", BAYAMON, start=8, end=12), job("PM", BAYAMON, start=13, end=17)]
		assigned, _ = plan(jobs, [crew("C1", BAYAMON)])
		by_order = {a.order: a for a in assigned}
		self.assertEqual(by_order["PM"].estimated_arrival, at(13))
		self.assertEqual(by_order["PM"].sequence, 2)

	def test_balances_load(self):
		jobs = [job(f"O{i}", SAN_JUAN, end=17, duration=60) for i in range(4)]
		assigned, _ = plan(jobs, [crew("A", SAN_JUAN), crew("B", SAN_JUAN)])
		counts = {}
		for a in assigned:
			counts[a.crew] = counts.get(a.crew, 0) + 1
		self.assertEqual(counts, {"A": 2, "B": 2})

	def test_deterministic(self):
		jobs = [job(f"O{i}", BAYAMON, end=17, duration=45) for i in range(5)]
		r1 = plan(jobs, [crew("A", SAN_JUAN), crew("B", CAGUAS)])
		r2 = plan(jobs, [crew("A", SAN_JUAN), crew("B", CAGUAS)])
		self.assertEqual(r1, r2)


class TestSla(unittest.TestCase):
	due = at(12)

	def test_open_states(self):
		self.assertEqual(sla_status("Asignada", self.due, at(8)), OPEN)
		self.assertEqual(sla_status("Asignada", self.due, at(11)), AT_RISK)
		self.assertEqual(sla_status("En sitio", self.due, at(13)), OVERDUE)

	def test_closed_states(self):
		self.assertEqual(sla_status("Completada", self.due, at(14), finished_on=at(11)), MET)
		self.assertEqual(sla_status("Completada", self.due, at(14), finished_on=at(13)), BREACHED)
		self.assertEqual(
			sla_status("No completada", self.due, at(14), finished_on=at(13), stops_sla=True), MET
		)

	def test_no_due(self):
		self.assertIsNone(sla_status("Recibida", None, at(8)))


if __name__ == "__main__":
	unittest.main()
