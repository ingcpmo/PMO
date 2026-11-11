"""Genera la biblioteca de capacitación QSG: guías PDF, guiones, videos MP4,
catálogo maestro y banco de evaluación.

Uso: python3 build.py <carpeta_salida> <carpeta_pantallas_app>
Requiere: playwright (chromium), ffmpeg, openpyxl.
"""

import html
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from contenido import ACTIVIDADES, CODIGOS_CIERRE, PANTALLAS_APP  # noqa: E402

AZUL = "#0b5cab"
AMBAR = "#ffb020"
VERSION = "v1.0 · noviembre 2026"
LOGO = (
	'<svg viewBox="0 0 512 512" width="{s}" height="{s}"><rect width="512" height="512" rx="112" fill="#0b5cab"/>'
	'<circle cx="256" cy="236" r="118" fill="none" stroke="#fff" stroke-width="40"/>'
	'<path d="M318 300l86 86" stroke="#fff" stroke-width="44" stroke-linecap="round"/>'
	'<circle cx="256" cy="236" r="34" fill="#ffb020"/></svg>'
)
e = html.escape


def logo(s):
	return LOGO.format(s=s)


# ---------------------------------------------------------------- slides
SLIDE_CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{width:1920px;height:1080px;font-family:'DejaVu Sans',sans-serif;background:#f4f6f9;color:#14213d;overflow:hidden}}
.top{{height:120px;background:{AZUL};color:#fff;display:flex;align-items:center;padding:0 80px;gap:28px}}
.top .t{{font-size:40px;font-weight:bold}} .top .n{{margin-left:auto;font-size:30px;opacity:.85}}
.main{{padding:70px 110px;height:880px;display:flex;flex-direction:column;justify-content:center}}
.kicker{{color:{AZUL};font-size:34px;font-weight:bold;letter-spacing:2px;text-transform:uppercase;margin-bottom:24px}}
h1{{font-size:76px;line-height:1.15;margin-bottom:36px}}
p.big{{font-size:46px;line-height:1.45;color:#2b3a55}}
ul{{list-style:none}} li{{font-size:40px;line-height:1.4;margin:14px 0;padding-left:58px;position:relative}}
li:before{{content:'';position:absolute;left:0;top:14px;width:26px;height:26px;border-radius:6px;background:{AMBAR}}}
ul.bad li:before{{background:#d64545}} ul.ok li:before{{background:#1e9e5a}}
.foot{{position:absolute;bottom:0;left:0;right:0;height:80px;background:#fff;border-top:6px solid {AMBAR};display:flex;align-items:center;padding:0 80px;font-size:26px;color:#5a6680}}
.foot b{{color:{AZUL};margin-right:12px}} .foot .r{{margin-left:auto}}
.step{{font-size:150px;font-weight:bold;color:{AMBAR};line-height:1}}
.cover{{background:{AZUL};color:#fff;height:1080px;display:flex;flex-direction:column;justify-content:center;padding:0 140px}}
.cover h1{{font-size:96px;color:#fff}} .cover p{{font-size:44px;opacity:.9}}
.cover .tag{{display:inline-block;background:{AMBAR};color:#14213d;font-size:34px;font-weight:bold;padding:10px 26px;border-radius:12px;margin-bottom:40px}}
.phone{{display:flex;gap:90px;align-items:center;height:880px;padding:0 120px}}
.phone img{{height:820px;border-radius:40px;box-shadow:0 20px 60px rgba(0,0,0,.25);border:10px solid #14213d}}
"""


def page(body, titulo="", num=""):
	top = (
		f'<div class="top">{logo(70)}<div class="t">QSG · Capacitación de campo</div><div class="n">{e(num)} {e(titulo)}</div></div>'
		if titulo
		else ""
	)
	foot = f'<div class="foot"><b>QSG</b> Material original QSG para uso interno de capacitación<span class="r">{VERSION}</span></div>'
	return f"<html><head><meta charset='utf-8'><style>{SLIDE_CSS}</style></head><body>{top}{body}{foot if titulo else ''}</body></html>"


def dur(texto, minimo=5.0):
	return max(minimo, min(14.0, 2.5 + len(texto) / 15))


def slides_actividad(a):
	n, t = a["num"], a["titulo"]
	s = []
	s.append(
		(
			page(
				f'<div class="cover">{logo(160)}<div style="height:50px"></div><div><span class="tag">{e(a["tecnologia"])} · Módulo {n}</span></div>'
				f'<h1>{e(t)}</h1><p>Capacitación de campo QSG · Liberty Puerto Rico</p></div>'
			),
			5,
			f"Módulo {n}: {t}.",
		)
	)
	s.append(
		(
			page(f'<div class="main"><div class="kicker">Objetivo</div><p class="big">{e(a["objetivo"])}</p></div>', t, n),
			dur(a["objetivo"]),
			a["objetivo"],
		)
	)
	lis = "".join(f"<li>{e(x)}</li>" for x in a["epp"])
	s.append(
		(
			page(f'<div class="main"><div class="kicker">Herramientas, equipo y EPP</div><ul>{lis}</ul></div>', t, n),
			dur(" ".join(a["epp"]), 7),
			"Antes de empezar, verifica: " + "; ".join(a["epp"]) + ".",
		)
	)
	for i, (paso, det) in enumerate(a["pasos"], 1):
		s.append(
			(
				page(
					f'<div class="main" style="flex-direction:row;align-items:center;gap:80px"><div class="step">{i}</div>'
					f'<div><div class="kicker">Paso {i} de {len(a["pasos"])}</div><h1 style="font-size:64px">{e(paso)}</h1><p class="big">{e(det)}</p></div></div>',
					t,
					n,
				),
				dur(paso + det),
				f"Paso {i}. {paso}. {det}",
			)
		)
	lis = "".join(f"<li>{e(x)}</li>" for x in a["criterios"])
	s.append(
		(
			page(f'<div class="main"><div class="kicker">Criterios de aceptación QSG</div><ul class="ok">{lis}</ul></div>', t, n),
			dur(" ".join(a["criterios"]), 8),
			"Para aceptar el trabajo: " + "; ".join(a["criterios"]) + ".",
		)
	)
	lis = "".join(f"<li>{e(x)}</li>" for x in a["errores"])
	s.append(
		(
			page(f'<div class="main"><div class="kicker">Errores que generan retrabajo</div><ul class="bad">{lis}</ul></div>', t, n),
			dur(" ".join(a["errores"]), 8),
			"Evita estos errores: " + "; ".join(a["errores"]) + ".",
		)
	)
	lis = "".join(f"<li>{e(x)}</li>" for x in a["evidencia_app"])
	s.append(
		(
			page(f'<div class="main"><div class="kicker">Evidencia en la app QSG Campo</div><ul>{lis}</ul></div>', t, n),
			dur(" ".join(a["evidencia_app"]), 7),
			"En la app debes dejar: " + "; ".join(a["evidencia_app"]) + ".",
		)
	)
	s.append(
		(
			page(
				f'<div class="cover">{logo(140)}<div style="height:40px"></div><h1>Hazlo bien a la primera.</h1>'
				f'<p>Sin retrabajo, sin riesgos, con evidencia completa.</p><p style="margin-top:40px;font-size:34px">QSG · Módulo {n} · {e(t)}</p></div>'
			),
			5,
			"Hazlo bien a la primera: sin retrabajo, sin riesgos y con evidencia completa.",
		)
	)
	return s


def slides_app(a, pantallas_dir):
	s = slides_actividad(a)
	cuerpo = s[:3]
	t, n = a["titulo"], a["num"]
	for i, (img, tit, txt) in enumerate(PANTALLAS_APP, 1):
		src = (Path(pantallas_dir) / img).resolve().as_uri()
		cuerpo.append(
			(
				page(
					f'<div class="phone"><img src="{src}"><div><div class="kicker">Pantalla {i} de {len(PANTALLAS_APP)}</div>'
					f'<h1 style="font-size:70px">{e(tit)}</h1><p class="big">{e(txt)}</p></div></div>',
					t,
					n,
				),
				dur(tit + txt, 6),
				f"{tit}. {txt}",
			)
		)
	return cuerpo + s[-4:]


def render_video(slides, mp4, tmp, browser):
	tmp = Path(tmp)
	pg = browser.new_page(viewport={"width": 1920, "height": 1080})
	clips = []
	for i, (h, d, _) in enumerate(slides):
		f = tmp / f"s{i:03d}.html"
		f.write_text(h, encoding="utf-8")
		pg.goto(f.as_uri())
		pg.wait_for_timeout(150)
		png = tmp / f"s{i:03d}.png"
		pg.screenshot(path=str(png))
		clip = tmp / f"c{i:03d}.mp4"
		subprocess.run(
			[
				"ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", str(png), "-t", f"{d:.2f}",
				"-vf", f"fade=t=in:st=0:d=0.4,fade=t=out:st={d - 0.4:.2f}:d=0.4,format=yuv420p",
				"-r", "30", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", str(clip),
			],
			check=True,
		)
		clips.append(clip)
	pg.close()
	lst = tmp / "list.txt"
	lst.write_text("".join(f"file '{c}'\n" for c in clips))
	subprocess.run(
		["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy",
		 "-movflags", "+faststart", str(mp4)],
		check=True,
	)
	for c in tmp.glob("*"):
		c.unlink()


def guion_md(a, slides):
	out = [f"# Guion de narración · Módulo {a['num']}: {a['titulo']}", "",
		   "Video original QSG. Lee el texto de cada escena a ritmo normal; la duración ya está ajustada.",
		   "Para grabar la voz: graba cada escena por separado y móntala sobre el video sin música de terceros.", "",
		   "| Escena | Duración | Narración |", "|---|---|---|"]
	t = 0.0
	for i, (_, d, txt) in enumerate(slides, 1):
		out.append(f"| {i} ({int(t // 60)}:{int(t % 60):02d}) | {d:.0f} s | {txt.replace('|', '/')} |")
		t += d
	out += ["", f"Duración total: {int(t // 60)} min {int(t % 60)} s.", ""]
	return "\n".join(out)


# ---------------------------------------------------------------- PDF guide
DOC_CSS = f"""
@page{{size:Letter;margin:16mm 16mm 18mm}}
body{{font-family:'DejaVu Sans',sans-serif;font-size:10.5pt;color:#14213d;line-height:1.45}}
.hdr{{display:flex;align-items:center;gap:14px;border-bottom:4px solid {AMBAR};padding-bottom:10px;margin-bottom:14px}}
.hdr .t{{font-size:9pt;color:#5a6680}} h1{{font-size:20pt;color:{AZUL};margin:0}}
h2{{font-size:12.5pt;color:{AZUL};border-left:6px solid {AMBAR};padding-left:8px;margin:16px 0 6px}}
table{{border-collapse:collapse;width:100%;font-size:9.5pt}} td,th{{border:1px solid #d5dbe5;padding:5px 7px;vertical-align:top;text-align:left}}
th{{background:#eef2f7}} ol li,ul li{{margin:3px 0}} .note{{background:#fff2d6;padding:8px 10px;border-radius:6px;font-size:9pt}}
.chk td:first-child{{width:22px}} .box{{display:inline-block;width:12px;height:12px;border:1.5px solid #14213d}}
.ftr{{margin-top:18px;font-size:8pt;color:#5a6680;border-top:1px solid #d5dbe5;padding-top:6px}}
a{{color:{AZUL}}}
"""


def guia_html(a):
	h = [f"<html><head><meta charset='utf-8'><style>{DOC_CSS}</style></head><body>"]
	h.append(f'<div class="hdr">{logo(54)}<div><div class="t">QSG · Guía de campo · Módulo {a["num"]} · {e(a["tecnologia"])}</div><h1>{e(a["titulo"])}</h1></div></div>')
	h.append(f"<h2>Objetivo</h2><p>{e(a['objetivo'])}</p>")
	h.append("<h2>Herramientas, equipo y EPP</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in a["epp"]) + "</ul>")
	h.append("<h2>Procedimiento</h2><ol>" + "".join(f"<li><b>{e(p)}.</b> {e(d)}</li>" for p, d in a["pasos"]) + "</ol>")
	h.append("<h2>Criterios de aceptación</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in a["criterios"]) + "</ul>")
	h.append('<p class="note">Los valores marcados <b>PMO</b> son los que valida la app QSG Campo. Los marcados <b>Referencia</b> son prácticas de la industria: confírmalos con el manual técnico vigente de Liberty Puerto Rico, que siempre prevalece.</p>')
	h.append("<h2>Errores que generan retrabajo</h2><ul>" + "".join(f"<li>{e(x)}</li>" for x in a["errores"]) + "</ul>")
	h.append('<h2>Lista de verificación antes de cerrar</h2><table class="chk">' + "".join(f'<tr><td><span class="box"></span></td><td>{e(x)}</td></tr>' for x in a["evidencia_app"] + a["criterios"]) + "</table>")
	cods = {c[0]: c for c in CODIGOS_CIERRE}
	h.append("<h2>Códigos de cierre relacionados</h2><table><tr><th>Código</th><th>Cuándo usarlo</th><th>Resultado</th><th>Se cobra</th><th>Reprograma</th></tr>")
	for c in a["codigos"]:
		k = cods[c]
		h.append(f"<tr><td><b>{k[0]}</b></td><td>{e(k[1])}</td><td>{k[2]}</td><td>{k[5]}</td><td>{k[6]}</td></tr>")
	h.append("</table>")
	if a["videos"]:
		h.append("<h2>Material de referencia externo (solo enlaces)</h2><table><tr><th>Recurso</th><th>Autor</th><th>Qué observar</th></tr>")
		for tit, url, autor, idioma, lic, nota in a["videos"]:
			h.append(f'<tr><td><a href="{e(url)}">{e(tit)}</a><br><small>{e(idioma)}</small></td><td>{e(autor)}</td><td>{e(nota)}</td></tr>')
		h.append("</table><p style='font-size:8.5pt'>Los derechos de estos recursos pertenecen a sus autores. QSG solo los enlaza; no los copia ni los modifica.</p>")
	h.append("<h2>Autoevaluación</h2><ol>")
	for q, ops, _ in a["preguntas"]:
		h.append(f"<li>{e(q)}<br>" + " &nbsp; ".join(f"{chr(97 + i)}) {e(o)}" for i, o in enumerate(ops)) + "</li>")
	h.append("</ol><p style='font-size:8.5pt'>Respuestas: " + ", ".join(f"{i}-{chr(97 + r)}" for i, (_, _, r) in enumerate(a["preguntas"], 1)) + "</p>")
	h.append(f'<div class="ftr">QSG · Material original para capacitación interna de cuadrillas y contratistas · {VERSION}. No sustituye el manual técnico de Liberty Puerto Rico ni el programa de seguridad de la empresa.</div></body></html>')
	return "".join(h)


def to_pdf(browser, html_str, pdf, tmp):
	f = Path(tmp) / "doc.html"
	f.write_text(html_str, encoding="utf-8")
	pg = browser.new_page()
	pg.goto(f.as_uri())
	pg.pdf(path=str(pdf), format="Letter", print_background=True)
	pg.close()


def enlaces_md(a):
	out = [f"# Material de referencia · Módulo {a['num']}: {a['titulo']}", "",
		   "Estos recursos son de terceros. QSG solo los enlaza: no se descargan, no se vuelven a subir y no se les pone la marca QSG.", "",
		   "| Recurso | Autor | Idioma | Uso permitido | Qué observar |", "|---|---|---|---|---|"]
	for tit, url, autor, idioma, lic, nota in a["videos"]:
		out.append(f"| [{tit}]({url}) | {autor} | {idioma} | {lic} | {nota} |")
	return "\n".join(out) + "\n"


# ---------------------------------------------------------------- Excel
def hoja(ws, cab, filas, anchos):
	ws.append(cab)
	for c in ws[1]:
		c.font = Font(bold=True, color="FFFFFF")
		c.fill = PatternFill("solid", fgColor="0B5CAB")
		c.alignment = Alignment(vertical="center", wrap_text=True)
	for f in filas:
		ws.append(f)
	for i, w in enumerate(anchos, 1):
		ws.column_dimensions[get_column_letter(i)].width = w
	for row in ws.iter_rows(min_row=2):
		for c in row:
			c.alignment = Alignment(vertical="top", wrap_text=True)
	ws.freeze_panes = "A2"
	ws.auto_filter.ref = ws.dimensions


def catalogo(path):
	wb = Workbook()
	ws = wb.active
	ws.title = "Videos externos"
	filas = []
	for a in ACTIVIDADES:
		for tit, url, autor, idioma, lic, nota in a["videos"]:
			filas.append([a["num"], a["titulo"], tit, autor, idioma, lic, nota, url])
	hoja(ws, ["Módulo", "Actividad", "Recurso", "Autor", "Idioma", "Uso permitido", "Qué observar", "Enlace"], filas, [8, 26, 46, 22, 10, 34, 50, 60])
	for r in range(2, ws.max_row + 1):
		c = ws.cell(r, 8)
		c.hyperlink = c.value
		c.font = Font(color="0B5CAB", underline="single")
	ws = wb.create_sheet("Material QSG")
	filas = []
	for a in ACTIVIDADES:
		base = a["carpeta"]
		filas.append([a["num"], a["titulo"], "Video", f"{base}/Video-QSG-{a['num']}.mp4", a["duracion_video"], "Original QSG"])
		filas.append([a["num"], a["titulo"], "Guía de campo (PDF)", f"{base}/Guia-QSG-{a['num']}.pdf", "2–3 páginas", "Original QSG"])
		filas.append([a["num"], a["titulo"], "Guion de narración", f"{base}/Guion-video-{a['num']}.md", "", "Original QSG"])
		if a["videos"]:
			filas.append([a["num"], a["titulo"], "Enlaces de referencia", f"{base}/Enlaces-de-referencia-{a['num']}.md", "", "Solo enlaces"])
	hoja(ws, ["Módulo", "Actividad", "Tipo", "Archivo", "Duración", "Propiedad"], filas, [8, 34, 24, 60, 12, 16])
	ws = wb.create_sheet("Códigos de cierre")
	hoja(ws, ["Código", "Descripción", "Resultado", "Causa", "Detiene SLA", "Se cobra", "Reprograma"], [list(c) for c in CODIGOS_CIERRE], [16, 44, 16, 12, 12, 10, 12])
	ws = wb.create_sheet("Rangos de medición")
	hoja(ws, ["Tecnología", "Medición", "Mínimo", "Máximo", "Unidad", "Fuente"], [
		["FTTH", "Potencia recibida en ONT a 1490 nm", -25, -8, "dBm", "PMO (valida la app)"],
		["FTTH", "Pérdida por empalme de fusión", "", 0.10, "dB", "Referencia, confirmar con Liberty"],
		["FTTH", "Diferencia CTO a roseta", "", 1.5, "dB", "Referencia, confirmar con Liberty"],
		["HFC", "Nivel downstream en el módem", -7, 7, "dBmV", "PMO (valida la app)"],
		["HFC", "MER / SNR downstream", 35, "", "dB", "PMO (valida la app)"],
		["HFC", "Nivel de transmisión upstream", 35, 51, "dBmV", "PMO (valida la app)"],
	], [12, 40, 10, 10, 10, 36])
	wb.save(path)


def banco(path):
	wb = Workbook()
	ws = wb.active
	ws.title = "Banco de preguntas"
	filas = []
	for a in ACTIVIDADES:
		for q, ops, r in a["preguntas"]:
			filas.append([a["num"], a["titulo"], q, *ops, chr(97 + r)])
	hoja(ws, ["Módulo", "Actividad", "Pregunta", "a)", "b)", "c)", "d)", "Respuesta"], filas, [8, 30, 54, 26, 26, 26, 26, 10])
	ws = wb.create_sheet("Registro de capacitación")
	hoja(ws, ["Fecha", "Técnico", "Contratista", "Cuadrilla", "Módulo", "Calificación (%)", "Aprobado (≥ 80 %)", "Instructor", "Observaciones"], [], [12, 26, 22, 14, 10, 14, 16, 22, 40])
	wb.save(path)


def leeme(browser, ini, tmp):
	md = Path(__file__).parent / "LEEME.md"
	shutil.copy(md, ini / "LEEME-QSG.md")
	body = subprocess.run(["pandoc", str(md), "-f", "gfm", "-t", "html"], capture_output=True, text=True, check=True).stdout
	h = (
		f"<html><head><meta charset='utf-8'><style>{DOC_CSS} h1{{display:none}}</style></head><body>"
		f"<div class='hdr'>{logo(54)}<div><div class='t'>QSG · Capacitación de campo · {VERSION}</div>"
		f"<div style='font-size:20pt;color:{AZUL};font-weight:bold'>Biblioteca de capacitación FTTH y HFC</div></div></div>{body}</body></html>"
	)
	to_pdf(browser, h, ini / "LEEME-QSG.pdf", tmp)


# ---------------------------------------------------------------- main
def main(out, pantallas):
	out = Path(out)
	if out.exists():
		shutil.rmtree(out)
	out.mkdir(parents=True)
	tmp = tempfile.mkdtemp()
	with sync_playwright() as p:
		br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").is_file() else None)
		for a in ACTIVIDADES:
			d = out / a["carpeta"]
			d.mkdir()
			sl = slides_app(a, pantallas) if a["num"] == "09" else slides_actividad(a)
			render_video(sl, d / f"Video-QSG-{a['num']}.mp4", tmp, br)
			(d / f"Guion-video-{a['num']}.md").write_text(guion_md(a, sl), encoding="utf-8")
			to_pdf(br, guia_html(a), d / f"Guia-QSG-{a['num']}.pdf", tmp)
			if a["videos"]:
				(d / f"Enlaces-de-referencia-{a['num']}.md").write_text(enlaces_md(a), encoding="utf-8")
			print("ok", a["carpeta"], flush=True)
		ini = out / "00-Inicio"
		ini.mkdir()
		catalogo(ini / "Catalogo-maestro-QSG.xlsx")
		leeme(br, ini, tmp)
		ev = out / "10-Evaluaciones"
		ev.mkdir()
		banco(ev / "Banco-de-preguntas-y-registro.xlsx")
		br.close()


if __name__ == "__main__":
	main(sys.argv[1], sys.argv[2])
