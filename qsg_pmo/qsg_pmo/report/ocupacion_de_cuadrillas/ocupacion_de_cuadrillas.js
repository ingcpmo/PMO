// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt

frappe.query_reports["Ocupacion de Cuadrillas"] = {
	filters: [
		{ fieldname: "date", label: __("Fecha"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "contractor", label: __("Contratista"), fieldtype: "Link", options: "QSG Contratista" },
		{ fieldname: "zone", label: __("Zona"), fieldtype: "Link", options: "QSG Zona" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "availability" && data && data.availability !== __("Disponible")) {
			value = `<span style="color: var(--red-600)">${value}</span>`;
		}
		return value;
	},
};
