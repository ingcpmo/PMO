/* QSG Campo: app del técnico (vanilla JS, sin compilación).
 * Usa la API de qsg_pmo/api.py. Funciona en cualquier navegador móvil moderno
 * y se puede instalar en la pantalla de inicio (manifest en /assets/qsg_pmo/campo.webmanifest).
 */
(function () {
	"use strict";

	const API = "/api/method/qsg_pmo.api.";
	const $app = document.getElementById("app");
	// El token CSRF viene en un atributo (la política CSP de /campo no permite scripts en línea)
	window.QSG_CSRF = $app.dataset.csrf;
	const state = {
		user: $app.dataset.user,
		name: $app.dataset.name,
		day: todayISO(),
		orders: [],
		order: null,
		tab: "trabajo",
		codes: null,
		loading: false,
	};

	// ------------------------------------------------------------------ íconos
	const I = {
		back: '<path d="M15 18l-6-6 6-6"/>',
		refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8"/><path d="M21 3v5h-5"/>',
		phone: '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/>',
		nav: '<path d="M3 11l19-9-9 19-2-8-8-2z"/>',
		camera: '<path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/>',
		check: '<path d="M20 6L9 17l-5-5"/>',
		x: '<path d="M18 6L6 18M6 6l12 12"/>',
		truck: '<path d="M1 3h15v13H1zM16 8h4l3 3v5h-7z"/><circle cx="5.5" cy="18.5" r="2.5"/><circle cx="18.5" cy="18.5" r="2.5"/>',
		pin: '<path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/>',
		flag: '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1zM4 22v-7"/>',
		logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/>',
	};
	const icon = (n) =>
		`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${I[n]}</svg>`;

	// ------------------------------------------------------------------ utilidades
	function todayISO(d = new Date()) {
		const z = (n) => String(n).padStart(2, "0");
		return `${d.getFullYear()}-${z(d.getMonth() + 1)}-${z(d.getDate())}`;
	}
	function shiftDay(iso, delta) {
		const d = new Date(iso + "T12:00:00");
		d.setDate(d.getDate() + delta);
		return todayISO(d);
	}
	function fmtDay(iso) {
		const d = new Date(iso + "T12:00:00");
		const s = d.toLocaleDateString("es-PR", { weekday: "long", day: "numeric", month: "short" });
		return (iso === (state.today || todayISO()) ? "Hoy, " : "") + s;
	}
	const hhmm = (t) => {
		if (!t) return "";
		const [h, m] = String(t).split(":");
		return `${h.padStart(2, "0")}:${(m || "00").padStart(2, "0")}`;
	};
	function fmtTime(dt) {
		if (!dt) return "";
		return String(dt).slice(11, 16);
	}
	function esc(v) {
		return String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
	}
	function serverError(r) {
		try {
			if (r._server_messages) {
				const m = JSON.parse(r._server_messages).map((x) => JSON.parse(x).message);
				return m.join(" ").replace(/<br>/g, "\n").replace(/<[^>]+>/g, "");
			}
		} catch (e) {
			/* sigue */
		}
		return r.exception || r.message || "Error del servidor";
	}

	async function call(method, args = {}, post = false) {
		let res;
		if (post) {
			res = await fetch(API + method, {
				method: "POST",
				headers: { "Content-Type": "application/json", Accept: "application/json", "X-Frappe-CSRF-Token": window.QSG_CSRF },
				body: JSON.stringify(args),
				credentials: "same-origin",
			});
		} else {
			const q = new URLSearchParams(Object.entries(args).filter(([, v]) => v != null));
			res = await fetch(API + method + "?" + q, { headers: { Accept: "application/json" }, credentials: "same-origin" });
		}
		if (res.status === 403 && method === "yo") location.href = "/login?redirect-to=/campo";
		const data = await res.json().catch(() => ({}));
		if (!res.ok) throw new Error(serverError(data));
		return data.message;
	}

	async function uploadPhoto(file, order) {
		const blob = await shrink(file);
		const fd = new FormData();
		fd.append("file", blob, "foto.jpg");
		fd.append("name", order);
		const res = await fetch(API + "subir_foto", {
			method: "POST",
			headers: { "X-Frappe-CSRF-Token": window.QSG_CSRF, Accept: "application/json" },
			body: fd,
			credentials: "same-origin",
		});
		const data = await res.json().catch(() => ({}));
		if (!res.ok) throw new Error(serverError(data));
		return data.message.file_url;
	}

	// Reduce la foto a 1600 px antes de subirla (ahorra datos en campo)
	function shrink(file, max = 1600) {
		return new Promise((resolve) => {
			const img = new Image();
			img.onload = () => {
				const k = Math.min(1, max / Math.max(img.width, img.height));
				const c = document.createElement("canvas");
				c.width = Math.round(img.width * k);
				c.height = Math.round(img.height * k);
				c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
				c.toBlob((b) => resolve(b || file), "image/jpeg", 0.82);
				URL.revokeObjectURL(img.src);
			};
			img.onerror = () => resolve(file);
			img.src = URL.createObjectURL(file);
		});
	}

	async function gps() {
		// En la app Android/iOS (Capacitor) se usa el GPS nativo: funciona también con http:// en la red local
		const nativeGeo = window.Capacitor?.isNativePlatform?.() && window.Capacitor.Plugins?.Geolocation;
		if (nativeGeo) {
			try {
				const p = await nativeGeo.getCurrentPosition({ enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 });
				return { lat: p.coords.latitude, lng: p.coords.longitude };
			} catch (e) {
				return {};
			}
		}
		return new Promise((resolve) => {
			if (!navigator.geolocation) return resolve({});
			navigator.geolocation.getCurrentPosition(
				(p) => resolve({ lat: p.coords.latitude, lng: p.coords.longitude }),
				() => resolve({}),
				{ enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 }
			);
		});
	}

	let toastTimer;
	function toast(msg, bad = false) {
		document.querySelector(".toast")?.remove();
		const el = document.createElement("div");
		el.className = "toast" + (bad ? " bad" : "");
		el.textContent = msg;
		document.body.appendChild(el);
		clearTimeout(toastTimer);
		toastTimer = setTimeout(() => el.remove(), bad ? 6000 : 2500);
	}

	// ------------------------------------------------------------------ estilos de estado
	const STATUS_CLASS = {
		Programada: "info",
		"En ruta": "warn",
		"En sitio": "warn",
		Completada: "ok",
		"No completada": "bad",
		Cancelada: "",
	};
	const SLA_CLASS = { "En tiempo": "ok", "En riesgo": "warn", Vencido: "bad", Cumplido: "ok", Incumplido: "bad" };
	const chip = (txt, cls) => (txt ? `<span class="chip ${cls || ""}">${esc(txt)}</span>` : "");
	const isClosed = (s) => ["Completada", "No completada", "Cancelada"].includes(s);

	// ------------------------------------------------------------------ vistas
	function shell(title, sub, left, body, actions) {
		$app.innerHTML = `
			${navigator.onLine ? "" : '<div class="offline">Sin conexión: los cambios no se guardarán hasta recuperar señal</div>'}
			<header class="top">
				${left}
				<h1>${esc(title)}<small>${esc(sub)}</small></h1>
				<button class="icon-btn" data-act="refresh" aria-label="Actualizar">${icon("refresh")}</button>
			</header>
			<main>${body}</main>
			${actions ? `<nav class="actionbar">${actions}</nav>` : ""}`;
	}

	function renderList() {
		const o = state.orders;
		const done = o.filter((x) => isClosed(x.status)).length;
		const pending = o.length - done;
		const cards = o
			.map(
				(x, i) => `
			<article class="card ${isClosed(x.status) ? "done" : ""}" data-open="${esc(x.name)}">
				<div class="seq">${x.route_sequence || i + 1}</div>
				<div class="body">
					<div class="row1"><span class="who">${esc(x.subscriber_name || x.name)}</span>
						<span class="when">${hhmm(x.window_start)}–${hhmm(x.window_end)}</span></div>
					<div class="where">${esc(x.address || "")}${x.municipality ? " · " + esc(x.municipality) : ""}</div>
					<div class="chips">
						${chip(x.status, STATUS_CLASS[x.status])}
						${chip(x.work_type, "")}
						${isClosed(x.status) ? "" : chip(x.sla_status && "SLA " + x.sla_status, SLA_CLASS[x.sla_status])}
						${x.is_rework ? chip("Retrabajo", "bad") : ""}
						${x.priority && x.priority !== "Normal" ? chip(x.priority, x.priority === "Urgente" ? "bad" : "warn") : ""}
					</div>
				</div>
			</article>`
			)
			.join("");
		const body = `
			<div class="daybar">
				<button data-day="-1" aria-label="Día anterior">‹</button>
				<div class="day">${esc(fmtDay(state.day))}</div>
				<button data-day="1" aria-label="Día siguiente">›</button>
			</div>
			<div class="summary">
				<div class="stat"><b>${o.length}</b><span>Órdenes</span></div>
				<div class="stat"><b>${pending}</b><span>Pendientes</span></div>
				<div class="stat"><b>${done}</b><span>Cerradas</span></div>
			</div>
			<div class="progress"><i style="width:${o.length ? Math.round((done * 100) / o.length) : 0}%"></i></div>
			${state.loading ? '<div class="spin"></div>' : cards || '<div class="empty">No tiene órdenes asignadas para este día.</div>'}`;
		shell(
			"Mi ruta",
			state.name,
			`<button class="icon-btn" data-act="logout" aria-label="Salir">${icon("logout")}</button>`,
			body
		);
	}

	function renderOrder() {
		const o = state.order;
		const closed = isClosed(o.status);
		const mapUrl =
			o.latitude && o.longitude
				? `https://www.google.com/maps/dir/?api=1&destination=${o.latitude},${o.longitude}`
				: `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent((o.address || "") + ", " + (o.municipality || "") + ", Puerto Rico")}`;
		const req = o.checklist.filter((r) => r.mandatory);
		const ok = req.filter((r) => r.compliant).length;

		const hero = `
			<section class="panel hero">
				<div class="chips" style="margin-bottom:8px">
					${chip(o.status, STATUS_CLASS[o.status])}
					${closed ? "" : chip(o.sla_status && "SLA " + o.sla_status, SLA_CLASS[o.sla_status])}
					${o.is_rework ? chip("Retrabajo", "bad") : ""}
					${o.arrival_out_of_range ? chip(`Llegada a ${o.arrival_distance_m} m`, "warn") : ""}
				</div>
				<div class="who">${esc(o.subscriber_name)}</div>
				<div class="meta">${esc(o.work_type)} · ${hhmm(o.window_start)}–${hhmm(o.window_end)}<br>${esc(o.address || "")}${o.municipality ? ", " + esc(o.municipality) : ""}</div>
				<div class="quick">
					<a class="btn" href="tel:${esc(o.phone || "")}">${icon("phone")} Llamar</a>
					<a class="btn" href="${mapUrl}" target="_blank" rel="noopener">${icon("nav")} Navegar</a>
				</div>
			</section>`;

		const tabs = `
			<div class="tabs" role="tablist">
				${[
					["trabajo", `Evidencia ${ok}/${req.length}`],
					["datos", "Datos"],
					["historial", "Historial"],
				]
					.map(([k, l]) => `<button role="tab" class="${state.tab === k ? "on" : ""}" data-tab="${k}">${l}</button>`)
					.join("")}
			</div>`;

		let content = "";
		if (state.tab === "trabajo") content = renderChecklist(o, closed);
		if (state.tab === "datos") content = renderData(o);
		if (state.tab === "historial") content = renderHistory(o);

		let actions = "";
		if (o.status === "Programada")
			actions = `<button class="btn primary" data-act="enruta">${icon("truck")} Salir hacia el sitio</button>`;
		else if (o.status === "En ruta")
			actions = `<button class="btn primary" data-act="ensitio">${icon("pin")} Llegué al sitio</button>`;
		else if (o.status === "En sitio")
			actions = `<button class="btn danger" data-act="nocomp">${icon("x")} No completada</button>
				<button class="btn ok" data-act="comp">${icon("flag")} Completar</button>`;

		shell(
			o.name,
			o.external_order_id ? "Orden cliente " + o.external_order_id : o.customer || "",
			`<button class="icon-btn" data-act="back" aria-label="Volver">${icon("back")}</button>`,
			hero + tabs + content,
			actions
		);
	}

	function renderChecklist(o, closed) {
		if (!o.checklist.length) return '<div class="panel empty">Este tipo de trabajo no tiene checklist.</div>';
		const editable = !closed && o.status === "En sitio";
		const rows = o.checklist
			.map((r) => {
				const filled = r.item_type === "Foto" ? r.photo : r.value;
				const markCls = r.compliant ? "ok" : filled ? "bad" : "";
				const markIcon = r.compliant ? icon("check") : filled ? icon("x") : "";
				let range = "";
				if (r.item_type === "Medición") {
					const lo = r.min_value || null,
						hi = r.max_value || null;
					range =
						lo != null && hi != null
							? `Rango ${lo} a ${hi} ${r.unit || ""}`
							: lo != null
								? `Mínimo ${lo} ${r.unit || ""}`
								: hi != null
									? `Máximo ${hi} ${r.unit || ""}`
									: r.unit || "";
				}
				let input = "";
				const dis = editable ? "" : "disabled";
				if (r.item_type === "Foto") {
					input = `<div class="photo">
						${r.photo ? `<img src="${esc(r.photo)}" alt="">` : ""}
						<label class="btn ${r.photo ? "" : "primary"}" ${editable ? "" : 'style="pointer-events:none;opacity:.5"'}>
							${icon("camera")} ${r.photo ? "Repetir" : "Tomar foto"}
							<input type="file" accept="image/*" capture="environment" data-photo="${esc(r.name)}" ${dis}>
						</label></div>`;
				} else if (r.item_type === "Sí/No") {
					input = `<div class="yn">
						<button data-yn="${esc(r.name)}" data-v="Sí" class="${r.value === "Sí" ? "on" : ""}" ${dis}>Sí</button>
						<button data-yn="${esc(r.name)}" data-v="No" class="no ${r.value === "No" ? "on" : ""}" ${dis}>No</button></div>`;
				} else if (r.item_type === "Medición") {
					input = `<input type="number" inputmode="decimal" step="any" data-val="${esc(r.name)}" value="${esc(r.value || "")}"
						class="${filled && !r.compliant ? "bad" : ""}" placeholder="${esc(r.unit || "valor")}" ${dis}>`;
				} else {
					input = `<input type="text" data-val="${esc(r.name)}" value="${esc(r.value || "")}" ${dis}>`;
				}
				return `<div class="check">
					<div class="mark ${markCls}">${markIcon}</div>
					<div class="txt">
						<div class="lbl">${esc(r.description)} ${r.mandatory ? "<em>*</em>" : ""}</div>
						${range ? `<div class="hint">${esc(range)}</div>` : '<div class="hint"></div>'}
						${input}
					</div></div>`;
			})
			.join("");
		const note = editable
			? ""
			: `<div class="hint" style="color:var(--muted);font-size:13px;margin-bottom:6px">${
					closed ? "Orden cerrada: solo lectura." : "Marque «Llegué al sitio» para registrar la evidencia."
				}</div>`;
		return `<section class="panel"><h2>Checklist</h2>${note}${rows}</section>`;
	}

	function renderData(o) {
		const n = o.network || {};
		const kv = (pairs) =>
			`<dl class="kv">${pairs
				.filter(([, v]) => v)
				.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`)
				.join("")}</dl>`;
		return `
			<section class="panel"><h2>Cliente</h2>${kv([
				["Cuenta", o.account_number],
				["Teléfono", o.phone],
				["Tecnología", o.technology],
				["Prioridad", o.priority],
				["Vence SLA", o.sla_due && String(o.sla_due).slice(0, 16)],
				["Cuadrilla", o.crew],
				["Contratista", o.contractor],
			])}</section>
			<section class="panel"><h2>Red</h2>${
				kv([
					["Nodo HFC", n.hfc_node],
					["Tap", n.tap],
					["OLT", n.olt],
					["Puerto PON", n.pon_port],
					["Splitter / CTO", n.splitter_cto],
					["Serial equipo", n.equipment_serial],
				]) || '<div class="hint">Sin datos de red.</div>'
			}</section>
			${
				o.materials.length
					? `<section class="panel"><h2>Materiales instalados</h2>${kv(o.materials.map((m) => [m.item, `${m.qty}${m.serial_no ? " · " + m.serial_no : ""}`]))}</section>`
					: ""
			}`;
	}

	function renderHistory(o) {
		const items = o.events
			.slice()
			.reverse()
			.map(
				(e) => `<li><time>${esc(String(e.time).slice(0, 16))} · ${esc(e.user || "")}</time>
				<b>${esc(e.type)}</b>: ${e.from ? esc(e.from) + " → " : ""}${esc(e.to || "")}${e.reason ? `<br><span class="hint">${esc(e.reason)}</span>` : ""}</li>`
			)
			.join("");
		return `<section class="panel"><h2>Historial</h2><ul class="tl">${items || "<li>Sin eventos.</li>"}</ul></section>`;
	}

	// ------------------------------------------------------------------ hoja de cierre
	async function openClose(result) {
		const o = state.order;
		if (!state.codes) state.codes = await call("codigos_cierre");
		const codes = state.codes.filter((c) => c.result === result);
		const completing = result === "Completada";
		const missing = o.checklist.filter((r) => r.mandatory && !r.compliant);
		const kit = o.kit.length ? o.kit : o.materials;
		const bg = document.createElement("div");
		bg.className = "sheet-bg";
		bg.innerHTML = `
			<form class="sheet" novalidate>
				<h3>${completing ? "Completar orden" : "No completada"}</h3>
				${
					completing && missing.length
						? `<div class="toast bad" style="position:static;margin-bottom:12px">Faltan ${missing.length} pasos obligatorios: ${esc(missing.map((m) => m.description).join(", "))}</div>`
						: ""
				}
				<div class="field"><label>Código de cierre</label><div class="codes">
					${codes
						.map(
							(c, i) => `<label class="code"><input type="radio" name="code" value="${esc(c.name)}" ${i === 0 && completing ? "checked" : ""}>
							<span><b>${esc(c.name)}</b><small>${esc(c.description)}${c.cause ? " · causa " + esc(c.cause) : ""}</small></span></label>`
						)
						.join("")}
				</div></div>
				${
					completing && kit.length
						? `<div class="field"><label>Materiales y seriales</label>${kit
								.map(
									(m, i) => `<div class="mat">
									<input value="${esc(m.item)}" data-mi="${i}" data-k="item" aria-label="Artículo" readonly>
									<input type="number" inputmode="decimal" value="${esc(m.qty)}" data-mi="${i}" data-k="qty" aria-label="Cantidad">
									<input class="serial" placeholder="Serial (si aplica)" value="${esc(m.serial_no || "")}" data-mi="${i}" data-k="serial_no"></div>`
								)
								.join("")}</div>`
						: ""
				}
				<div class="field"><label for="notes">Notas</label><textarea id="notes" rows="3" placeholder="${completing ? "Observaciones del trabajo" : "Qué pasó y qué se necesita"}"></textarea></div>
				${
					completing
						? `<div class="field"><label>Firma del cliente</label><canvas class="sig"></canvas>
						<div class="sig-actions"><span>Firme con el dedo</span><button type="button" data-clear>Borrar</button></div></div>`
						: ""
				}
				<div class="quick" style="margin-top:4px">
					<button type="button" class="btn" data-cancel>Cancelar</button>
					<button type="submit" class="btn ${completing ? "ok" : "primary"}">Cerrar orden</button>
				</div>
			</form>`;
		document.body.appendChild(bg);
		const form = bg.querySelector("form");
		const sig = completing ? signaturePad(bg.querySelector("canvas")) : null;
		bg.querySelector("[data-clear]")?.addEventListener("click", () => sig.clear());
		bg.querySelector("[data-cancel]").addEventListener("click", () => bg.remove());
		bg.addEventListener("click", (e) => e.target === bg && bg.remove());
		form.addEventListener("submit", async (e) => {
			e.preventDefault();
			const code = form.querySelector("input[name=code]:checked")?.value;
			if (!code) return toast("Seleccione un código de cierre", true);
			if (completing && sig.empty()) return toast("Falta la firma del cliente", true);
			const mats = kit.map((m, i) => {
				const get = (k) => form.querySelector(`[data-mi="${i}"][data-k="${k}"]`)?.value;
				return { item: get("item"), qty: get("qty"), serial_no: get("serial_no") };
			});
			const btn = form.querySelector("[type=submit]");
			btn.disabled = true;
			btn.textContent = "Guardando…";
			try {
				const pos = await gps();
				state.order = await call(
					"cerrar",
					{
						name: o.name,
						codigo: code,
						notas: form.querySelector("#notes").value,
						firma: sig ? sig.data() : null,
						materiales: completing ? mats : null,
						...pos,
					},
					true
				);
				bg.remove();
				toast(`Orden ${state.order.status.toLowerCase()}`);
				renderOrder();
			} catch (err) {
				btn.disabled = false;
				btn.textContent = "Cerrar orden";
				toast(err.message, true);
			}
		});
	}

	function signaturePad(canvas) {
		const ratio = window.devicePixelRatio || 1;
		canvas.width = canvas.offsetWidth * ratio;
		canvas.height = canvas.offsetHeight * ratio;
		const ctx = canvas.getContext("2d");
		ctx.scale(ratio, ratio);
		ctx.lineWidth = 2.2;
		ctx.lineCap = "round";
		ctx.strokeStyle = "#111";
		let drawing = false,
			dirty = false;
		const pt = (e) => {
			const r = canvas.getBoundingClientRect();
			return [e.clientX - r.left, e.clientY - r.top];
		};
		canvas.addEventListener("pointerdown", (e) => {
			drawing = true;
			canvas.setPointerCapture(e.pointerId);
			ctx.beginPath();
			ctx.moveTo(...pt(e));
		});
		canvas.addEventListener("pointermove", (e) => {
			if (!drawing) return;
			ctx.lineTo(...pt(e));
			ctx.stroke();
			dirty = true;
		});
		["pointerup", "pointercancel"].forEach((ev) => canvas.addEventListener(ev, () => (drawing = false)));
		return {
			empty: () => !dirty,
			clear: () => {
				ctx.clearRect(0, 0, canvas.width, canvas.height);
				dirty = false;
			},
			data: () => canvas.toDataURL("image/png"),
		};
	}

	// ------------------------------------------------------------------ acciones
	async function loadList() {
		state.loading = true;
		renderList();
		try {
			state.orders = await call("mis_ordenes", { fecha: state.day });
		} catch (e) {
			toast(e.message, true);
			state.orders = [];
		}
		state.loading = false;
		renderList();
	}

	async function openOrder(name, push = true) {
		try {
			state.order = await call("orden", { name });
			if (push) state.tab = "trabajo";
			if (push) history.pushState({ order: name }, "", "#" + encodeURIComponent(name));
			renderOrder();
			window.scrollTo(0, 0);
		} catch (e) {
			toast(e.message, true);
		}
	}

	async function setStatus(estado, btn) {
		btn.disabled = true;
		try {
			const pos = estado === "En sitio" ? await gps() : {};
			if (estado === "En sitio" && !pos.lat) toast("No se pudo leer el GPS; se registra la llegada sin ubicación.");
			state.order = await call("cambiar_estado", { name: state.order.name, estado, ...pos }, true);
			renderOrder();
			if (state.order.arrival_out_of_range)
				toast(`Atención: está a ${state.order.arrival_distance_m} m de la dirección registrada.`, true);
		} catch (e) {
			btn.disabled = false;
			toast(e.message, true);
		}
	}

	let saveTimer;
	async function saveRow(row) {
		try {
			state.order = await call("guardar_checklist", { name: state.order.name, filas: [row] }, true);
			renderOrder();
		} catch (e) {
			toast(e.message, true);
		}
	}

	$app.addEventListener("click", (e) => {
		const t = e.target.closest("[data-open],[data-act],[data-day],[data-tab],[data-yn]");
		if (!t) return;
		if (t.dataset.open) return openOrder(t.dataset.open);
		if (t.dataset.day) {
			state.day = shiftDay(state.day, +t.dataset.day);
			return loadList();
		}
		if (t.dataset.tab) {
			state.tab = t.dataset.tab;
			return renderOrder();
		}
		if (t.dataset.yn) return saveRow({ name: t.dataset.yn, value: t.dataset.v });
		const act = t.dataset.act;
		if (act === "back") return history.back();
		if (act === "refresh") return state.order ? openOrder(state.order.name, false) : loadList();
		if (act === "logout") return (location.href = "/?cmd=web_logout");
		if (act === "enruta") return setStatus("En ruta", t);
		if (act === "ensitio") return setStatus("En sitio", t);
		if (act === "comp") return openClose("Completada");
		if (act === "nocomp") return openClose("No completada");
	});

	$app.addEventListener("change", async (e) => {
		const t = e.target;
		if (t.dataset.val) {
			clearTimeout(saveTimer);
			return saveRow({ name: t.dataset.val, value: t.value });
		}
		if (t.dataset.photo && t.files && t.files[0]) {
			toast("Subiendo foto…");
			try {
				const url = await uploadPhoto(t.files[0], state.order.name);
				await saveRow({ name: t.dataset.photo, photo: url });
				toast("Foto guardada");
			} catch (err) {
				toast(err.message, true);
			}
		}
	});

	window.addEventListener("popstate", () => {
		if (!location.hash) {
			state.order = null;
			loadList();
		} else openOrder(decodeURIComponent(location.hash.slice(1)), false);
	});
	window.addEventListener("online", () => (state.order ? renderOrder() : renderList()));
	window.addEventListener("offline", () => (state.order ? renderOrder() : renderList()));

	// arranque
	if (location.hash) {
		history.replaceState(null, "", location.pathname);
	}
	// el día lo define el servidor (zona horaria de la operación), no el reloj del teléfono
	call("yo")
		.then((me) => {
			if (me && me.hoy) state.day = me.hoy;
			state.today = state.day;
		})
		.catch(() => {})
		.finally(loadList);
})();
