// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt

frappe.query_reports["Estado de Seguridad"] = {
	filters: [],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "estado" && data) {
			const color = { OK: "green", ALERTA: "orange", FALLA: "red" }[data.estado] || "gray";
			value = `<span class="indicator-pill ${color}">${frappe.utils.escape_html(data.estado)}</span>`;
		}
		return value;
	},
};
