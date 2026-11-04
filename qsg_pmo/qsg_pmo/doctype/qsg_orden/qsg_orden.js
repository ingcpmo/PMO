// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt

frappe.ui.form.on("QSG Orden", {
	refresh(frm) {
		const colors = { "En tiempo": "green", "En riesgo": "orange", Vencido: "red", Cumplido: "green", Incumplido: "red" };
		if (frm.doc.sla_status) {
			frm.dashboard.add_indicator(__("SLA: {0}", [__(frm.doc.sla_status)]), colors[frm.doc.sla_status] || "gray");
		}
		if (frm.doc.is_rework) {
			frm.dashboard.add_indicator(__("Retrabajo en garantía de {0}", [frm.doc.rework_of]), "red");
		}
		if (frm.doc.arrival_out_of_range) {
			frm.dashboard.add_indicator(__("Llegada a {0} m de la dirección", [frm.doc.arrival_distance_m]), "orange");
		}
		if (frm.is_new()) return;

		const field_actions = __("Campo");
		if (frm.doc.status === "Programada") {
			frm.add_custom_button(__("Salir hacia el sitio"), () => set_status(frm, "En ruta"), field_actions);
		}
		if (["Programada", "En ruta"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Llegué al sitio"), () => mark_arrival(frm), field_actions);
		}
		if (["Recibida", "Asignada a contratista", "Programada", "En ruta", "Reprogramada"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Reasignar"), () => reassign_dialog(frm), __("Despacho"));
		}
	},
});

function set_status(frm, status) {
	frm.set_value("status", status);
	frm.save();
}

function mark_arrival(frm) {
	const save = (lat, lng) => {
		frm.set_value("status", "En sitio");
		if (lat) {
			frm.set_value("arrival_latitude", lat);
			frm.set_value("arrival_longitude", lng);
		}
		frm.save();
	};
	if (!navigator.geolocation) return save();
	navigator.geolocation.getCurrentPosition(
		(pos) => save(pos.coords.latitude, pos.coords.longitude),
		() => save(),
		{ enableHighAccuracy: true, timeout: 10000 }
	);
}

function reassign_dialog(frm) {
	const d = new frappe.ui.Dialog({
		title: __("Reasignar orden"),
		fields: [
			{ fieldname: "contractor", fieldtype: "Link", options: "QSG Contratista", label: __("Contratista"), default: frm.doc.contractor },
			{
				fieldname: "crew",
				fieldtype: "Link",
				options: "QSG Cuadrilla",
				label: __("Cuadrilla (opcional)"),
				get_query: () => ({ filters: { active: 1, contractor: d.get_value("contractor") || undefined } }),
			},
			{ fieldname: "reason", fieldtype: "Small Text", label: __("Motivo"), reqd: 1 },
		],
		primary_action_label: __("Reasignar"),
		primary_action(values) {
			frm.call("reassign", values).then(() => {
				d.hide();
				frm.reload_doc();
			});
		},
	});
	d.show();
}
