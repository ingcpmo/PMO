// Copyright (c) 2026, QSG and contributors
// For license information, please see license.txt
// Envía la ubicación de la cuadrilla mientras la app de campo está abierta, para el tablero de
// despacho. Sin señal, guarda las lecturas en el teléfono y las envía al recuperarla. Solo en horario
// de trabajo (6:00 a 20:00) y solo si el usuario es miembro de una cuadrilla.
(() => {
	if (!("geolocation" in navigator) || !window.fetch) return;
	const URL = "/api/method/qsg_pmo.inteligencia.api.reportar_ubicacion";
	const COLA = "qsg_gps_cola";
	let intervalo = 120;
	let ultimoEnvio = 0;
	let ultimaPos = null;
	let activo = true;
	let bateria = null;

	const csrf = () => window.QSG_CSRF || (document.getElementById("app") || { dataset: {} }).dataset.csrf || "";
	const leer = () => {
		try {
			return JSON.parse(localStorage.getItem(COLA) || "[]");
		} catch (e) {
			return [];
		}
	};
	const guardar = (c) => {
		try {
			localStorage.setItem(COLA, JSON.stringify(c.slice(-300)));
		} catch (e) {
			/* almacenamiento lleno o bloqueado: se pierde la lectura */
		}
	};
	const metros = (a, b) => {
		const r = 6371000;
		const dLat = ((b.lat - a.lat) * Math.PI) / 180;
		const dLng = ((b.lng - a.lng) * Math.PI) / 180;
		const x = Math.sin(dLat / 2) ** 2 + Math.cos((a.lat * Math.PI) / 180) * Math.cos((b.lat * Math.PI) / 180) * Math.sin(dLng / 2) ** 2;
		return 2 * r * Math.asin(Math.sqrt(x));
	};
	const horario = () => {
		const h = new Date().getHours();
		return h >= 6 && h < 20;
	};

	async function enviar(p) {
		const body = new URLSearchParams({ lat: p.lat, lng: p.lng, momento: p.t });
		if (p.acc != null) body.set("precision", Math.round(p.acc));
		if (p.vel != null) body.set("velocidad", (p.vel * 3.6).toFixed(1));
		if (p.bat != null) body.set("bateria", p.bat);
		const r = await fetch(URL, {
			method: "POST",
			credentials: "same-origin",
			headers: { "X-Frappe-CSRF-Token": csrf(), Accept: "application/json" },
			body,
		});
		if (r.status === 403 || r.status === 401) {
			activo = false;
			return;
		}
		if (!r.ok) throw new Error(String(r.status));
		const m = ((await r.json()) || {}).message || {};
		if (m.ok === false) activo = false;
		if (m.intervalo) intervalo = Math.max(30, Number(m.intervalo));
	}

	async function vaciarCola() {
		let cola = leer();
		while (cola.length && navigator.onLine && activo) {
			try {
				await enviar(cola[0]);
				cola = cola.slice(1);
				guardar(cola);
			} catch (e) {
				break;
			}
		}
	}

	async function alMoverse(pos) {
		if (!activo || !horario()) return;
		const p = {
			lat: pos.coords.latitude,
			lng: pos.coords.longitude,
			acc: pos.coords.accuracy,
			vel: pos.coords.speed,
			bat: bateria,
			t: new Date(pos.timestamp || Date.now()).toISOString(),
		};
		const ahora = Date.now();
		const lejos = ultimaPos && metros(ultimaPos, p) > 250;
		if (ahora - ultimoEnvio < intervalo * 1000 && !lejos) return;
		ultimoEnvio = ahora;
		ultimaPos = p;
		if (!navigator.onLine) {
			guardar([...leer(), p]);
			return;
		}
		try {
			await vaciarCola();
			await enviar(p);
		} catch (e) {
			guardar([...leer(), p]);
		}
	}

	if (navigator.getBattery) {
		navigator.getBattery().then((b) => {
			const actualizar = () => (bateria = Math.round(b.level * 100));
			actualizar();
			b.addEventListener("levelchange", actualizar);
		});
	}
	window.addEventListener("online", vaciarCola);
	navigator.geolocation.watchPosition(alMoverse, () => {}, { enableHighAccuracy: true, maximumAge: 30000, timeout: 60000 });
})();
