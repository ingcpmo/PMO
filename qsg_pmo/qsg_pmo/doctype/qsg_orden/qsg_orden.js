// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt

frappe.ui.form.on("QSG Orden", {
	refresh(frm) {
		const colors = { "En tiempo": "green", "En riesgo": "orange", Vencido: "red", Cumplido: "green", Incumplido: "red" };
		if (frm.doc.sla_status) {
			frm.dashboard.add_indicator(__("SLA: {0}", [__(frm.doc.sla_status)]), colors[frm.doc.sla_status] || "gray");
		}
		if (!frm.is_new() && ["Asignada", "En ruta"].includes(frm.doc.status)) {
			frm.add_custom_button(__("Llegué al sitio"), () => mark_arrival(frm));
		}
	},
});

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
