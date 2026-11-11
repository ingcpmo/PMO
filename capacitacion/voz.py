"""Narración en español con Piper (MIT) y la voz es-mls_10246-low
(entrenada con Multilingual LibriSpeech, OpenSLR 94, licencia CC BY 4.0).

La voz se descarga de https://github.com/rhasspy/piper/releases/tag/v0.0.2
y se indica con la variable de entorno QSG_VOZ (ruta al .onnx).
"""

import os
import re
import subprocess
import sys
import wave


_U = "cero uno dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince dieciséis diecisiete dieciocho diecinueve veinte veintiuno veintidós veintitrés veinticuatro veinticinco veintiséis veintisiete veintiocho veintinueve".split()
_D = {3: "treinta", 4: "cuarenta", 5: "cincuenta", 6: "sesenta", 7: "setenta", 8: "ochenta", 9: "noventa"}
_C = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos", 6: "seiscientos", 7: "setecientos", 8: "ochocientos", 9: "novecientos"}


def num2words(n, lang="es"):
	if n < 30:
		return _U[n]
	if n < 100:
		d, u = divmod(n, 10)
		return _D[d] + ("" if u == 0 else " y " + _U[u])
	if n < 1000:
		c, r = divmod(n, 100)
		if n == 100:
			return "cien"
		return _C[c] + ("" if r == 0 else " " + num2words(r))
	m, r = divmod(n, 1000)
	return ("mil" if m == 1 else num2words(m) + " mil") + ("" if r == 0 else " " + num2words(r))

CREDITO_VOZ = (
	"Voz sintética: Piper (licencia MIT), voz es-mls_10246 entrenada con Multilingual LibriSpeech "
	"(OpenSLR 94, CC BY 4.0)."
)

SIGLAS = {
	"dBmV": "decibelios milivoltio", "dBm": "decibelios miliwatt", "dB": "decibelios",
	"FTTH": "efe te te hache", "HFC": "hache efe ce", "ONT": "o ene te", "CTO": "ce te o",
	"SNR": "ese ene erre", "MER": "mer", "APC": "a pe ce", "UPC": "u pe ce", "EPP": "e pe pe",
	"QSG": "cu ese ge", "GPS": "ge pe ese", "SLA": "ese ele a", "RG6": "erre ge seis",
	"RG11": "erre ge once", "Mbps": "megabits por segundo", "nm": "nanómetros", "µm": "micras",
	"lb·pulg": "libras pulgada", "GPON": "ge pon", "PON": "pon", "MAC": "mac", "DOCSIS": "docsis",
	"OSHA": "osha", "NEC": "ene e ce", "AWG": "a doble ve ge", "SCTE": "ese ce te e", "BPI": "be pe i",
	"LOS": "ele o ese", "IEC": "i e ce", "PMO": "pe eme o", "RCP": "erre ce pe", "NPS": "ene pe ese",
	"PR": "Puerto Rico", "LUMA": "luma", "FOA": "efe o a", "Wi-Fi": "uaifai", "kV": "kilovoltios",
	"CMTS": "ce eme te ese", "OLT": "o ele te", "CFR": "ce efe erre", "NFPA": "ene efe pe a",
	"SC": "ese ce", "MLS": "eme ele ese", "CC": "ce ce", "BY": "bai", "MIT": "eme i te",
}
CODIGOS = {
	"COMP-OK": "comp o ka", "COMP-PARCIAL": "comp parcial", "CLI-AUS": "cli aus", "CLI-RECH": "cli rech",
	"CLI-REPROG": "cli reprog", "CLI-DIR": "cli dir", "RED-SINPUERTO": "red sin puerto",
	"RED-SINSENAL": "red sin señal", "RED-AVERIA": "red avería", "RED-CONSTR": "red constr",
}


def _num(m):
	signo, ent, dec = m.group(1), m.group(2), m.group(3)
	txt = num2words(int(ent), lang="es")
	if dec:
		txt += " coma " + " ".join(num2words(int(c), lang="es") for c in dec) if dec.startswith("0") else " coma " + num2words(int(dec), lang="es")
	return ("menos " if signo else "") + txt


def normalizar(t):
	t = re.sub(r"\s*\(PMO\)", "", t)
	t = t.replace("(Referencia; confirma con Liberty)", ", valor de referencia que se confirma con Liberty,")
	t = t.replace("≈", "aproximadamente ").replace("≥", "mayor o igual a ").replace("≤", "menor o igual a ")
	t = t.replace("+", "más ").replace("%", " por ciento").replace("·", " ").replace("/", " o ")
	t = t.replace("1 o 4", "un cuarto").replace("1 o 8", "un octavo").replace(" x ", " por ")
	for k, v in CODIGOS.items():
		t = t.replace(k, v)
	t = re.sub(r"(\d)\s*m\b", r"\1 metros", t)
	t = re.sub(r"(\d)\s*s\b", r"\1 segundos", t)
	t = re.sub(r"(\d)\s*cm\b", r"\1 centímetros", t)
	t = re.sub(r"(\d)\s*x\s*(\d)", r"\1 por \2", t)
	for k in sorted(SIGLAS, key=len, reverse=True):
		t = re.sub(rf"(?<![\w]){re.escape(k)}(?![\w])", SIGLAS[k], t)
	t = re.sub(r"(−)?(\d+)(?:[.,](\d+))?", _num, t)
	t = t.replace("−", " menos ").replace("(", ", ").replace(")", ", ").replace("'", "")
	return re.sub(r"\s+", " ", t).strip()


def narrar(texto, wav):
	modelo = os.environ.get("QSG_VOZ")
	if not modelo:
		raise SystemExit("Define QSG_VOZ con la ruta al modelo .onnx de la voz")
	subprocess.run([sys.executable, "-m", "piper", "-m", modelo, "-f", str(wav), "--sentence-silence", "0.25"],
				   input=normalizar(texto).encode("utf-8"), check=True, capture_output=True)
	with wave.open(str(wav)) as w:
		return w.getnframes() / w.getframerate()
