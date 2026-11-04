// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt

frappe.ui.form.on("QSG Plan de Despacho", {
	refresh(frm) {
		if (frm.is_new()) return;
		if (frm.doc.status !== "Aprobado") {
			frm.add_custom_button(__("Generar propuesta"), () => {
				frm.call("generate_proposal").then((r) => {
					frm.reload_doc();
					frappe.show_alert({
						message: __("{0} asignadas, {1} sin asignar", [r.message.assigned, r.message.unassigned]),
						indicator: "green",
					});
				});
			}).addClass("btn-primary");
		}
		if (frm.doc.status === "Propuesto") {
			frm.add_custom_button(__("Aprobar y publicar"), () => {
				frappe.confirm(__("¿Asignar las órdenes a las cuadrillas y generar las solicitudes de materiales?"), () => {
					frm.call("approve").then((r) => {
						frm.reload_doc();
						const n = (r.message.material_requests || []).length;
						frappe.show_alert({ message: __("Plan aprobado. Solicitudes de materiales: {0}", [n]), indicator: "green" });
					});
				});
			});
		}
	},
});
