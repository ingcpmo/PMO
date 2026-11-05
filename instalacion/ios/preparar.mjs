// Prepara la app de iPhone "QSG Campo".
//   node preparar.mjs https://pmo.qsg.pr   -> escribe capacitor.config.json con ese servidor
//   node preparar.mjs --ios                 -> agrega los permisos de ubicación y cámara al proyecto ios/
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const arg = process.argv[2] || process.env.QSG_SERVIDOR || "";

if (arg === "--ios") {
	patchIos();
} else {
	writeConfig(arg);
}

function writeConfig(raw) {
	const servidor = raw.trim().replace(/\/+$/, "");
	let url;
	try {
		url = new URL(servidor);
	} catch {
		console.error("Indique la dirección de QSG PMO, por ejemplo: https://pmo.qsg.pr o http://192.168.1.50:8080");
		process.exit(1);
	}
	if (!/^https?:$/.test(url.protocol)) {
		console.error("La dirección debe empezar con http:// o https://");
		process.exit(1);
	}
	const config = {
		appId: "pr.qsg.campo",
		appName: "QSG Campo",
		webDir: "www",
		server: {
			url: `${servidor}/campo`,
			cleartext: url.protocol === "http:",
			allowNavigation: [url.hostname],
			errorPath: "index.html",
		},
		ios: { backgroundColor: "#0b5cab", contentInset: "automatic" },
		plugins: {},
	};
	fs.writeFileSync(path.join(here, "capacitor.config.json"), JSON.stringify(config, null, "\t") + "\n");
	fs.writeFileSync(path.join(here, "www", "servidor.js"), `window.QSG_SERVIDOR = ${JSON.stringify(servidor)};\n`);
	fs.writeFileSync(path.join(here, ".servidor"), servidor + "\n");
	console.log(`Servidor configurado: ${servidor}/campo`);
	if (url.protocol === "http:") {
		console.log("Aviso: con http:// la conexión no va cifrada y el iPhone pide una excepción. Use https:// en producción.");
	}
}

function patchIos() {
	const plistPath = path.join(here, "ios", "App", "App", "Info.plist");
	if (!fs.existsSync(plistPath)) {
		console.error("No existe ios/. Ejecute antes: npx cap add ios");
		process.exit(1);
	}
	let plist = fs.readFileSync(plistPath, "utf8");
	const claves = {
		NSLocationWhenInUseUsageDescription:
			"QSG Campo usa su ubicación para registrar la llegada a cada orden y para que despacho vea la ruta del día.",
		NSCameraUsageDescription: "QSG Campo usa la cámara para las fotos de evidencia de la instalación.",
		NSPhotoLibraryUsageDescription: "QSG Campo adjunta fotos de evidencia de la instalación.",
	};
	let extra = "";
	for (const [clave, texto] of Object.entries(claves)) {
		if (!plist.includes(`<key>${clave}</key>`)) extra += `\t<key>${clave}</key>\n\t<string>${texto}</string>\n`;
	}
	let servidor = "";
	try {
		servidor = fs.readFileSync(path.join(here, ".servidor"), "utf8").trim();
	} catch {
		/* sin servidor configurado */
	}
	// Solo para pruebas en la red local con http://: el iPhone exige una excepción de seguridad de transporte
	if (servidor.startsWith("http://") && !plist.includes("<key>NSAppTransportSecurity</key>")) {
		extra += "\t<key>NSAppTransportSecurity</key>\n\t<dict>\n\t\t<key>NSAllowsArbitraryLoads</key>\n\t\t<true/>\n\t</dict>\n";
	}
	if (extra) {
		plist = plist.replace(/<\/dict>\s*<\/plist>\s*$/, `${extra}</dict>\n</plist>\n`);
		fs.writeFileSync(plistPath, plist);
	}
	console.log("Proyecto iOS listo: permisos de ubicación, cámara y fotos.");
}
