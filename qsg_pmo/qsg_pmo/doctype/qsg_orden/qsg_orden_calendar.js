// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt

// Agenda de cuadrillas: filtre por Cuadrilla o Contratista en la vista de calendario
frappe.views.calendar["QSG Orden"] = {
	field_map: {
		start: "estimated_arrival",
		end: "estimated_finish",
		id: "name",
		title: "subscriber_name",
		allDay: 0,
	},
	filters: [
		{ fieldtype: "Link", fieldname: "crew", options: "QSG Cuadrilla", label: __("Cuadrilla") },
		{ fieldtype: "Link", fieldname: "contractor", options: "QSG Contratista", label: __("Contratista") },
	],
	get_events_method: "frappe.desk.calendar.get_events",
};
