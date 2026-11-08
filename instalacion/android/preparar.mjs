// Prepara la app Android "QSG Campo".
//   node preparar.mjs http://192.168.1.50:8080   -> escribe capacitor.config.json con ese servidor
//   node preparar.mjs --android                  -> ajusta permisos e iconos del proyecto android/
//   node preparar.mjs --preguntar                -> APK de descarga directa: pide la dirección del
//                                                   servidor la primera vez que se abre y la recuerda
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const arg = process.argv[2] || process.env.QSG_SERVIDOR || "";

if (arg === "--android") {
	patchAndroid();
} else if (arg === "--preguntar") {
	writeConfigPreguntar();
} else {
	writeConfig(arg);
}

function writeConfig(raw) {
	const servidor = raw.trim().replace(/\/+$/, "");
	let url;
	try {
		url = new URL(servidor);
	} catch {
		console.error("Indique la dirección de QSG PMO, por ejemplo: http://192.168.1.50:8080 o https://pmo.qsg.pr");
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
		android: { backgroundColor: "#0b5cab" },
		plugins: {},
	};
	fs.writeFileSync(path.join(here, "capacitor.config.json"), JSON.stringify(config, null, "\t") + "\n");
	fs.writeFileSync(path.join(here, "www", "servidor.js"), `window.QSG_SERVIDOR = ${JSON.stringify(servidor)};\n`);
	console.log(`Servidor configurado: ${servidor}/campo`);
	if (url.protocol === "http:") {
		console.log("Aviso: con http:// la conexión no va cifrada. Úselo solo para pruebas en la red local.");
	}
}

function writeConfigPreguntar() {
	// Servidores que la app abre dentro de ella (con GPS y cámara) cuando la dirección se escribe al
	// abrirla: GitHub Codespaces (y su inicio de sesión para puertos privados) y la red local. Otra
	// dirección se abre en el navegador; para un dominio propio, construya el APK con esa dirección.
	const permitidos = ["*.app.github.dev", "github.com", "192.168.*.*", "10.*.*.*", "172.*.*.*"];
	const config = {
		appId: "pr.qsg.campo",
		appName: "QSG Campo",
		webDir: "www",
		server: {
			cleartext: true,
			allowNavigation: permitidos,
			errorPath: "index.html",
		},
		android: { backgroundColor: "#0b5cab" },
		plugins: {},
	};
	fs.writeFileSync(path.join(here, "capacitor.config.json"), JSON.stringify(config, null, "\t") + "\n");
	fs.writeFileSync(path.join(here, "www", "servidor.js"), "window.QSG_SERVIDOR = \"\";\n");
	console.log("APK de descarga directa: pedirá la dirección del servidor la primera vez que se abra.");
}

function patchAndroid() {
	const main = path.join(here, "android", "app", "src", "main");
	const manifestPath = path.join(main, "AndroidManifest.xml");
	if (!fs.existsSync(manifestPath)) {
		console.error("No existe android/. Ejecute antes: npx cap add android");
		process.exit(1);
	}
	let manifest = fs.readFileSync(manifestPath, "utf8");
	const permissions = [
		"android.permission.INTERNET",
		"android.permission.ACCESS_COARSE_LOCATION",
		"android.permission.ACCESS_FINE_LOCATION",
		"android.permission.CAMERA",
	];
	const missing = permissions.filter((p) => !manifest.includes(`"${p}"`));
	if (missing.length) {
		const lines = missing.map((p) => `    <uses-permission android:name="${p}" />`).join("\n");
		manifest = manifest.replace(/<\/manifest>\s*$/, `${lines}\n    <uses-feature android:name="android.hardware.location.gps" android:required="false" />\n    <uses-feature android:name="android.hardware.camera" android:required="false" />\n</manifest>\n`);
		fs.writeFileSync(manifestPath, manifest);
	}

	// Icono de QSG en todas las densidades (se usa el mismo PNG; Android lo escala)
	const icon = path.join(here, "..", "..", "qsg_pmo", "public", "images", "qsg-icon-512.png");
	const res = path.join(main, "res");
	if (fs.existsSync(icon)) {
		fs.rmSync(path.join(res, "mipmap-anydpi-v26"), { recursive: true, force: true });
		for (const dir of fs.readdirSync(res).filter((d) => d.startsWith("mipmap-"))) {
			for (const name of ["ic_launcher.png", "ic_launcher_round.png", "ic_launcher_foreground.png"]) {
				fs.copyFileSync(icon, path.join(res, dir, name));
			}
		}
	}
	console.log("Proyecto Android listo: permisos de cámara y ubicación, icono de QSG.");
}
