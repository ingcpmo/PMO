// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt
// Tablero de despacho: mapa en vivo, alertas del GPS, recomendaciones, órdenes sin asignar y asistente.
(() => {
	const $root = document.getElementById("despacho");
	const CSRF = $root.dataset.csrf;
	const DESPACHA = $root.dataset.despacha === "1";
	const GERENCIA = $root.dataset.gerencia === "1";
	// Pestañas con formularios: no se repintan solas mientras el usuario escribe
	const FIJAS = ["asistente", "equipo", "reglas"];
	const API = "/api/method/qsg_pmo.inteligencia.api.";
	const ABIERTAS = ["Recibida", "Asignada a contratista", "Programada", "En ruta", "Reprogramada"];
	const COLOR = {
		Recibida: "#8a96a3",
		"Asignada a contratista": "#6b7785",
		Programada: "#0b5cab",
		"En ruta": "#b26a00",
		"En sitio": "#7b3fbf",
		Completada: "#1e8e3e",
		"No completada": "#c62828",
		Reprogramada: "#e07b00",
		Cancelada: "#b0b8c1",
	};
	const SEV = { Alta: 0, Media: 1, Baja: 2 };
	const S = { datos: null, tab: "alertas", chat: [], interpretado: null, porAsignar: null, equipo: null, reglas: null, vistas: null, creado: null };

	const esc = (s) =>
		String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
	const hoyLocal = () => {
		const d = new Date();
		d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
		return d.toISOString().slice(0, 10);
	};
	const hora = (v) => (v ? String(v).slice(11, 16) : "");

	// ------------------------------------------------------------------ API
	function mensajeError(j) {
		try {
			if (j._server_messages) return JSON.parse(JSON.parse(j._server_messages)[0]).message;
		} catch (e) {
			/* mensaje sin formato */
		}
		return j.exception || j.exc_type || "";
	}
	async function leer(r) {
		let j = {};
		try {
			j = await r.json();
		} catch (e) {
			/* respuesta vacía */
		}
		if (!r.ok) throw new Error(mensajeError(j) || `Error ${r.status}`);
		return j.message;
	}
	const get = async (m, args = {}) =>
		leer(await fetch(`${API}${m}?${new URLSearchParams(args)}`, { credentials: "same-origin", headers: { Accept: "application/json" } }));
	const post = async (m, args = {}) =>
		leer(
			await fetch(API + m, {
				method: "POST",
				credentials: "same-origin",
				headers: { "X-Frappe-CSRF-Token": CSRF, Accept: "application/json", "Content-Type": "application/json" },
				body: JSON.stringify(args),
			}),
		);

	function sonar() {
		try {
			const C = window.AudioContext || window.webkitAudioContext;
			const c = new C();
			const o = c.createOscillator();
			const g = c.createGain();
			o.connect(g);
			g.connect(c.destination);
			o.frequency.value = 880;
			g.gain.setValueAtTime(0.15, c.currentTime);
			o.start();
			o.stop(c.currentTime + 0.35);
			setTimeout(() => c.close(), 700);
		} catch (e) {
			/* sin audio: queda el aviso en pantalla */
		}
	}

	function aviso(texto, malo = false) {
		const d = document.createElement("div");
		d.textContent = texto;
		d.style.cssText = `position:fixed;bottom:16px;left:50%;transform:translateX(-50%);z-index:3000;padding:10px 14px;border-radius:8px;color:#fff;background:${malo ? "#c62828" : "#1d2733"}`;
		document.body.appendChild(d);
		setTimeout(() => d.remove(), 4000);
	}

	// ------------------------------------------------------------------ modal
	const $modal = document.getElementById("modal");
	const abrir = (html) => {
		$modal.querySelector(".modal-cuerpo").innerHTML = html;
		$modal.hidden = false;
	};
	const cerrar = () => ($modal.hidden = true);
	$modal.addEventListener("click", (e) => {
		if (e.target === $modal || e.target.classList.contains("cerrar")) cerrar();
	});

	// ------------------------------------------------------------------ mapa
	const mapa = L.map("mapa").setView([18.22, -66.45], 9);
	const mosaicos = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
		maxZoom: 18,
		attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
	}).addTo(mapa);
	// Mapa de respaldo: si los mosaicos de OpenStreetMap no cargan (sin internet o una red que los
	// bloquea), se dibujan los 78 municipios de Puerto Rico que trae la app. Se quita si vuelven.
	let respaldo = null;
	let pidiendoRespaldo = false;
	let mosaicoCargado = false;
	mosaicos.on("tileload", () => {
		mosaicoCargado = true;
		if (respaldo) {
			mapa.removeLayer(respaldo);
			respaldo = null;
			mapa.getContainer().classList.remove("sin-mosaicos");
		}
	});
	mosaicos.on("tileerror", () => {
		if (respaldo || pidiendoRespaldo || mosaicoCargado) return;
		pidiendoRespaldo = true;
		fetch("/assets/qsg_pmo/geo/pr-municipios.json")
			.then((r) => r.json())
			.then((geo) => {
				if (mosaicoCargado) return;
				const css = getComputedStyle(document.documentElement);
				if (!mapa.getPane("respaldo")) mapa.createPane("respaldo").style.zIndex = 250;
				respaldo = L.geoJSON(geo, {
					pane: "respaldo",
					interactive: false,
					style: {
						color: css.getPropertyValue("--limite").trim(),
						weight: 0.8,
						fillColor: css.getPropertyValue("--tierra").trim(),
						fillOpacity: 1,
					},
				}).addTo(mapa);
				mapa.getContainer().classList.add("sin-mosaicos");
				mapa.attributionControl.addAttribution("Municipios: U.S. Census Bureau");
			})
			.catch(() => {})
			.finally(() => (pidiendoRespaldo = false));
	});
	const capaOrdenes = L.layerGroup().addTo(mapa);
	const capaCuadrillas = L.layerGroup().addTo(mapa);
	const capaIncidencias = L.layerGroup().addTo(mapa);
	let encuadrado = false;

	function pintarMapa() {
		const d = S.datos;
		capaOrdenes.clearLayers();
		capaCuadrillas.clearLayers();
		capaIncidencias.clearLayers();
		const puntos = [];
		for (const o of d.ordenes) {
			if (!o.latitude || !o.longitude) continue;
			puntos.push([o.latitude, o.longitude]);
			const m = L.circleMarker([o.latitude, o.longitude], {
				radius: o.segment === "Empresarial" ? 9 : 7,
				color: COLOR[o.status] || "#555",
				fillColor: COLOR[o.status] || "#555",
				fillOpacity: o.aproximada ? 0.25 : 0.75,
				dashArray: o.aproximada ? "3 3" : null,
				weight: 2,
			});
			const boton =
				DESPACHA && ABIERTAS.includes(o.status) ? `<br><button class="btn peq" data-mejor="${esc(o.name)}">Mejor cuadrilla</button>` : "";
			m.bindPopup(
				`<b>${esc(o.name)}</b> · ${esc(o.status)}<br>${esc(o.work_type || "")} · ${esc(o.segment || "")}<br>` +
					`${esc(o.municipality || "")} · ${esc(hora("2000-01-01 " + (o.window_start || "")))}–${esc(hora("2000-01-01 " + (o.window_end || "")))}<br>` +
					`Cuadrilla: ${esc(o.crew || "sin asignar")} · SLA: ${esc(o.sla_status || "-")}` +
					(o.aproximada ? "<br><i>Ubicación aproximada (centro del municipio)</i>" : "") +
					boton,
			);
			capaOrdenes.addLayer(m);
		}
		for (const c of d.cuadrillas) {
			// Sin GPS hoy: se muestra en su punto de salida, en gris
			const conGps = Boolean(c.lat && c.lng);
			const lat = conGps ? c.lat : c.base_lat;
			const lng = conGps ? c.lng : c.base_lng;
			if (!lat || !lng) continue;
			puntos.push([lat, lng]);
			const alta = c.alertas.some((a) => a.severidad === "Alta");
			const clase = alta ? " alerta" : conGps ? "" : " sin-gps";
			const icono = L.divIcon({ className: "", html: `<span class="etiqueta-cuadrilla${clase}">${esc(c.cuadrilla)}${conGps ? "" : " · sin GPS"}</span>` });
			const alertas = c.alertas.map((a) => `<li>${esc(a.mensaje)}</li>`).join("");
			L.marker([lat, lng], { icon: icono })
				.bindPopup(
					`<b>${esc(c.cuadrilla)}</b> · ${esc(c.contratista || "")}<br>${c.km_hoy} km hoy · ` +
						`${c.ordenes.completadas}/${c.ordenes.total} completadas<br>` +
						(c.siguiente_orden ? `Siguiente: ${esc(c.siguiente_orden)} (llega ${esc(hora(c.llegada_estimada))})<br>` : "") +
						(conGps ? `Última ubicación: ${esc(hora(c.ultimo_ping))}` : "Sin GPS hoy: se muestra en su punto de salida") +
						(alertas ? `<ul>${alertas}</ul>` : ""),
				)
				.addTo(capaCuadrillas);
		}
		for (const [zona, lista] of Object.entries(d.incidencias || {})) {
			const z = d.zonas[zona];
			if (!z || !z.lat) continue;
			const texto = lista.map((i) => `${i.tipo} (${i.impacto})`).join(", ");
			L.circle([z.lat, z.lng], { radius: 9000, color: "#c62828", fillOpacity: 0.08, weight: 1 })
				.bindTooltip(`${esc(zona)}: ${esc(texto)}`)
				.addTo(capaIncidencias);
		}
		if (!encuadrado && puntos.length) {
			mapa.fitBounds(puntos, { padding: [30, 30], maxZoom: 12 });
			encuadrado = true;
		}
	}
	mapa.on("popupopen", (e) => {
		const b = e.popup.getElement().querySelector("[data-mejor]");
		if (b) b.addEventListener("click", () => mejorCuadrilla(b.dataset.mejor));
	});

	// ------------------------------------------------------------------ KPIs
	function pintarKpis() {
		const o = S.datos.ordenes;
		const cuenta = (f) => o.filter(f).length;
		const alertas = S.datos.cuadrillas.reduce((n, c) => n + c.alertas.length, 0);
		const k = [
			["Órdenes del día", o.length, ""],
			["Completadas", cuenta((x) => x.status === "Completada"), "bueno"],
			["En campo", cuenta((x) => ["En ruta", "En sitio"].includes(x.status)), ""],
			["Sin asignar", DESPACHA ? (S.datos.por_asignar || []).length : cuenta((x) => !x.crew && ABIERTAS.includes(x.status)), "alerta"],
			["SLA en riesgo", cuenta((x) => x.sla_status === "En riesgo"), "alerta"],
			["SLA vencido", cuenta((x) => x.sla_status === "Vencido"), "malo"],
			["Alertas GPS", alertas, alertas ? "alerta" : ""],
			["Recomendaciones", S.datos.recomendaciones.length, ""],
		];
		document.getElementById("kpis").innerHTML = k
			.map(([l, v, cls]) => `<div class="kpi ${v ? cls : ""}"><div class="v">${v}</div><div class="l">${esc(l)}</div></div>`)
			.join("");
	}

	// ------------------------------------------------------------------ pestañas
	const $contenido = document.getElementById("contenido");
	document.querySelectorAll(".pestanas button").forEach((b) =>
		b.addEventListener("click", () => {
			S.tab = b.dataset.tab;
			document.querySelectorAll(".pestanas button").forEach((x) => x.classList.toggle("on", x === b));
			pintarPanel();
			if (S.tab === "sinasignar") cargarPorAsignar();
			if (S.tab === "equipo") cargarEquipo();
			if (S.tab === "reglas") cargarReglas();
		}),
	);

	function tarjeta(sev, titulo, cuerpo, acciones = "") {
		return `<div class="tarjeta ${esc((sev || "").toLowerCase())}"><h4>${titulo}</h4>${cuerpo}${acciones ? `<div class="acciones">${acciones}</div>` : ""}</div>`;
	}

	function pintarPanel() {
		const d = S.datos;
		if (!d) return;
		let html = "";
		if (S.tab === "alertas") {
			const lista = d.cuadrillas
				.flatMap((c) => c.alertas.map((a) => ({ ...a, c })))
				.sort((a, b) => (SEV[a.severidad] ?? 3) - (SEV[b.severidad] ?? 3));
			html = lista
				.map((a) =>
					tarjeta(
						a.severidad,
						`${esc(a.c.cuadrilla)} · ${esc(a.tipo)}`,
						`<p>${esc(a.mensaje)}</p>`,
						(a.c.lat ? `<button class="btn peq" data-ver="${a.c.lat},${a.c.lng}">Ver en mapa</button>` : "") +
							(DESPACHA && a.orden ? `<button class="btn peq" data-mejor="${esc(a.orden)}">Mejor cuadrilla</button>` : ""),
					),
				)
				.join("");
			const sinConfirmar = (d.sin_confirmar || [])
				.map((x) =>
					tarjeta(
						"media",
						`${esc(x.cuadrilla)} · Sin confirmar`,
						`<p>${esc(x.orden)} se asignó hace ${x.minutos} min y el contratista no ha tocado «Recibida».</p>`,
						DESPACHA ? `<button class="btn peq" data-mejor="${esc(x.orden)}">Mejor cuadrilla</button>` : "",
					),
				)
				.join("");
			html = sinConfirmar + html || '<div class="vacio">Sin alertas. Las cuadrillas van según lo planificado.</div>';
		} else if (S.tab === "recomendaciones") {
			html = d.recomendaciones
				.map((r) =>
					tarjeta(
						r.priority,
						`${esc(r.rec_type)} · ${esc(r.title)}`,
						`<p class="suave">${esc(hora(r.rec_time))} ${r.zone ? "· " + esc(r.zone) : ""}</p><pre class="texto">${esc(r.detail || "")}</pre>` +
							(r.action ? `<p><b>Sugerencia:</b> ${esc(r.action)}</p>` : ""),
						DESPACHA
							? (r.order ? `<button class="btn peq" data-mejor="${esc(r.order)}" data-rec="${esc(r.name)}">Mejor cuadrilla</button>` : "") +
									`<button class="btn peq" data-atender="${esc(r.name)}" data-estado="Resuelta">Resuelta</button>` +
									`<button class="btn peq" data-atender="${esc(r.name)}" data-estado="Descartada">Descartar</button>`
							: "",
					),
				)
				.join("");
			html = html || '<div class="vacio">No hay recomendaciones nuevas.</div>';
		} else if (S.tab === "cuadrillas") {
			html = d.cuadrillas
				.map((c) => {
					const pct = c.ordenes.total ? Math.round((c.ordenes.completadas / c.ordenes.total) * 100) : 0;
					const min = c.minutos_sin_gps;
					const gps = min == null ? "sin GPS hoy" : `GPS hace ${min} min`;
					return tarjeta(
						c.alertas.length ? "media" : "",
						`${esc(c.cuadrilla)} <span class="suave">${esc(c.zona || "")} · ${esc(c.contratista || "")}</span>`,
						`<p>${c.ordenes.completadas} de ${c.ordenes.total} completadas · ${c.ordenes.pendientes} pendientes · ${c.km_hoy} km · ${esc(gps)}</p>` +
							(c.siguiente_orden ? `<p class="suave">Siguiente: ${esc(c.siguiente_orden)}, llega ${esc(hora(c.llegada_estimada))}</p>` : "") +
							`<div class="barra-progreso"><span style="width:${pct}%"></span></div>`,
						c.lat ? `<button class="btn peq" data-ver="${c.lat},${c.lng}">Ver en mapa</button>` : "",
					);
				})
				.join("");
		} else if (S.tab === "sinasignar") {
			html = DESPACHA ? pintarPorAsignar() : '<div class="vacio">Las asignaciones las decide despacho.</div>';
		} else if (S.tab === "equipo") {
			html = pintarEquipo();
		} else if (S.tab === "reglas") {
			html = pintarReglas();
		} else if (S.tab === "asistente") {
			html = pintarAsistente();
		}
		$contenido.innerHTML = html;
	}

	$contenido.addEventListener("click", async (e) => {
		const b = e.target.closest("button");
		if (!b) return;
		if (b.dataset.ver) {
			const [lat, lng] = b.dataset.ver.split(",").map(Number);
			mapa.flyTo([lat, lng], 13);
		} else if (b.dataset.mejor) {
			mejorCuadrilla(b.dataset.mejor, b.dataset.rec);
		} else if (b.dataset.asignarA) {
			asignar(b.dataset.orden, b.dataset.asignarA);
		} else if (b.dataset.contratista) {
			perfilContratista(b.dataset.contratista);
		} else if (b.id === "guardar-usuario") {
			guardarUsuario();
		} else if (b.dataset.clave) {
			accionUsuario("nueva_clave", { correo: b.dataset.clave });
		} else if (b.dataset.estado && b.dataset.usuario) {
			accionUsuario("estado_usuario", { correo: b.dataset.usuario, activo: b.dataset.estado });
		} else if (b.id === "guardar-reglas") {
			guardarReglas();
		} else if (b.id === "recalcular") {
			recalcular();
		} else if (b.dataset.atender) {
			try {
				await post("atender", { recomendacion: b.dataset.atender, estado: b.dataset.estado });
				aviso(`Recomendación ${b.dataset.estado.toLowerCase()}`);
				cargar();
			} catch (err) {
				aviso(err.message, true);
			}
		} else if (b.id === "enviar-pregunta") {
			preguntar();
		} else if (b.id === "interpretar") {
			interpretar();
		} else if (b.id === "crear-orden") {
			crearOrden();
		}
	});

	// ------------------------------------------------------------------ mejor cuadrilla
	async function mejorCuadrilla(orden, recomendacion) {
		abrir(`<p>Buscando la mejor cuadrilla para ${esc(orden)}…</p>`);
		try {
			const r = await get("mejor_cuadrilla", { orden, ignorar_contratista: 1 });
			if (!r.opciones.length) {
				abrir(`<h3>${esc(orden)}</h3><p>Ninguna cuadrilla con la habilidad puede llegar dentro de la ventana y del turno.</p>`);
				return;
			}
			const filas = r.opciones
				.map(
					(o, i) => `<div class="tarjeta"><h4>${i + 1}. ${esc(o.cuadrilla)} ${categoria(o)} <span class="suave">${esc(o.contratista || "")}</span></h4>
					<p>${o.km} km · llegada ${esc(hora(o.llegada))} · termina ${esc(hora(o.termina))}</p>
					<p class="suave">${o.razones.map(esc).join(" · ")}</p>
					<div class="acciones"><button class="btn peq primario" data-asignar="${esc(o.cuadrilla)}">Asignar</button></div></div>`,
				)
				.join("");
			abrir(
				`<h3>Mejor cuadrilla para ${esc(orden)}</h3>` +
					(r.ubicacion_aproximada ? '<p class="suave">La orden no tiene GPS: se usó el centro del municipio.</p>' : "") +
					filas,
			);
			$modal.querySelectorAll("[data-asignar]").forEach((b) => b.addEventListener("click", () => asignar(orden, b.dataset.asignar, recomendacion)));
		} catch (err) {
			abrir(`<p>${esc(err.message)}</p>`);
		}
	}

	// ------------------------------------------------------------------ por asignar (recomendación por reglas)
	const categoria = (o) =>
		o.categoria ? `<span class="cat cat-${esc(o.categoria)}" title="Categoría y puntaje del contratista">${esc(o.categoria)} · ${Math.round(o.puntaje || 0)}</span>` : '<span class="cat" title="Aún sin cierres para calificar">sin calificar</span>';
	const hhmm = (v) => {
		const [h, m] = String(v || "").split(":");
		return h ? `${h.padStart(2, "0")}:${m || "00"}` : "";
	};
	const fechaCorta = (f) => (f ? String(f).slice(5).split("-").reverse().join("/") : "sin fecha");

	async function asignar(orden, cuadrilla, recomendacion) {
		const motivo = window.prompt(`Asignar ${orden} a ${cuadrilla}. Motivo:`, "Recomendación por reglas: cercanía y calificación");
		if (!motivo) return;
		try {
			await post("reasignar", { orden, cuadrilla, motivo, recomendacion: recomendacion || null });
			cerrar();
			aviso(`${orden} asignada a ${cuadrilla}. El contratista recibe el aviso en su app.`);
			await cargar();
			if (S.tab === "sinasignar") cargarPorAsignar();
		} catch (err) {
			aviso(err.message, true);
		}
	}

	async function cargarPorAsignar() {
		if (!DESPACHA) return;
		try {
			S.porAsignar = await get("por_asignar");
		} catch (err) {
			S.porAsignar = { ordenes: [], total: 0, error: err.message };
		}
		if (S.tab === "sinasignar") pintarPanel();
	}

	function pintarPorAsignar() {
		const r = S.porAsignar;
		if (!r) return '<div class="vacio">Calculando las mejores opciones…</div>';
		if (r.error) return `<div class="vacio">${esc(r.error)}</div>`;
		if (!r.ordenes.length) return '<div class="vacio">No hay peticiones por asignar.</div>';
		const tarjetas = r.ordenes.map((o) => {
			const opciones = (o.opciones || [])
				.map(
					(x, i) => `<div class="opcion"><div><b>${i + 1}. ${esc(x.cuadrilla)}</b> ${categoria(x)}
						<button class="vinculo" data-contratista="${esc(x.contratista || "")}">${esc(x.contratista || "")}</button><br>
						<span class="suave">${x.km} km · ${Math.round(x.minutos_viaje)} min de viaje · llega ${esc(hora(x.llegada))} · ${x.cupos} cupos · ${esc((x.ubicacion || "").toLowerCase())}</span></div>
						<button class="btn peq primario" data-asignar-a="${esc(x.cuadrilla)}" data-orden="${esc(o.name)}">Asignar</button></div>`,
				)
				.join("");
			return tarjeta(
				o.priority === "Crítica" || o.priority === "Alta" ? "alta" : "",
				`${esc(o.name)} · ${esc(o.priority || "")} <span class="suave">${esc(o.work_type || "")}</span>`,
				`<p>${esc(o.subscriber_name || "")} · ${esc(o.municipality || "")} · ${esc(fechaCorta(o.appointment_date))} ${esc(hhmm(o.window_start))}–${esc(hhmm(o.window_end))}</p>` +
					(o.aproximada ? '<p class="suave">Sin GPS de la dirección: se usó el centro del municipio.</p>' : "") +
					(opciones || `<p class="suave">${esc(o.motivo || "Sin opciones.")}</p>`),
				`<button class="btn peq" data-mejor="${esc(o.name)}">Ver el detalle</button>`,
			);
		});
		const resto = r.total > r.ordenes.length ? `<p class="suave">Se muestran ${r.ordenes.length} de ${r.total}, las más urgentes primero.</p>` : "";
		return `<p class="suave">Ordenadas por cercanía, cupo y calificación del contratista. Usted decide.</p>${tarjetas.join("")}${resto}`;
	}

	async function perfilContratista(nombre) {
		if (!nombre) return;
		abrir(`<p>Cargando ${esc(nombre)}…</p>`);
		try {
			const p = await get("perfil_contratista", { contratista: nombre });
			const e = p.evaluacion;
			const fila = (l, v) => `<tr><td>${esc(l)}</td><td>${v}</td></tr>`;
			const pct = (v) => `${Math.round(v || 0)} %`;
			abrir(
				`<h3>${esc(p.contratista)} ${categoria(p)}</h3>
				<p class="suave">${esc(p.estado || "")}${p.contacto ? " · " + esc(p.contacto) : ""}${p.telefono ? " · " + esc(p.telefono) : ""}</p>` +
					(e
						? `<table class="datos">${fila("Período", `${esc(e.period_start)} a ${esc(e.period_end)}`)}${fila("Órdenes cerradas", e.orders_total)}
						${fila("Llega dentro de la ventana", pct(e.window_compliance))}${fila("Primera visita exitosa", pct(e.first_time_right))}
						${fila("Cumple el SLA", pct(e.sla_compliance))}${fila("Evidencia completa", pct(e.evidence_compliance))}
						${fila("Encuesta del cliente", e.avg_rating ? `${e.avg_rating} de 5` : "sin encuestas")}${fila("Retrabajos", `${e.rework_count} (${pct(e.rework_rate)})`)}</table>`
						: '<p class="suave">Todavía no tiene órdenes cerradas para calificar.</p>') +
					`<h4>Cuadrillas</h4><p>${p.cuadrillas.map((c) => `${esc(c.name)} · ${esc(c.base_zone || "sin zona")}${c.active ? "" : " · inactiva"}`).join("<br>") || "Ninguna"}</p>`,
			);
		} catch (err) {
			abrir(`<p>${esc(err.message)}</p>`);
		}
	}

	// ------------------------------------------------------------------ equipo (perfiles de usuario)
	async function cargarEquipo() {
		try {
			S.equipo = await get("equipo");
		} catch (err) {
			S.equipo = { error: err.message };
		}
		if (S.tab === "equipo") pintarPanel();
	}

	function pintarEquipo() {
		const q = S.equipo;
		if (!q) return '<div class="vacio">Cargando el equipo…</div>';
		if (q.error) return `<div class="vacio">${esc(q.error)}</div>`;
		const creado = S.creado
			? `<div class="tarjeta baja"><h4>${S.creado.nuevo ? "Usuario creado" : "Contraseña nueva"}</h4>
				<p>Usuario: <b>${esc(S.creado.usuario)}</b><br>Contraseña: <b class="clave">${esc(S.creado.contrasena)}</b></p>
				<p class="suave">Anótela ahora: no se vuelve a mostrar.${S.creado.cuadrilla ? " Cuadrilla " + esc(S.creado.cuadrilla) + "." : ""}</p></div>`
			: "";
		const usuarios = q.usuarios
			.map((u) =>
				tarjeta(
					u.activo ? "" : "baja",
					`${esc(u.nombre || u.usuario)} <span class="chip">${esc(u.perfil || "")}</span>${u.demo ? ' <span class="chip">demostración</span>' : ""}${u.activo ? "" : ' <span class="chip">desactivado</span>'}`,
					`<p class="suave">${esc(u.usuario)}${u.cuadrilla ? ` · ${esc(u.cuadrilla)} · ${esc(u.contratista || "")} · ${esc(u.zona || "")}` : ""}${u.gps_hace_min != null ? ` · GPS hace ${u.gps_hace_min} min` : ""}</p>`,
					u.yo
						? '<span class="suave">Usted</span>'
						: `<button class="btn peq" data-clave="${esc(u.usuario)}">Nueva contraseña</button>
							<button class="btn peq" data-usuario="${esc(u.usuario)}" data-estado="${u.activo ? 0 : 1}">${u.activo ? "Desactivar" : "Activar"}</button>`,
				),
			)
			.join("");
		const municipios = q.municipios.map((m) => `<option value="${esc(m.municipio)}">${esc(m.municipio)} (${esc(m.zona)})</option>`).join("");
		const habilidades = q.habilidades.map((h) => `<label class="casilla"><input type="checkbox" name="habilidad" value="${esc(h)}"> ${esc(h)}</label>`).join("");
		const contratistas = q.contratistas.map((c) => `<option value="${esc(c.name)}">`).join("");
		return `${creado}
			<details class="tarjeta" ${S.creado ? "" : "open"}><summary><b>Agregar un usuario</b></summary>
			<div class="formulario">
				<label>Perfil<select id="u-perfil" class="campo">
					<option value="Contratista">Contratista: recibe órdenes y reporta su trabajo</option>
					<option value="Administrador">Administrador: ve todo, asigna y configura</option>
					<option value="Despachador">Despachador: ve todo y asigna</option>
					<option value="Supervisor">Supervisor: solo las cuadrillas de su empresa</option>
				</select></label>
				<label>Correo<input id="u-correo" class="campo" type="email" autocomplete="off" placeholder="correo@ejemplo.com"></label>
				<label>Nombre<input id="u-nombre" class="campo" maxlength="80"></label>
				<label>Teléfono<input id="u-telefono" class="campo" type="tel" maxlength="30"></label>
				<div id="u-campo">
					<label>Empresa contratista<input id="u-contratista" class="campo" list="lista-contratistas" placeholder="Si lo deja vacío, se usa el nombre"></label>
					<datalist id="lista-contratistas">${contratistas}</datalist>
					<div id="u-cuadrilla">
						<label>Municipio de salida<select id="u-municipio" class="campo"><option value="">Elija…</option>${municipios}</select></label>
						<p class="suave">Qué trabajos puede hacer:</p>
						<div class="casillas">${habilidades}</div>
						<label>Órdenes por día<input id="u-cupo" class="campo" type="number" min="1" max="20" value="5"></label>
						<div class="turno"><label>Turno desde<input id="u-desde" class="campo" type="time" value="07:00"></label>
						<label>hasta<input id="u-hasta" class="campo" type="time" value="17:00"></label></div>
						<p class="suave">Fuera de su turno no se le recomiendan órdenes.</p>
					</div>
				</div>
				<button class="btn primario" id="guardar-usuario">Guardar</button>
			</div></details>
			<h4>Usuarios (${q.usuarios.length})</h4>${usuarios}`;
	}

	$contenido.addEventListener("change", (e) => {
		if (e.target.id !== "u-perfil") return;
		const p = e.target.value;
		document.getElementById("u-campo").hidden = !["Contratista", "Supervisor"].includes(p);
		document.getElementById("u-cuadrilla").hidden = p !== "Contratista";
	});

	async function guardarUsuario() {
		const v = (id) => document.getElementById(id).value.trim();
		const args = {
			perfil: v("u-perfil"),
			correo: v("u-correo"),
			nombre: v("u-nombre"),
			telefono: v("u-telefono"),
			contratista: v("u-contratista"),
			municipio: v("u-municipio"),
			habilidades: [...document.querySelectorAll('input[name="habilidad"]:checked')].map((x) => x.value),
			cupo: v("u-cupo"),
			turno_desde: v("u-desde"),
			turno_hasta: v("u-hasta"),
		};
		try {
			const r = await post("guardar_usuario", args);
			S.creado = r.contrasena ? r : null;
			aviso(r.nuevo ? `Usuario ${r.usuario} creado` : `Usuario ${r.usuario} actualizado`);
			cargarEquipo();
		} catch (err) {
			aviso(err.message, true);
		}
	}

	async function accionUsuario(metodo, args) {
		try {
			const r = await post(metodo, args);
			S.creado = r.contrasena ? { ...r, nuevo: false } : null;
			aviso(r.contrasena ? `Contraseña nueva para ${r.usuario}` : `${r.usuario} ${r.activo ? "activado" : "desactivado"}`);
			cargarEquipo();
		} catch (err) {
			aviso(err.message, true);
		}
	}

	// ------------------------------------------------------------------ reglas
	async function cargarReglas() {
		try {
			S.reglas = await get("reglas");
		} catch (err) {
			S.reglas = { error: err.message };
		}
		if (S.tab === "reglas") pintarPanel();
	}

	function pintarReglas() {
		const r = S.reglas;
		if (!r) return '<div class="vacio">Cargando las reglas…</div>';
		if (r.error) return `<div class="vacio">${esc(r.error)}</div>`;
		const grupo = (titulo, intro, lista) =>
			`<div class="tarjeta"><h4>${esc(titulo)}</h4><p class="suave">${intro}</p>` +
			lista
				.map(
					(x) => `<label class="regla" title="${esc(x.ayuda)}"><span>${esc(x.etiqueta)}</span>
					<span><input class="campo num" type="number" step="any" min="${x.min}" max="${x.max}" data-regla="${esc(x.campo)}" value="${x.valor}" ${r.editable ? "" : "disabled"}> <span class="suave">${esc(x.unidad)}</span></span></label>`,
				)
				.join("") +
			"</div>";
		return (
			'<p class="suave">Todo se calcula por reglas en el servidor, sin modelo de lenguaje. El sistema propone y usted asigna.</p>' +
			grupo(
				"Asignación: a quién se recomienda",
				"Se descartan las cuadrillas sin la habilidad, sin cupo, fuera de turno o que no llegan en la ventana. Las demás se ordenan por minutos de viaje desde su último GPS, con estos ajustes:",
				r.asignacion,
			) +
			grupo(
				"Calificación del contratista",
				`Peso de cada factor en el puntaje, con los cierres de los últimos ${r.dias_calificacion} días. Categoría A desde ${r.categorias.A} puntos, B desde ${r.categorias.B}, C por debajo. Se recalcula cada hora.`,
				r.calificacion,
			) +
			grupo("Tiempos", "Cuándo avisa el tablero.", r.tiempos) +
			(r.editable
				? '<p><button class="btn primario" id="guardar-reglas">Guardar las reglas</button> <button class="btn" id="recalcular">Recalcular calificaciones ahora</button></p>'
				: '<p class="suave">Solo el administrador cambia las reglas.</p>')
		);
	}

	async function guardarReglas() {
		const valores = {};
		document.querySelectorAll("[data-regla]").forEach((i) => (valores[i.dataset.regla] = i.value));
		try {
			S.reglas = await post("guardar_reglas", { valores });
			aviso("Reglas guardadas");
			pintarPanel();
		} catch (err) {
			aviso(err.message, true);
		}
	}

	async function recalcular() {
		try {
			const r = await post("recalcular_calificaciones");
			aviso(r.length ? r.map((x) => `${x.contratista}: ${x.categoria || "-"} (${Math.round(x.puntaje || 0)})`).join(" · ") : "Ningún contratista tiene cierres en el período");
		} catch (err) {
			aviso(err.message, true);
		}
	}

	// ------------------------------------------------------------------ asistente y órdenes por texto
	function pintarAsistente() {
		const chat = S.chat.map((m) => `<div class="burbuja ${m.yo ? "yo" : ""}"><pre class="texto">${esc(m.texto)}</pre></div>`).join("");
		const interp = S.interpretado ? tablaInterpretacion(S.interpretado) : "";
		return `<div class="chat">${chat || '<p class="suave">Pregunte por la operación: «¿qué cuadrillas van atrasadas?», «¿qué zona rinde peor este mes?», «¿qué falta recoger en bodega para mañana?»</p>'}</div>
			<p><input id="pregunta" class="campo" placeholder="Escriba su pregunta" maxlength="2000"></p>
			<p><button class="btn primario" id="enviar-pregunta">Preguntar</button></p>
			<hr>
			<h4>Nueva orden desde un correo o mensaje</h4>
			<textarea id="texto-orden" placeholder="Pegue aquí el correo, ticket o mensaje del cliente"></textarea>
			<p><button class="btn" id="interpretar">Interpretar</button></p>
			${interp}`;
	}

	function tablaInterpretacion(d) {
		const etiquetas = {
			work_type: "Tipo de trabajo",
			priority: "Prioridad",
			municipality: "Municipio",
			zone: "Zona",
			subscriber_name: "Cliente",
			phone: "Teléfono",
			account_number: "Cuenta",
			address: "Dirección",
			appointment_date: "Fecha",
			window_start: "Desde",
			window_end: "Hasta",
			external_order_id: "Número del cliente",
		};
		const filas = Object.entries(etiquetas)
			.map(([k, l]) => `<tr><td>${esc(l)}</td><td>${esc(d[k] || "—")}</td></tr>`)
			.join("");
		const faltan = (d.faltantes || []).length ? `<p class="suave">Falta: ${esc(d.faltantes.join(", "))}</p>` : "";
		const nota = d.nota_isla ? `<p class="suave">${esc(d.nota_isla)}</p>` : "";
		return `<table class="datos">${filas}</table>${faltan}${nota}<p class="suave">Interpretado por: ${esc(d.fuente)}${d.aviso_ia ? " · " + esc(d.aviso_ia) : ""}</p>
			<p><button class="btn primario" id="crear-orden" ${d.work_type ? "" : "disabled"}>Crear la orden</button></p>`;
	}

	async function preguntar() {
		const $p = document.getElementById("pregunta");
		const texto = ($p.value || "").trim();
		if (!texto) return;
		S.chat.push({ yo: true, texto }, { yo: false, texto: "Consultando…" });
		pintarPanel();
		try {
			const r = await post("preguntar", { pregunta: texto });
			S.chat[S.chat.length - 1].texto = r.respuesta;
		} catch (err) {
			S.chat[S.chat.length - 1].texto = err.message;
		}
		pintarPanel();
	}

	async function interpretar() {
		const texto = (document.getElementById("texto-orden").value || "").trim();
		if (!texto) return;
		S.textoOrden = texto;
		try {
			S.interpretado = await post("interpretar_solicitud", { texto });
		} catch (err) {
			aviso(err.message, true);
		}
		pintarPanel();
		document.getElementById("texto-orden").value = texto;
	}

	async function crearOrden() {
		try {
			const r = await post("crear_orden_desde_texto", { texto: S.textoOrden });
			aviso(`Orden ${r.name} ${r.created ? "creada" : "actualizada"} (${r.status})`);
			S.interpretado = null;
			cargar();
		} catch (err) {
			aviso(err.message, true);
		}
	}

	// ------------------------------------------------------------------ resumen del día
	document.getElementById("btn-briefing").addEventListener("click", async () => {
		abrir("<p>Preparando el resumen…</p>");
		try {
			const r = await get("briefing", { fecha: document.getElementById("fecha").value });
			abrir(`<h3>Resumen del ${esc(r.datos.fecha)}</h3><pre class="texto">${esc(r.texto)}</pre><p class="suave">Generado con: ${esc(r.proveedor === "Ninguno" ? "reglas" : r.proveedor)}</p>`);
		} catch (err) {
			abrir(`<p>${esc(err.message)}</p>`);
		}
	});
	if (!DESPACHA) document.getElementById("btn-briefing").hidden = true;

	// ------------------------------------------------------------------ jornada simulada (solo demostración)
	const $sim = document.getElementById("sim");
	const $simReiniciar = document.getElementById("sim-reiniciar");
	let simulando = null;
	function detenerSimulacion(mensaje, malo = false) {
		clearInterval(simulando);
		simulando = null;
		$sim.textContent = "▶ Simular jornada";
		if (mensaje) aviso(mensaje, malo);
	}
	async function pasoSimulado() {
		try {
			const r = await post("demo_paso");
			if (r.eventos.length) aviso(r.eventos.slice(0, 2).join(" · "));
			await cargar();
			if (!r.quedan) detenerSimulacion("Jornada terminada: todas las órdenes del día se cerraron.");
		} catch (err) {
			detenerSimulacion(err.message, true);
		}
	}
	$sim.addEventListener("click", () => {
		if (simulando) return detenerSimulacion();
		$sim.textContent = "❚❚ Pausar simulación";
		pasoSimulado();
		simulando = setInterval(pasoSimulado, 6000);
	});
	$simReiniciar.addEventListener("click", async () => {
		detenerSimulacion();
		try {
			const r = await post("demo_reiniciar");
			aviso(`Jornada reiniciada: ${r.ordenes} órdenes para hoy`);
			encuadrado = false;
			await cargar();
		} catch (err) {
			aviso(err.message, true);
		}
	});

	// ------------------------------------------------------------------ carga
	async function cargar() {
		try {
			S.datos = await get("tablero", { fecha: document.getElementById("fecha").value });
			document.getElementById("proveedor").textContent = `IA: ${S.datos.ia}`;
			$sim.hidden = $simReiniciar.hidden = !(S.datos.demo && DESPACHA);
			document.getElementById("perfil").textContent = S.datos.perfil || "";
			avisarNuevas(S.datos.por_asignar || []);
			pintarKpis();
			pintarMapa();
			if (!FIJAS.includes(S.tab)) pintarPanel();
		} catch (err) {
			aviso(err.message, true);
		}
	}
	// Petición nueva sin cuadrilla: aviso con sonido y contador en la pestaña
	function avisarNuevas(nombres) {
		const nuevas = S.vistas ? nombres.filter((n) => !S.vistas.has(n)) : [];
		S.vistas = new Set(nombres);
		const $tab = document.querySelector('[data-tab="sinasignar"]');
		$tab.textContent = nombres.length ? `Sin asignar (${nombres.length})` : "Sin asignar";
		if (!nuevas.length) return;
		sonar();
		aviso(nuevas.length === 1 ? `Petición nueva por asignar: ${nuevas[0]}` : `${nuevas.length} peticiones nuevas por asignar`);
		if (S.tab === "sinasignar") cargarPorAsignar();
	}
	document.querySelector('[data-tab="equipo"]').hidden = !GERENCIA;
	document.querySelector('[data-tab="reglas"]').hidden = !DESPACHA;
	document.getElementById("salir").addEventListener("click", async (e) => {
		e.preventDefault();
		try {
			await fetch("/api/method/logout", { credentials: "same-origin" });
		} catch (err) {
			/* sin conexión: igual se va al inicio de sesión */
		}
		location.href = "/login?redirect-to=" + encodeURIComponent("/campo?app=1");
	});

	const $fecha = document.getElementById("fecha");
	$fecha.value = new URLSearchParams(location.search).get("fecha") || hoyLocal();
	$fecha.addEventListener("change", () => {
		encuadrado = false;
		cargar();
	});
	document.getElementById("actualizar").addEventListener("click", cargar);
	cargar().then(pintarPanel);
	setInterval(() => {
		if (!document.hidden) cargar();
	}, 60000);
})();
