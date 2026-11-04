// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt

frappe.query_reports["Liquidacion de Contratistas"] = {
	filters: [
		{ fieldname: "from_date", label: __("Desde"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), -30), reqd: 1 },
		{ fieldname: "to_date", label: __("Hasta"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "contractor", label: __("Contratista"), fieldtype: "Link", options: "QSG Contratista" },
	],
};
