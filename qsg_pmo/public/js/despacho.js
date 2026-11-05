// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt
// Tablero de despacho: mapa en vivo, alertas del GPS, recomendaciones, órdenes sin asignar y asistente.
(() => {
	const $root = document.getElementById("despacho");
	const CSRF = $root.dataset.csrf;
	const DESPACHA = $root.dataset.despacha === "1";
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
	const S = { datos: null, tab: "alertas", chat: [], interpretado: null };

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
			["Sin asignar", cuenta((x) => !x.crew && ABIERTAS.includes(x.status)), cuenta((x) => !x.crew && ABIERTAS.includes(x.status)) ? "alerta" : ""],
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
			html = html || '<div class="vacio">Sin alertas. Las cuadrillas van según lo planificado.</div>';
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
			const lista = d.ordenes.filter((o) => !o.crew && ABIERTAS.includes(o.status));
			html = lista
				.map((o) =>
					tarjeta(
						o.priority === "Crítica" || o.priority === "Alta" ? "alta" : "",
						`${esc(o.name)} · ${esc(o.priority || "")}`,
						`<p>${esc(o.work_type || "")} · ${esc(o.municipality || "")} · ${esc(o.segment || "")}</p>`,
						DESPACHA ? `<button class="btn peq primario" data-mejor="${esc(o.name)}">Mejor cuadrilla</button>` : "",
					),
				)
				.join("");
			html = html || '<div class="vacio">Todas las órdenes del día tienen cuadrilla.</div>';
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
					(o, i) => `<div class="tarjeta"><h4>${i + 1}. ${esc(o.cuadrilla)} <span class="suave">${esc(o.contratista || "")}</span></h4>
					<p>Llegada ${esc(hora(o.llegada))} · termina ${esc(hora(o.termina))}</p>
					<p class="suave">${o.razones.map(esc).join(" · ")}</p>
					<div class="acciones"><button class="btn peq primario" data-asignar="${esc(o.cuadrilla)}">Asignar</button></div></div>`,
				)
				.join("");
			abrir(
				`<h3>Mejor cuadrilla para ${esc(orden)}</h3>` +
					(r.ubicacion_aproximada ? '<p class="suave">La orden no tiene GPS: se usó el centro del municipio.</p>' : "") +
					filas,
			);
			$modal.querySelectorAll("[data-asignar]").forEach((b) =>
				b.addEventListener("click", async () => {
					const motivo = window.prompt("Motivo de la asignación", "Sugerencia de mejor cuadrilla");
					if (!motivo) return;
					try {
						await post("reasignar", { orden, cuadrilla: b.dataset.asignar, motivo, recomendacion: recomendacion || null });
						cerrar();
						aviso(`${orden} asignada a ${b.dataset.asignar}`);
						cargar();
					} catch (err) {
						aviso(err.message, true);
					}
				}),
			);
		} catch (err) {
			abrir(`<p>${esc(err.message)}</p>`);
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
			pintarKpis();
			pintarMapa();
			if (S.tab !== "asistente") pintarPanel();
		} catch (err) {
			aviso(err.message, true);
		}
	}
	const $fecha = document.getElementById("fecha");
	$fecha.value = new URLSearchParams(location.search).get("fecha") || hoyLocal();
	$fecha.addEventListener("change", () => {
		encuadrado = false;
		cargar();
	});
	document.getElementById("actualizar").addEventListener("click", cargar);
	cargar().then(pintarPanel);
	setInterval(() => {
		if (!document.hidden && S.tab !== "asistente") cargar();
	}, 60000);
})();
