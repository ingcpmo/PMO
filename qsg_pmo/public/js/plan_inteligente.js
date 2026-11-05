// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt
// Botones de inteligencia en QSG Plan de Despacho (se suman a los del formulario, no los reemplazan).

frappe.ui.form.on("QSG Plan de Despacho", {
	refresh(frm) {
		if (frm.is_new()) return;
		const despacho = frappe.user.has_role(["System Manager", "QSG Gerente", "QSG Despachador"]);
		if (despacho && frm.doc.status !== "Aprobado") {
			frm.add_custom_button(
				__("Optimizar rutas"),
				() => {
					frappe
						.call({
							method: "qsg_pmo.inteligencia.api.optimizar_plan",
							args: { plan: frm.doc.name },
							freeze: true,
							freeze_message: __("Optimizando rutas y asignaciones…"),
						})
						.then((r) => {
							const m = r.message || {};
							frm.reload_doc();
							frappe.msgprint({
								title: __("Plan optimizado"),
								indicator: "green",
								message:
									`<p><b>${frappe.utils.escape_html(m.resumen || "")}</b></p>` +
									`<div style="white-space:pre-wrap">${frappe.utils.escape_html(m.explicacion || "")}</div>` +
									`<p class="text-muted small">${__("Revise y apruebe el plan como siempre.")}</p>`,
							});
						});
				},
				__("Inteligencia"),
			);
		}
		if (frm.doc.status === "Aprobado" && frappe.user.has_role(["System Manager", "QSG Gerente", "QSG Despachador", "QSG Bodega"])) {
			frm.add_custom_button(
				__("Ajustar materiales al stock del camión"),
				() => {
					frappe.confirm(__("¿Reducir las solicitudes de materiales de este plan a lo que falta en cada camión?"), () => {
						frappe
							.call({ method: "qsg_pmo.inteligencia.api.ajustar_materiales_del_plan", args: { plan: frm.doc.name }, freeze: true })
							.then((r) => {
								const lineas = r.message || [];
								frm.reload_doc();
								frappe.msgprint(lineas.length ? lineas.map(frappe.utils.escape_html).join("<br>") : __("No había solicitudes para ajustar."));
							});
					});
				},
				__("Inteligencia"),
			);
		}
		frm.add_custom_button(__("Tablero de despacho"), () => window.open(`/despacho?fecha=${encodeURIComponent(frm.doc.plan_date)}`), __("Inteligencia"));
	},
});
