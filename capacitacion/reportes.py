"""Genera los reportes PDF del marco end-to-end HFC y FTTH (fuentes abiertas).

Uso: python3 reportes.py <carpeta_salida>
"""

import html
import sys
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).parent))
from build import AMBAR, AZUL, logo  # noqa: E402

e = html.escape
FECHA = "11 de noviembre de 2026"
YT = "https://www.youtube.com/watch?v="

CSS = f"""
@page{{size:Letter;margin:15mm 15mm 17mm}}
body{{font-family:'DejaVu Sans',sans-serif;font-size:9.6pt;color:#14213d;line-height:1.42}}
.hdr{{display:flex;align-items:center;gap:14px;border-bottom:4px solid {AMBAR};padding-bottom:10px;margin-bottom:12px}}
.hdr .t{{font-size:8.5pt;color:#5a6680}} h1{{font-size:19pt;color:{AZUL};margin:0}}
h2{{font-size:12.5pt;color:{AZUL};border-left:6px solid {AMBAR};padding-left:8px;margin:18px 0 6px;page-break-after:avoid}}
h3{{font-size:10.5pt;color:#14213d;margin:12px 0 4px;page-break-after:avoid}}
table{{border-collapse:collapse;width:100%;font-size:8.6pt;margin:4px 0 8px}} td,th{{border:1px solid #d5dbe5;padding:4px 6px;vertical-align:top;text-align:left}}
th{{background:#eef2f7}} tr{{page-break-inside:avoid}}
.u{{display:block;font-size:7.2pt;color:#5a6680;word-break:break-all}}
.box{{background:#fff2d6;padding:9px 11px;border-radius:6px;margin:8px 0}}
.exec{{background:#e9f1fb;border-left:5px solid {AZUL};padding:10px 12px;border-radius:4px}}
.ok{{color:#1e7a46;font-weight:bold}} .no{{color:#b23b3b;font-weight:bold}} .mid{{color:#9a6b00;font-weight:bold}}
ul{{margin:4px 0 4px 18px;padding:0}} li{{margin:2px 0}}
.ftr{{margin-top:16px;font-size:7.5pt;color:#5a6680;border-top:1px solid #d5dbe5;padding-top:6px}}
a{{color:{AZUL};text-decoration:none}}
"""


def L(titulo, url):
	return f'<a href="{e(url)}">{e(titulo)}</a><span class="u">{e(url)}</span>'


def tabla(cab, filas):
	h = "<table><tr>" + "".join(f"<th>{c}</th>" for c in cab) + "</tr>"
	for f in filas:
		h += "<tr>" + "".join(f"<td>{c}</td>" for c in f) + "</tr>"
	return h + "</table>"


def doc(titulo, sub, cuerpo):
	return (
		f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body>"
		f'<div class="hdr">{logo(54)}<div><div class="t">QSG PMO · Capacitación · {FECHA}</div><h1>{e(titulo)}</h1>'
		f'<div class="t">{e(sub)}</div></div></div>{cuerpo}'
		f'<div class="ftr">QSG · Reporte de investigación. Los contenidos enlazados pertenecen a sus autores; QSG solo los referencia. '
		f"Ninguno de estos materiales se descargó ni se editó. El manual técnico de Liberty Puerto Rico siempre prevalece.</div></body></html>"
	)


LIC_OK = '<span class="ok">Ver y enlazar libremente</span>'
LIC_PERM = '<span class="mid">Ver libre; copiar o editar requiere permiso</span>'

NORMAS_PR = tabla(
	["Norma o requisito", "Qué exige", "Fuente"],
	[
		["Código de Construcción de PR 2018", "Adopta el NEC 2017 (NFPA 70) y el Reglamento Complementario al Código Eléctrico. Vigente desde el 15 de noviembre de 2018.", L("ICC: Puerto Rico Code Alert", "https://www.icc-nta.org/code-update/puerto-rico-commonwealth-code-alert/")],
		["NEC 2017, Art. 820 (coaxial)", "La malla se conecta a tierra lo más cerca posible de la entrada (820.93). Conductor de cobre de 14 AWG o más, de hasta 6 m (20 pies) en viviendas de una o dos familias (820.100).", "NFPA 70 (2017)"],
		["NEC 2017, Art. 770 (fibra)", "Cables de fibra óptica en edificios. Los miembros metálicos del cable se conectan a tierra; un drop totalmente dieléctrico no requiere tierra.", "NFPA 70 (2017)"],
		["OSHA 29 CFR 1910.268 (telecomunicaciones)", "La aplica PR OSHA. Exige capacitación con registro certificado (nombre del técnico, firma de quien capacita y fecha), además de primeros auxilios y RCP.", L("OSHA 1910.268", "https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.268")],
		["OSHA 29 CFR 1926.1053 (escaleras)", "Ángulo 4 a 1, que sobresalga 3 pies sobre el apoyo y tres puntos de contacto. Distancia de 10 pies (3 m) a líneas de hasta 50 kV.", L("OSHA 1926.1053", "https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.1053")],
		["Requisito de Liberty PR para sus técnicos", "Certificación SCTE BPI, licencia de conducir, escalera de extensión, trabajo en altura de más de 30 pies, conocimiento del NEC y de las reglas de la FCC, y ser bilingüe.", L("Oferta de empleo: Liberty PR Service Technician", "https://www.mediabistro.com/jobs/3530823456-service-technician")],
		["Red de Liberty PR", "HFC con DOCSIS 3.1 en más del 60 % de los hogares, y FTTH en expansión (abril de 2023).", L("DPL News", "https://dplnews.com/puerto-rico-liberty-actualiza-su-red-fija-y-ofrece-velocidad-de-hasta-1000-mbps/")],
	],
)


