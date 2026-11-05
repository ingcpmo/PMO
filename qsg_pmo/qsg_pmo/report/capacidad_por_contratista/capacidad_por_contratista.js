// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt

frappe.query_reports["Capacidad por Contratista"] = {
	filters: [{ fieldname: "date", label: __("Fecha"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 }],
};
