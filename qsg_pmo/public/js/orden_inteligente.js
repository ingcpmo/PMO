// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt
// «Mejor cuadrilla» en QSG Orden: quién puede llegar antes, con las razones, y asignar con un clic.

frappe.ui.form.on("QSG Orden", {
	refresh(frm) {
		if (frm.is_new()) return;
		const abiertas = ["Recibida", "Asignada a contratista", "Programada", "En ruta", "Reprogramada"];
		if (!abiertas.includes(frm.doc.status)) return;
		if (!frappe.user.has_role(["System Manager", "QSG Gerente", "QSG Despachador"])) return;
		frm.add_custom_button(__("Mejor cuadrilla"), () => qsg_mejor_cuadrilla(frm), __("Inteligencia"));
	},
});

function qsg_mejor_cuadrilla(frm) {
	const esc = frappe.utils.escape_html;
	frappe
		.call({
			method: "qsg_pmo.inteligencia.api.mejor_cuadrilla",
			args: { orden: frm.doc.name, ignorar_contratista: frm.doc.contractor ? 0 : 1 },
			freeze: true,
		})
		.then((r) => {
			const data = r.message || {};
			const opciones = data.opciones || [];
			if (!opciones.length) {
				frappe.msgprint(__("Ninguna cuadrilla con la habilidad puede llegar dentro de la ventana y del turno."));
				return;
			}
			const filas = opciones
				.map(
					(o, i) => `<tr>
						<td><b>${i + 1}. ${esc(o.cuadrilla)}</b><br><span class="text-muted small">${esc(o.contratista || "")}</span></td>
						<td>${esc(frappe.datetime.str_to_user(o.llegada))}</td>
						<td class="small">${o.razones.map(esc).join("<br>")}</td>
						<td><button class="btn btn-xs btn-primary" data-crew="${esc(o.cuadrilla)}">${__("Asignar")}</button></td>
					</tr>`,
				)
				.join("");
			const aviso = data.ubicacion_aproximada ? `<p class="text-warning small">${__("La orden no tiene GPS: se usó el centro del municipio.")}</p>` : "";
			const d = new frappe.ui.Dialog({
				title: __("Mejor cuadrilla para {0}", [frm.doc.name]),
				size: "large",
				fields: [{ fieldtype: "HTML", fieldname: "tabla" }],
			});
			d.fields_dict.tabla.$wrapper.html(
				`${aviso}<table class="table table-bordered"><thead><tr><th>${__("Cuadrilla")}</th><th>${__("Llegada")}</th><th>${__("Por qué")}</th><th></th></tr></thead><tbody>${filas}</tbody></table>`,
			);
			d.fields_dict.tabla.$wrapper.on("click", "button[data-crew]", (e) => {
				const crew = e.currentTarget.dataset.crew;
				frappe.prompt(
					{ fieldname: "motivo", fieldtype: "Data", label: __("Motivo"), reqd: 1, default: __("Sugerencia de mejor cuadrilla") },
					(v) => {
						frappe
							.call({ method: "qsg_pmo.inteligencia.api.reasignar", args: { orden: frm.doc.name, cuadrilla: crew, motivo: v.motivo }, freeze: true })
							.then(() => {
								d.hide();
								frm.reload_doc();
								frappe.show_alert({ message: __("Orden asignada a {0}", [crew]), indicator: "green" });
							});
					},
					__("Asignar a {0}", [crew]),
				);
			});
			d.show();
		});
}