# ===================================================================== HFC
def hfc():
	c = []
	c.append(
		'<h2>Resumen ejecutivo</h2><div class="exec"><ul>'
		"<li><b>Objetivo:</b> darles al equipo técnico y al administrativo una visión de todo el proceso de una instalación HFC de abonado antes de salir a campo. No reemplaza la formación de los técnicos.</li>"
		"<li><b>Hallazgo principal:</b> la mejor fuente abierta es <b>FLOW Tech Spot</b>, la guía de técnicos de FLOW, marca de Liberty Latin America en el Caribe (el mismo grupo que Liberty PR). Cubre de forma estructurada, con fotos, la acometida desde el tap, el conector F, la tierra, el cableado interior, el módem y el cierre.</li>"
		"<li><b>Videos de calidad abiertos:</b> PPC (preparación e instalación del conector de drop), VIAVI (fugas y certificación del hogar) y OSHA (escaleras y líneas eléctricas).</li>"
		"<li><b>Brecha:</b> no existe un video abierto de una acometida completa, del tap a la casa, hecho por una escuela o un fabricante. Ese tramo solo está documentado como guía con fotos.</li>"
		"<li><b>Plataformas formales:</b> SCTE BPI (Liberty la exige), NCTI Installer y SATSAID (en español) son de pago y con derechos reservados.</li>"
		"<li><b>Propiedad intelectual:</b> todo se ve y se enlaza gratis. Para descargar o editar un video de terceros hay que pedir permiso al autor.</li>"
		"<li><b>Decisión pendiente:</b> (1) página de entrenamiento QSG en español con los 11 pasos y enlaces; (2) pedir permiso a PPC y VIAVI para subtitular y editar sus videos; (3) ambas.</li>"
		"</ul></div>"
	)
	c.append("<h2>1. Fuente principal: FLOW Tech Spot (Liberty Latin America)</h2>")
	c.append(
		"<p>Es la guía de técnicos de FLOW (Cable &amp; Wireless / Liberty Latin America, Trinidad y Tobago): texto con fotos, en inglés, sin registro. Su objetivo declarado es enseñar lo que un técnico necesita para operar en una planta HFC. "
		"Algunas reglas son locales de Trinidad (por ejemplo, la eléctrica T&amp;TEC); en PR rige el NEC 2017 con LUMA.</p>"
	)
	c.append(
		tabla(
			["Página", "Contenido útil"],
			[
				[L("Home", "https://sites.google.com/view/tt-flowtechspot/home"), "Qué es la planta HFC; índice del sitio."],
				[L("Installation Fundamentals", "https://sites.google.com/view/tt-flowtechspot/installation-fundamentals"), "2.3 firma de la orden de trabajo; 3.2 conector F en 6 pasos; 4.1 a 4.4 drop aéreo, amarre al mensajero, vano y ganchos; 4.7 caja de acometida; 4.8 lazo de goteo (unos 5 pulgadas en RG6) y radio de curvatura; 4.9 tierra (obligatoria; cobre 14 AWG); 5 bloque de tierra; 6 toma de pared; 7 MoCA y módem; 5.2 y 7.2 niveles QAM."],
				[L("Service/Repair", "https://sites.google.com/view/tt-flowtechspot/servicerepair"), "Diagnóstico, atenuación del drop, conector F paso a paso, frecuencias, MER/BER."],
				[L("DOCSIS 3.1", "https://sites.google.com/view/tt-flowtechspot/docsis-3-1"), "Tecnología del módem que usa Liberty PR."],
				[L("Cable Loss Calculation", "https://sites.google.com/view/tt-flowtechspot/cable-loss-calculation"), "Pérdidas del cable y de los divisores."],
				[L("Customer Service", "https://sites.google.com/view/tt-flowtechspot/customer-service"), "Atención al cliente."],
				[L("Technician Checklist", "https://sites.google.com/view/tt-flowtechspot/technician-checklist"), "Visita: puntualidad, presentación, explicación del Wi-Fi, prueba de velocidad y demostración de TV."],
			],
		)
	)
	c.append("<h2>2. Secuencia end-to-end de la instalación HFC</h2>")
	c.append(
		tabla(
			["#", "Paso", "Fuente abierta", "Tipo / autor", "Para"],
			[
				["1", "Qué es HFC y cómo llega al cliente", L("FLOW Tech Spot · Home", "https://sites.google.com/view/tt-flowtechspot/home") + L("FLOW · DOCSIS 3.1", "https://sites.google.com/view/tt-flowtechspot/docsis-3-1"), "Texto · FLOW", "Adm. y técnico"],
				["2", "Seguridad: escalera y líneas eléctricas", L("OSHA: 5 Things to Know about Ladder Safety", YT + "GuPdykagKMg") + L("OSHA: Work Safely with Ladders Near Power Lines", YT + "4QcctfnUeOM"), "Video oficial · OSHA", "Técnico"],
				["3", "Acometida aérea desde el tap", L("Installation Fundamentals, sec. 4.1 a 4.4", "https://sites.google.com/view/tt-flowtechspot/installation-fundamentals"), "Texto con fotos · FLOW", "Técnico"],
				["4", "Preparación del coaxial y conector F de compresión", L("PPC: Drop Connector Preparation and Installation", "https://www.ppc-online.com/hubfs/VIDEOS/drop-connector-installation_video.mp4") + L("PPC: página de videos", "https://www.ppc-online.com/videos"), "Video · PPC Broadband (Belden)", "Técnico"],
				["4b", "Coaxial paso a paso para estudiar", L("FOA: Coax Cable, guía VHO (PDF)", "https://foa.org/tech/ref/premises/VHO/VHO-coax.pdf") + L("Fiber U: lección Coax Cable", "https://fiberu.org/Basic_Skills_Lab_Copper_Cabling/LP1-coax.html") + L("FOA: video Coax Cables", YT + "OQnlN8qwpu4"), "PDF y video · FOA", "Técnico"],
				["5", "Tierra: bloque de tierra y conductor", L("Installation Fundamentals, sec. 4.9 y 5", "https://sites.google.com/view/tt-flowtechspot/installation-fundamentals") + L("Viasat: Installation Grounding Job Aid", "https://eguide.field.viasat.com/installation-grounding-job-aid/"), "Texto · FLOW y Viasat", "Técnico"],
				["6", "Lazo de goteo, radio de curvatura y entrada", L("Installation Fundamentals, sec. 4.8", "https://sites.google.com/view/tt-flowtechspot/installation-fundamentals"), "Texto · FLOW", "Técnico"],
				["7", "Cableado interior, divisores, MoCA y módem", L("Installation Fundamentals, sec. 5 a 7", "https://sites.google.com/view/tt-flowtechspot/installation-fundamentals"), "Texto · FLOW", "Técnico"],
				["8", "Niveles de señal", L("VIAVI: Cable Subscriber Installation Test Guide (PDF)", "https://www.viavisolutions.com/en-uk/literature/cable-subscriber-installation-test-guide-brochures-en.pdf"), "Guía · VIAVI", "Técnico y supervisor"],
				["9", "Fugas e ingreso: certificación del hogar", L("VIAVI: Home Leakage Pressure Test Demonstration (9:38)", "https://video.viavisolutions.com/detail/videos/signal-leakage/video/1708632626568330138/home-leakage-pressure-test-demonstration") + L("VIAVI: Introducing Home Leakage Testing (6:26)", "https://video.viavisolutions.com/detail/videos/signal-leakage/video/5841930055001/viavi:-introducing-home-leakage-testing"), "Video · VIAVI", "Técnico y supervisor"],
				["9b", "Por qué el 70 % del ruido nace en la casa", L("SCTE/VIAVI: The Connected Home, Ingress Test Equipment Training (PDF)", "https://www.scte.org/documents/5080/The_Connected_Home_Ingress_Test_Equipment_Training.pdf"), "Presentación · SCTE y VIAVI (2022)", "Supervisor y adm."],
				["10", "Cierre con el cliente y firma", L("Installation Fundamentals, sec. 2.3", "https://sites.google.com/view/tt-flowtechspot/installation-fundamentals") + L("FLOW · Customer Service", "https://sites.google.com/view/tt-flowtechspot/customer-service"), "Texto · FLOW", "Adm. y técnico"],
				["11", "Cierre en la app QSG Campo", "Video QSG 09 · biblioteca QSG (carpeta 09-Cierre-y-evidencia-QSG-Campo)", "Video propio · QSG", "Adm. y técnico"],
			],
		)
	)
	c.append("<h2>3. Material complementario abierto</h2>")
	c.append(
		tabla(
			["Recurso", "Qué aporta", "Autor"],
			[
				[L("Stop Ingress in its Tracks (4:55)", "https://video.viavisolutions.com/detail/videos/signal-leakage/video/1730746600433644148/stop-ingress-in-its-tracks-with-affordable-leakage-solution-for-even-the-smallest-vehicles"), "Detección de fugas desde el vehículo.", "VIAVI"],
				[L("Home Leakage Test Kit (2:37)", "https://video.viavisolutions.com/detail/videos/signal-leakage/video/5856065373001/home-leakage-test-kit.-tighten-up-home-coaxial-network---viavi-solutions"), "Kit para revisar fugas en la red coaxial de la casa.", "VIAVI"],
				[L("Introducing the DSP-TDR (2:01)", "https://video.viavisolutions.com/detail/videos/signal-leakage/video/6057643772001/introducing-the-dsp-tdr-–-simpler-faster-and-more-precise-cable-break/fault-finding"), "Ubicación de cortes y fallas en el cable.", "VIAVI"],
				[L("Testing Complete Network Frequency Transmission Performance (2:14)", "https://video.viavisolutions.com/detail/videos/signal-leakage/video/5541644709001/testing-complete-network-frequency-transmission-performance"), "Prueba de desempeño en frecuencia.", "VIAVI"],
				[L("SWTA swivel tap adapter (video)", "https://www.ppc-online.com/hubfs/VIDEOS/swta-install_video_rev2.mp4"), "Adaptador para conectar en el tap.", "PPC"],
				[L("VIAVI: entrenamiento OneExpert CATV", "https://www.viavisolutions.com/en-uk/node/113609"), "Uso del medidor de señal si la cuadrilla lo tiene.", "VIAVI"],
				[L("ModemGuides: niveles del módem, SNR y T3/T4", "https://www.modemguides.com/blogs/modemguides-blog/modem-signal-levels-snr-power-t3-t4-timeouts-explained"), "Explicación sencilla de niveles para técnicos nuevos.", "ModemGuides"],
			],
		)
	)
	c.append("<h2>4. Normas y requisitos aplicables en Puerto Rico</h2>" + NORMAS_PR)
	c.append("<h2>5. Plataformas formales evaluadas (de pago o con registro)</h2>")
	c.append(
		tabla(
			["Plataforma", "Qué cubre", "Formato / idioma", "Costo", "Reutilización"],
			[
				[L("SCTE · BPI Fundamentals", "https://account.scte.org/education/course-offerings/course-catalog/broadband-premises-installation-bpi-fundamentals/") + L("SCTE · certificación BPI", "https://www.scte.org/bpi/"), "La referencia del sector, y Liberty la exige. Acometida aérea y subterránea, tierra, cableado interior, mediciones, video, datos y voz; incluye simulador.", "En línea, 1 año; 2 días presenciales opcionales · inglés", "Examen USD 50 a 85; guía impresa USD 149; curso con precio aparte", '<span class="no">No</span>'],
				[L("NCTI · Installer", "https://ncti.com/installer/"), "El end-to-end HFC más completo: escaleras, herramientas, acometida, tierra, divisores, conectorización, diagnóstico.", "En línea, 30 horas · inglés", "USD 715 + 125 examen", '<span class="no">No</span>'],
				[L("NCTI · Broadband Digital Installer", "https://ncti.com/broadband-digital-installer"), "Módem DOCSIS 3.1, parámetros RF, VoIP, cableado interior.", "En línea, 18 horas · inglés", "USD 740", '<span class="no">No</span>'],
				[L("SATSAID · Experto en Redes HFC", "https://www.cursosatsaid.tv/portal/display_curso.php?n=EHFC"), "Dispositivos, conectores y herramientas, ruido, instalación domiciliaria, DOCSIS y cable módem, seguridad.", "En línea, unas 8 semanas · <b>español</b>", "Pago (moneda argentina)", '<span class="no">No</span> (derechos reservados)'],
				[L("CommScope Infrastructure Academy", "https://www.commscopetraining.com/courses/broadband"), "Fundamentos HFC/FTTx, coaxial, tierra. Teórico.", "En línea", "USD 25 a 295 por curso", '<span class="no">No</span>'],
				[L("SCTE Europa", "https://www.thescte.eu/training"), "Catálogo técnico (DOCSIS 3.1, fibra, Wi-Fi).", "En línea · inglés", "Gratis para miembros", '<span class="no">No</span>'],
			],
		)
	)
	c.append("<h2>6. Propiedad intelectual y uso permitido</h2>")
	c.append(
		tabla(
			["Fuente", "Uso permitido"],
			[
				["FLOW Tech Spot", LIC_OK + ". El sitio no declara licencia; para copiar texto o fotos, pedir permiso."],
				["PPC Broadband", LIC_PERM + ". Los videos están abiertos en su sitio, pero no dice que se puedan editar ni redistribuir."],
				["VIAVI", LIC_PERM + "."],
				["OSHA", LIC_OK + ". Gobierno de EE. UU.; verificar contenido de terceros antes de copiar."],
				["FOA (Fiber Optic Association)", LIC_PERM + ". Su política permite enlazar; para copiar hay que escribir a info@foa.org."],
				["SCTE (presentación de ingreso)", LIC_PERM + ". Tiene copyright de SCTE 2021 y VIAVI 2020."],
				["Plataformas de pago (SCTE, NCTI, SATSAID, CommScope)", '<span class="no">No se puede descargar ni redistribuir.</span> Se accede con inscripción o licencia corporativa.'],
			],
		)
	)
	c.append(
		'<div class="box"><b>Por qué no se descargaron videos:</b> los videos de YouTube no se pueden bajar desde el servidor de trabajo, porque YouTube pide verificar que no es un robot, y ese control no se debe saltar. '
		"Los sitios cerrados o de pago no se descargan, aunque el uso sea educativo: hacerlo viola sus términos y la propiedad intelectual.</div>"
	)
	c.append("<h2>7. Brechas y próximos pasos</h2><ul>"
		"<li><b>Acometida completa en video:</b> no existe abierta. Opciones: convertir la guía de FLOW en clips ilustrados en español (pidiendo permiso), o grabar con el celular una instalación de una cuadrilla QSG para que se edite en clips.</li>"
		"<li><b>Idioma:</b> todo está en inglés. Se puede subtitular o resumir en español en la página QSG.</li>"
		"<li><b>Permisos:</b> enviar un correo a PPC y VIAVI pidiendo autorización para usar sus videos en la plataforma interna de QSG con subtítulos en español.</li>"
		"<li><b>Certificación:</b> inscribir a 2 o 3 técnicos líderes en SCTE BPI (Liberty la exige) y pedir cotización corporativa a SCTE y NCTI.</li>"
		"<li><b>Google Drive:</b> sin conectar todavía; los archivos están en la carpeta del proyecto capacitacion-qsg.</li></ul>")
	c.append("<h2>Anexo A. Videos de YouTube con licencia Creative Commons evaluados y descartados</h2>")
	c.append("<p>Se encontraron con el filtro Creative Commons de YouTube. Se descartaron como base por no ser entrenamiento formal (canales personales, narración en ruso, calidad desigual). Quedan como referencia.</p>")
	cc = [
		("#cabletoday LADDERS", "43YMaqYGVzk"), ("#cabletoday Coax Cables RG6 RG11", "CGiDGvmBiGg"), ("#cabletoday Fittings RG6, RG11, RG59", "U58SzcXefy8"),
		("Cable Tips; How to prep coaxial wire (Gr8jasmo)", "8vdrdGwe1eU"), ("Falcon Technologies: Snap-N-Seal Compression F-Type", "lQl5pWWL-z8"),
		("Master Coax Termination W/ Klein Coax Install Kit", "2x6Xjdku_24"), ("Cable in USA Step By Step New Install, parte 1", "aRLDNyElZi8"),
		("... parte 2", "NqfjF4k20vM"), ("... parte 3", "HUHBXXIR0fo"), ("... parte 4", "RkfVfgGspFQ"), ("#cabletoday Ground Block, Ground Wire", "YJXSxAevAnE"),
		("#cabletoday Splitters", "M8Lhbg-M93E"), ("#cabletoday MOCA filters", "_sZ8iYhEzoc"), ("#cabletoday Amplifier", "oWx1IvnCvxs"),
		("#cabletoday ROCAS, Wall Plate, Covers", "T4xxTEtclYw"), ("Ultimate Tech Hub: Coax Cable Facts, Safety & Dos & Don'ts", "jDZ7vGFwiEg"), ("Ultimate Tech Hub: Cable Modem How To", "D1S2ORps2RU"),
	]
	c.append(tabla(["Video", "Enlace"], [[e(t), L("ver", YT + i)] for t, i in cc]))
	c.append("<h2>Anexo B. Otras fuentes revisadas</h2><ul>"
		"<li>Internet Archive y Wikimedia Commons: no se encontró material de instalación HFC.</li>"
		"<li>CommScope VideoHub (" + L("videohub.commscope.com", "https://videohub.commscope.com/") + "): sobre todo fibra; nada de acometida coaxial.</li>"
		"<li>Klein Tools (" + L("kleintools.com/videos", "https://www.kleintools.com/videos") + "): demostraciones de herramientas, nada de coaxial.</li>"
		"<li>Viasat eGuide (" + L("eguide.field.viasat.com", "https://eguide.field.viasat.com/video-category/cabling/") + "): enfoque satelital; útil solo para la guía de tierra.</li>"
		"<li>Comunidad El Puente, curso de mediciones HFC: el sitio no permite consultas automáticas; no se pudo revisar.</li></ul>")
	return doc("Marco HFC end-to-end", "Fuentes abiertas y gratuitas para el equipo técnico y el administrativo · Liberty Puerto Rico", "".join(c))


