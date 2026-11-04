// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt

frappe.listview_settings["QSG Orden"] = {
	add_fields: ["status", "sla_status", "is_rework"],
	get_indicator(doc) {
		const map = {
			Recibida: "gray",
			"Asignada a contratista": "blue",
			Programada: "purple",
			"En ruta": "yellow",
			"En sitio": "orange",
			Completada: "green",
			"No completada": "red",
			Reprogramada: "pink",
			Cancelada: "darkgrey",
		};
		return [__(doc.status), map[doc.status] || "gray", "status,=," + doc.status];
	},
	onload(listview) {
		listview.page.add_actions_menu_item(__("Asignar a contratista"), () => {
			const names = listview.get_checked_items(true);
			if (!names.length) return frappe.msgprint(__("Seleccione órdenes."));
			const d = new frappe.ui.Dialog({
				title: __("Asignar {0} órdenes a contratista", [names.length]),
				fields: [
					{ fieldname: "contractor", fieldtype: "Link", options: "QSG Contratista", label: __("Contratista"), reqd: 1 },
					{ fieldname: "reason", fieldtype: "Small Text", label: __("Motivo (si cambia de contratista)") },
				],
				primary_action_label: __("Asignar"),
				primary_action(values) {
					frappe
						.call("qsg_pmo.qsg_pmo.doctype.qsg_orden.qsg_orden.assign_contractor", { names, ...values })
						.then((r) => {
							d.hide();
							frappe.show_alert({ message: __("{0} órdenes asignadas", [r.message.length]), indicator: "green" });
							listview.refresh();
						});
				},
			});
			d.show();
		});
	},
};
