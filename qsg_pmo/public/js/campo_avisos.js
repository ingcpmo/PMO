// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt
// Avisos de la app de campo. Mientras la app está abierta revisa cada minuto si el administrador
// asignó una orden nueva a la cuadrilla del usuario: suena, vibra y muestra una franja hasta que el
// contratista toca «Recibida». A los perfiles de despacho les muestra el acceso a su tablero.
(() => {
	if (!window.fetch) return;
	const API = "/api/method/qsg_pmo.inteligencia.api.";
	const CADA_MS = 60000;
	const csrf = () => window.QSG_CSRF || (document.getElementById("app") || { dataset: {} }).dataset.csrf || "";
	const esc = (s) =>
		String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
	let conocidas = null;
	let activo = true;

	async function llamar(metodo, args) {
		const opciones = { credentials: "same-origin", headers: { Accept: "application/json" } };
		if (args) {
			opciones.method = "POST";
			opciones.headers["X-Frappe-CSRF-Token"] = csrf();
			opciones.body = new URLSearchParams(args);
		}
		const r = await fetch(API + metodo, opciones);
		if (r.status === 401 || r.status === 403) activo = false;
		if (!r.ok) throw new Error(String(r.status));
		return ((await r.json()) || {}).message;
	}

	const estilo = document.createElement("style");
	estilo.textContent = `
		#qsg-avisos { position: fixed; left: 0; right: 0; bottom: 0; z-index: 900; background: #0b5cab; color: #fff;
			padding: 12px 16px calc(12px + env(safe-area-inset-bottom, 0px)); box-shadow: 0 -4px 16px rgba(0,0,0,.25);
			max-height: 60vh; overflow-y: auto; font: 15px/1.4 system-ui, sans-serif; }
		#qsg-avisos h3 { margin: 0 0 8px; font-size: 16px; }
		#qsg-avisos .aviso { display: flex; gap: 10px; align-items: center; justify-content: space-between;
			padding: 8px 0; border-top: 1px solid rgba(255,255,255,.25); }
		#qsg-avisos .aviso div { min-width: 0; }
		#qsg-avisos small { opacity: .85; }
		#qsg-avisos button { font: inherit; font-weight: 600; border: 0; border-radius: 10px; padding: 10px 14px;
			background: #fff; color: #0b5cab; white-space: nowrap; }
		#qsg-perfil { display: flex; gap: 8px; align-items: center; justify-content: space-between; padding: 8px 16px;
			background: #1d2733; color: #fff; font: 14px/1.3 system-ui, sans-serif; }
		#qsg-perfil a { color: #fff; font-weight: 600; background: #0b5cab; border-radius: 8px; padding: 6px 12px; text-decoration: none; }`;
	document.head.appendChild(estilo);

	function llamarLaAtencion() {
		try {
			if (navigator.vibrate) navigator.vibrate([300, 150, 300]);
			const C = window.AudioContext || window.webkitAudioContext;
			const c = new C();
			[0, 0.3].forEach((t) => {
				const o = c.createOscillator();
				const g = c.createGain();
				o.connect(g);
				g.connect(c.destination);
				o.frequency.value = 880;
				g.gain.setValueAtTime(0.2, c.currentTime + t);
				o.start(c.currentTime + t);
				o.stop(c.currentTime + t + 0.2);
			});
			setTimeout(() => c.close(), 1200);
		} catch (e) {
			/* sin sonido: queda la franja en pantalla */
		}
	}

	const corta = (v) => {
		const [h, m] = String(v || "").split(":");
		return h ? `${h.padStart(2, "0")}:${m || "00"}` : "";
	};
	const fecha = (f) => (f ? String(f).slice(5).split("-").reverse().join("/") : "");

	function pintar(lista) {
		let caja = document.getElementById("qsg-avisos");
		if (!lista.length) {
			if (caja) caja.remove();
			return;
		}
		if (!caja) {
			caja = document.createElement("div");
			caja.id = "qsg-avisos";
			caja.setAttribute("role", "alert");
			document.body.appendChild(caja);
			caja.addEventListener("click", async (e) => {
				const b = e.target.closest("button[data-orden]");
				if (!b) return;
				b.disabled = true;
				try {
					await llamar("confirmar_aviso", { orden: b.dataset.orden });
					await revisar();
					// La lista de la app se actualiza con su propio botón
					const actualizar = document.querySelector('[data-act="refresh"]');
					if (actualizar) actualizar.click();
				} catch (err) {
					b.disabled = false;
				}
			});
		}
		caja.innerHTML =
			`<h3>${lista.length === 1 ? "Tiene una orden nueva" : `Tiene ${lista.length} órdenes nuevas`}</h3>` +
			lista
				.map(
					(a) => `<div class="aviso"><div><b>${esc(a.suscriptor || a.orden)}</b><br>
					<small>${esc(fecha(a.fecha))} ${esc(corta(a.desde))}–${esc(corta(a.hasta))} · ${esc(a.municipio || "")} · ${esc(a.tipo || "")}${a.prioridad && a.prioridad !== "Normal" ? " · " + esc(a.prioridad) : ""}</small></div>
					<button data-orden="${esc(a.orden)}">Recibida</button></div>`,
				)
				.join("");
	}

	async function revisar() {
		if (!activo) return;
		let lista;
		try {
			lista = (await llamar("mis_avisos")) || [];
		} catch (e) {
			return; // sin señal: se intenta en la próxima vuelta
		}
		const nombres = lista.map((a) => a.orden);
		if (nombres.some((n) => !(conocidas || new Set()).has(n))) llamarLaAtencion();
		conocidas = new Set(nombres);
		pintar(lista);
	}

	async function iniciar() {
		try {
			const p = await llamar("mi_perfil");
			// Recién iniciada la sesión, administración y despacho van directo a su tablero
			if (p && p.inicio === "/despacho" && /\/login/.test(document.referrer)) {
				location.replace("/despacho");
				return;
			}
			if (p && p.inicio === "/despacho" && !document.getElementById("qsg-perfil")) {
				const barra = document.createElement("div");
				barra.id = "qsg-perfil";
				barra.innerHTML = `<span>Perfil ${esc((p.perfil || "").toLowerCase())}</span><a href="/despacho">Abrir despacho</a>`;
				document.body.insertBefore(barra, document.body.firstChild);
			}
			if (!p || !p.cuadrillas || !p.cuadrillas.length) return; // sin cuadrilla no hay avisos
		} catch (e) {
			/* se sigue con los avisos */
		}
		revisar();
		setInterval(() => {
			if (!document.hidden) revisar();
		}, CADA_MS);
		document.addEventListener("visibilitychange", () => {
			if (!document.hidden) revisar();
		});
	}
	iniciar();
})();