# ===================================================================== FTTH
def ftth():
	c = []
	c.append(
		'<h2>Resumen ejecutivo</h2><div class="exec"><ul>'
		"<li><b>Objetivo:</b> la misma visión end-to-end que en HFC, ahora para una instalación FTTH de abonado (red GPON de Liberty PR).</li>"
		"<li><b>Hallazgo principal:</b> FTTH tiene mejores fuentes abiertas que HFC. La <b>Fiber Optic Association (FOA)</b>, escuela sin fines de lucro, publica gratis un manual FTTH <b>en español</b>, un curso básico en español (Fiber U) y guías paso a paso en PDF de empalme, conectores y pruebas.</li>"
		"<li><b>Videos con permiso explícito:</b> <b>Corning</b> declara que sus videos de instalación se pueden descargar y usar para entrenar a grupos. Incluyen la instalación del conector endurecido OptiTap en el drop y en el terminal.</li>"
		"<li><b>Estándar real de un operador:</b> el <b>UTOPIA Fiber Installation Standard</b> (EE. UU., 2024) es un documento público de 9 páginas con normas de drop, instalación en casa, presentación del técnico y reportes. Es un buen modelo para el estándar QSG.</li>"
		"<li><b>Mediciones:</b> FOA y EXFO tienen guías abiertas de medición con medidor PON. El rango de la PMO es de −8 a −25 dBm a 1490 nm.</li>"
		"<li><b>Brechas:</b> FLOW (Liberty Latin America) no tiene contenido FTTH abierto, y no hay un video abierto de la instalación de la ONT.</li>"
		"<li><b>Decisión pendiente:</b> (1) página QSG en español con los 12 pasos; (2) descargar y subtitular los videos de Corning (permitido); (3) ambas.</li>"
		"</ul></div>"
	)
	c.append("<h2>1. Fuente principal en español: FOA</h2>")
	c.append(
		tabla(
			["Recurso", "Contenido"],
			[
				[L("Manual FTTH en español (índice)", "https://www.thefoa.org/tech/ref/appln/FTTH-ESP/index.html"), "Introducción, arquitecturas, PON, diseño, instalación, pruebas, casos, gestión de proyectos."],
				[L("Instalación de Fibra Hasta el Hogar", "https://www.thefoa.org/tech/ref/appln/FTTH-ESP/Instalacion%20de%20Fibra%20Hasta%20el%20Hogar.html"), "Instalación de la red y de la acometida."],
				[L("Prueba de las redes FTTH", "https://www.thefoa.org/tech/ref/appln/FTTH-ESP/Prueba%20de%20las%20redes%20FTTH.html"), "Pruebas de potencia y pérdida."],
				[L("Fiber U: Fibra Óptica Básica (curso en español)", "https://www.fiberu.org/Basic-ESP/index.html"), "10 lecciones con videos de la FOA y examen. Clave: L1 seguridad, L6 cables, L7 terminación y empalme, L8 prueba, L10 instalación."],
				[L("Guía de referencia FOA en español", "https://www.thefoa.org/ESP/index.htm"), L("Instalación", "https://www.thefoa.org/ESP/Instalacion.htm") + L("Conectores y empalmes", "https://www.thefoa.org/ESP/Conectores.htm") + L("Prueba", "https://www.thefoa.org/ESP/Prueba.htm")],
			],
		)
	)
	c.append("<h2 style='page-break-before:always'>2. Secuencia end-to-end de la instalación FTTH</h2>")
	c.append(
		tabla(
			["#", "Paso", "Fuente abierta", "Tipo / autor", "Para"],
			[
				["1", "Qué es FTTH/GPON y cómo llega al cliente", L("FOA: Introducción a la FTTH", "https://www.thefoa.org/tech/ref/appln/FTTH-ESP/Introduccion%20a%20la%20FTTH.html") + L("FOA: Arquitecturas FTTH", "https://www.thefoa.org/tech/ref/appln/FTTH-ESP/Arquitecturas%20de%20Red%20FTTH.html") + L("FOA: FTTH PONs", "https://www.thefoa.org/tech/ref/appln/FTTH-ESP/FTTH%20PONs.html") + L("FOA Lecture 64: PONs (video)", "https://youtu.be/lgNJRAPsLTg"), "Texto en español y video · FOA", "Adm. y técnico"],
				["2", "Seguridad con fibra y en altura", L("Fiber U L1: Introducción, estándares, seguridad", "https://www.fiberu.org/Basic-ESP/LP1.html") + L("FOA Lecture 2: Safety (video)", YT + "qhqclWudh7s") + L("OSHA: Ladder Safety (video)", YT + "GuPdykagKMg"), "Texto y video · FOA y OSHA", "Técnico"],
				["3", "Drop: tipos de cable y tendido", L("FOA: Drop Cables for Customer Premises FTTH", "https://www.thefoa.org/tech/ref/install/Drop_Cables_FTTH.html") + L("FOA: FTTH Installation", "https://www.thefoa.org/tech/ref/appln/FTTH-install.html") + L("FOA Lecture 66: FTTH Installation and Test (video)", "https://youtu.be/EOme0pvgnoc") + L("UTOPIA Fiber Installation Standard (PDF)", "https://utopiafiber.com/wp-content/uploads/2024/12/Appendix-A-UTOPIA-Installation-Standard-2024.10.16.pdf"), "Texto, video y estándar · FOA y UTOPIA", "Técnico"],
				["4", "Conector endurecido (OptiTap) en drop y terminal", L("Corning: OptiTap en drop ROC", YT + "IdGh3LtEIqI") + L("Corning: OptiTap en drop SST", YT + "B3x8ew89Wrg") + L("Corning: OptiTap en drop ROC 900", YT + "Xzer4n9VRh0") + L("Corning: OptiTap en MultiPort Terminal", YT + "P44rmrIAWV4"), "Video · Corning (uso para entrenamiento permitido)", "Técnico"],
				["5", "Empalme por fusión y mecánico", L("FOA: guía VHO de fusión (PDF)", "https://www.thefoa.org/tech/ref/termination/VHO-fuspl/VHO-Splice-fusion.pdf") + L("FOA: guía VHO de empalme mecánico (PDF)", "https://www.thefoa.org/tech/ref/termination/VHO-mechspl/VHO-Splice-mech.pdf") + L("FOA: Fusion Splicing (video)", YT + "kfYNj3nIPV8") + L("FOA: Mechanical Splicing (video)", YT + "haey8XdILf0") + L("Fiber U: curso de empalme", "https://www.fiberu.org/Splicing/index.html"), "PDF, video y curso · FOA", "Técnico"],
				["6", "Conectores de campo (prepulidos o splice-on)", L("FOA: guía VHO prepulidos/SOC (PDF)", "https://www.thefoa.org/tech/ref/termination/VHO-PPSterm/VHO-PPSterm.pdf") + L("FOA: Unicam (video)", YT + "vloHJnHmjnY"), "PDF y video · FOA", "Técnico"],
				["7", "Inspección y limpieza de conectores", L("Fiber U: MiniCourse Inspect & Clean", "https://www.fiberu.org/Inspect_Clean/index.html") + L("FOA Lecture 57: Inspection and Cleaning (video)", "https://youtu.be/Fhq9E4xthmA") + L("FOA: Inspección con microscopio (video)", "http://youtu.be/IyumH8CiUPQ"), "Curso y video · FOA", "Técnico"],
				["8", "Instalación dentro de la casa (roseta y recorrido)", L("FOA: FTTH Customer Premises Installation", "https://www.thefoa.org/tech/ref/appln/FTTH-prem.html") + L("UTOPIA: instalación en casa (sec. 3)", "https://utopiafiber.com/wp-content/uploads/2024/12/Appendix-A-UTOPIA-Installation-Standard-2024.10.16.pdf"), "Texto y estándar · FOA y UTOPIA", "Técnico"],
				["9", "Instalación de la ONT", L("FOA: Installation of FTTH active equipment", "https://www.thefoa.org/tech/ref/install/Installation%20of%20FTTH%20active%20equipment.html") + L("FOA Lecture 68: PON Demonstration (video)", "https://youtu.be/oQPMlyCnf8s"), "Texto y video · FOA", "Técnico"],
				["10", "Medición de potencia con medidor PON", L("FOA: OPM and PON meters (PDF)", "https://www.foa.org/tech/ref/install/OPM%20and%20PON%20meters.pdf") + L("FOA: Prueba de las redes FTTH", "https://www.thefoa.org/tech/ref/appln/FTTH-ESP/Prueba%20de%20las%20redes%20FTTH.html") + L("EXFO: PPM-350D, cómo probar redes PON (entrenamiento multimedia)", "https://www-int.exfo.com/de/resources/technical-documentation/multimedia-trainings/ppm-350d-ftth-pon-networks/?lang=en") + L("EXFO: póster FTTx PON testing", "https://www.exfo.com/es/recursos/documentacion-tecnica/reference-posters/fttx-pon-testing/?lang=en") + L("FOA Lecture 14: Testing Optical Power (video)", YT + "Fd9RhGafSWE"), "PDF, video y guía · FOA y EXFO", "Técnico y supervisor"],
				["11", "Diagnóstico de fallas", L("FOA: Troubleshooting FTTH", "https://www.thefoa.org/tech/ref/install/Troubleshooting_FTTH.html") + L("FOA: Advanced GPON Fault-Finding Manual 2026 (PDF)", "https://www.thefoa.org/tech/ref/install/Advanced%20GPON%20Fault-Finding%20Manual%202026.pdf") + L("FOA: ejemplos de malas instalaciones FTTH", "https://www.thefoa.org/tech/ref/install/Bad_FTTH.html") + L("FOA: malas instalaciones aéreas", "https://www.thefoa.org/tech/ref/install/Bad_Aerial.html"), "Texto y manual · FOA", "Técnico y supervisor"],
				["12", "Cierre, reporte y app QSG", L("UTOPIA: requisitos de reporte (sec. 1 y 3)", "https://utopiafiber.com/wp-content/uploads/2024/12/Appendix-A-UTOPIA-Installation-Standard-2024.10.16.pdf") + "<br>Video QSG 09 · biblioteca QSG (09-Cierre-y-evidencia-QSG-Campo)", "Estándar y video propio", "Adm. y técnico"],
			],
		)
	)
	c.append("<h2>3. Material complementario abierto</h2>")
	c.append(
		tabla(
			["Recurso", "Qué aporta", "Autor"],
			[
				[L("Fiber U: curso FTTx (6 partes)", "https://www.fiberu.org/FTTX/index.html"), "Arquitecturas, estándares, instalación y prueba; ejercicio de diseño.", "FOA"],
				[L("Fiber U: Basic Skills Lab", "https://www.fiberu.org/Basic%20Skills%20Lab/index.html"), "Laboratorio práctico: herramientas, preparación, empalme, terminación, prueba.", "FOA"],
				[L("Fiber U: Fiber Optic Testing", "https://www.fiberu.org/FOtest/index.html"), "Curso de pruebas.", "FOA"],
				[L("Fiber U: The Mysterious dB", "https://www.fiberu.org/dB/index.html"), "Qué es el dB y el dBm, para técnicos y administrativos.", "FOA"],
				[L("Fiber U: Connector Identification", "https://www.fiberu.org/ConnectorID/index.html"), "Identificar conectores (SC/APC, etc.).", "FOA"],
				[L("FOA: guía VHO de preparación de cable (PDF)", "https://www.thefoa.org/tech/ref/cable/VHO-cable/VHO-cables.pdf"), "Preparación del cable paso a paso.", "FOA"],
				[L("FOA: guía VHO de OTDR (PDF)", "https://www.thefoa.org/tech/ref/testing/OTDR/VHO-OTDR/VHO-OTDR.pdf"), "Uso del OTDR (reparación).", "FOA"],
				[L("FOA: guía VHO de pérdida por inserción (PDF)", "https://www.thefoa.org/tech/ref/testing/test/VHO-IL/VHO-ILtest.pdf"), "Medición de pérdida.", "FOA"],
				[L("FOA Lecture 63: FTTH Architectures (video)", "https://youtu.be/MzhXWafuTiU"), "Dónde están los splitters.", "FOA"],
				[L("FOA Lecture 16: Insertion Loss Testing (video)", YT + "LW1QtChMmJ0"), "Pérdida de un enlace.", "FOA"],
				[L("FOA Lecture 17: OTDR Testing (video)", YT + "0h_KHvl0AxI"), "OTDR para supervisores y reparación.", "FOA"],
				[L("Corning: canal de videos de instalación", "https://www.youtube.com/user/corningcablesystems"), "Todos los videos de productos Corning.", "Corning"],
				[L("Corning: conectores OptiTap y OptiTip", "https://www.corning.com/optical-communications/worldwide/en/home/products/hardened-connectors.html"), "Ficha del sistema de conectores endurecidos.", "Corning"],
				[L("AFL: FASTConnect (video)", "https://learn.aflglobal.com/mdus/video-instructions-for-fastconnect-lc-st-and-sc-connectors-on-2-or-3mm-cable"), "Otro conector de campo común.", "AFL"],
				[L("AFL: limpieza en seco y húmedo-seco", "https://learn.aflglobal.com/test-inspection/dry-and-wet-to-dry-cleaning-of-optical-connectors"), "Técnica de limpieza.", "AFL"],
				[L("VIAVI: Inspect Before You Connect, Ep. 4", "https://video.viavisolutions.com/detail/videos/inspect-before-you-connect_/video/5662282204001/viavi-inspect-before-you-connect:-episode-4---the-importance-of-inspecting-new-fiber-connectors"), "Hasta un conector nuevo puede venir sucio.", "VIAVI"],
				[L("VIAVI + Sumitomo: empalme por fusión", "https://video.viavisolutions.com/detail/video/1796700894089027763/learn-how-to-perform-a-fusion-splice-with-sumitomo-and-viavi"), "Empalme y verificación.", "VIAVI"],
			],
		)
	)
	c.append("<h2>4. Valores de referencia QSG / PMO</h2>")
	c.append(
		tabla(
			["Medición", "Rango", "Fuente"],
			[
				["Potencia recibida en la ONT a 1490 nm", "−8 a −25 dBm", "PMO (la valida la app QSG Campo)"],
				["Pérdida por empalme de fusión", "≤ 0,10 dB", "Referencia de la industria; confirmar con Liberty"],
				["Diferencia entre CTO y roseta", "≤ 1,5 dB", "Referencia de la industria; confirmar con Liberty"],
				["Conectores", "Solo APC con APC; inspeccionar, limpiar, inspeccionar y conectar", "Práctica FOA, IEC 61300-3-35"],
			],
		)
	)
	c.append("<h2>5. Normas y requisitos aplicables en Puerto Rico</h2>" + NORMAS_PR)
	c.append("<h2>6. Plataformas formales evaluadas (de pago o presenciales)</h2>")
	c.append(
		tabla(
			["Plataforma", "Qué cubre", "Formato / idioma", "Costo", "Reutilización"],
			[
				[L("Lightera Academy (ex Furukawa): FCP Fibras Ópticas", "https://academy.latam.lightera.com/es/"), "Instalación de drop, empalmes, medición, seguridad, práctica. Centros en Colombia, México y otros.", "Presencial y en línea, 24 horas · español y portugués", "Pago (algunos cursos de planeación gratis)", '<span class="no">No</span>'],
				[L("Corning: Fiber Broadband Technician (CFBT)", "https://www.corning.com/optical-communications/worldwide/en/home/training-and-events/training-programs/fiber-optic-training.html"), "5 días prácticos en Charlotte (EE. UU.): empalme, conectorización, prueba y activación.", "Presencial · inglés", "No publicado", '<span class="no">No</span>'],
				[L("Fiber Broadband Association: OpTIC Path", "https://fiberbroadband.org/education-and-certification/fba-optic-path/"), "Certificación de instalador FTTH, hasta 144 horas, incluida la instalación en casa del cliente.", "Presencial en colegios técnicos de EE. UU. · inglés", "Pago", '<span class="no">No</span>'],
				[L("CommScope Infrastructure Academy", "https://www.commscopetraining.com/courses/broadband"), "FTTx: sistemas ópticos, cables y conectores, arquitecturas, presupuesto de pérdida.", "En línea", "USD 25 a 295", '<span class="no">No</span>'],
				[L("Fibremex (México)", "https://fibremex.com/fibra-optica/views/Cursos/cursos-fibra-optica.php"), "Cursos de fibra óptica.", "Español", "No se pudo leer la página", "Sin dato"],
			],
		)
	)
	c.append("<h2>7. Propiedad intelectual y uso permitido</h2>")
	c.append(
		tabla(
			["Fuente", "Uso permitido"],
			[
				["Corning, videos de instalación", '<span class="ok">Descarga y uso para entrenamiento permitidos.</span> Texto de Corning: "You can download and create your own personal library or use for training purposes with a wider audience." ' + L("Fuente", "https://www.corning.com/optical-communications/worldwide/en/home/training-and-events/training-programs.html")],
				["FOA y Fiber U", LIC_PERM + ". Su política permite enlazar; para copiar hay que escribir a info@foa.org. Uso educativo no comercial, con crédito a la FOA."],
				["UTOPIA Fiber", LIC_OK + ". Documento público; citar como referencia."],
				["EXFO, VIAVI y AFL", LIC_PERM + "."],
				["OSHA", LIC_OK + ". Gobierno de EE. UU."],
				["Plataformas de pago", '<span class="no">No se puede descargar ni redistribuir.</span>'],
			],
		)
	)
	c.append(
		'<div class="box"><b>Nota sobre Corning:</b> aunque Corning permite descargar sus videos, están alojados en YouTube, que bloquea la descarga desde el servidor de trabajo. '
		"Se pueden bajar desde un computador de QSG, o pedir los archivos a Corning, y luego editarlos con subtítulos en español.</div>"
	)
	c.append("<h2>8. Brechas y próximos pasos</h2><ul>"
		"<li><b>Contenido de Liberty:</b> FLOW Tech Spot (Liberty Latin America) solo cubre HFC; no hay material FTTH abierto del grupo Liberty.</li>"
		"<li><b>ONT:</b> no hay un video abierto de la instalación de la ONT. Lo cubren la guía de la FOA y el video QSG 05 de la biblioteca QSG; lo ideal es grabar una instalación de una cuadrilla QSG.</li>"
		"<li><b>Videos de Corning:</b> se pueden descargar y subtitular en español con crédito a Corning; falta tu aprobación y que se bajen desde un computador.</li>"
		"<li><b>Estándar QSG:</b> usar el estándar de UTOPIA como modelo para redactar el estándar de instalación FTTH de QSG para Liberty PR.</li>"
		"<li><b>Certificación:</b> Lightera Academy tiene centros en Colombia, en español, como opción presencial.</li>"
		"<li><b>Google Drive:</b> sin conectar todavía; los archivos están en la carpeta del proyecto capacitacion-qsg.</li></ul>")
	return doc("Marco FTTH end-to-end", "Fuentes abiertas y gratuitas para el equipo técnico y el administrativo · Liberty Puerto Rico", "".join(c))


def main(out):
	out = Path(out)
	out.mkdir(parents=True, exist_ok=True)
	tmp = Path(tempfile.mkdtemp())
	with sync_playwright() as p:
		br = p.chromium.launch(executable_path="/opt/pw-browsers/chromium" if Path("/opt/pw-browsers/chromium").is_file() else None)
		for nombre, fn in [("Marco-HFC-end-to-end-QSG.pdf", hfc), ("Marco-FTTH-end-to-end-QSG.pdf", ftth)]:
			f = tmp / "r.html"
			f.write_text(fn(), encoding="utf-8")
			pg = br.new_page()
			pg.goto(f.as_uri())
			pg.pdf(path=str(out / nombre), format="Letter", print_background=True,
				   display_header_footer=True, header_template="<span></span>",
				   footer_template="<div style='font-size:7px;width:100%;text-align:center;color:#5a6680'>QSG · <span class='pageNumber'></span> de <span class='totalPages'></span></div>")
			pg.close()
			print("ok", nombre)
		br.close()


if __name__ == "__main__":
	main(sys.argv[1])
