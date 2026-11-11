# Biblioteca de capacitación QSG · FTTH y HFC

Material de capacitación de campo para cuadrillas y contratistas de QSG que instalan servicios FTTH y HFC para Liberty Puerto Rico. Está organizado por actividad, en el mismo orden en que se hace el trabajo.

## Cómo está organizada

| Carpeta | Qué contiene |
|---|---|
| 00-Inicio | Este documento y el **Catálogo maestro** (Excel) con todo el material, los enlaces externos, los códigos de cierre y los rangos de medición |
| 01-Seguridad-en-campo | Obligatorio antes de cualquier otro módulo |
| 02-FTTH-Tendido-de-drop | De la CTO a la roseta |
| 03-FTTH-Empalme-por-fusion | Pelado, clivado, fusión y protección |
| 04-FTTH-Conectores-inspeccion-y-limpieza | Inspeccionar, limpiar, inspeccionar, conectar |
| 05-FTTH-Instalacion-de-ONT | Ubicación, conexión, serial, aprovisionamiento y velocidad |
| 06-FTTH-Medicion-de-potencia-optica | Medidor PON, interpretación y qué hacer fuera de rango |
| 07-HFC-Cable-coaxial-y-conectores-F | Preparación RG6, compresión, tap y bloque de tierra |
| 08-HFC-Niveles-de-senal | Downstream, MER/SNR y upstream |
| 09-Cierre-y-evidencia-QSG-Campo | Uso de la app con pantallas reales: estados, evidencia, firma y códigos |
| 10-Evaluaciones | Banco de preguntas y hoja de registro de capacitación |

Cada carpeta de actividad trae:

- **Video-QSG-NN.mp4**: video original QSG de unos 3 minutos (1080p).
- **Guia-QSG-NN.pdf**: guía de campo de 2 a 3 páginas con procedimiento, criterios, lista de verificación, códigos de cierre y autoevaluación.
- **Guion-video-NN.md**: texto de narración escena por escena, para grabar voz en off con un técnico o instructor de QSG.
- **Enlaces-de-referencia-NN.md**: videos y guías de fabricantes y asociaciones, solo como enlace.

## Ruta de capacitación sugerida

1. Técnico nuevo: módulos 01 y 09, y luego los de su tecnología (FTTH: 02 a 06; HFC: 07 y 08).
2. Aprobación: 80 % o más en las preguntas del módulo, registrado en *10-Evaluaciones*.
3. Repaso: cuando un técnico o contratista acumula retrabajos en el reporte de calificación de la PMO, repite el módulo de la actividad donde falló.

## Propiedad intelectual

- Todo lo que lleva la marca QSG (videos, guías, guiones, catálogo y evaluaciones) es **material original de QSG**, hecho a partir de los procedimientos y las pantallas de la PMO QSG.
- Los videos de terceros (Fiber Optic Association, OSHA, AFL, VIAVI, Corning, OFS y otros) **no se descargan ni se vuelven a subir ni se marcan con QSG**. Solo se enlazan desde el catálogo, que es lo que esos autores permiten. Por ejemplo, la política de la FOA permite enlazar sin permiso, pero copiar su material requiere su autorización.
- No se usa música, logos ni imágenes de terceros dentro de los videos QSG.
- Para incorporar un video de terceros a la biblioteca, se pide permiso por escrito al autor y se guarda el permiso en *00-Inicio*.

## Valores técnicos

Los rangos marcados **PMO** son los que valida la app QSG Campo (por ejemplo, potencia en ONT de −8 a −25 dBm, downstream de −7 a +7 dBmV, upstream de 35 a 51 dBmV, MER ≥ 35 dB). Los marcados **Referencia** son prácticas de la industria. El manual técnico vigente de Liberty Puerto Rico siempre prevalece; si un valor difiere, se actualiza el contenido y se regeneran los videos.

## Cómo se actualiza

El contenido está en el repositorio de la PMO (`capacitacion/contenido.py`). Se edita el texto y se ejecuta `python3 capacitacion/build.py <salida> <carpeta de pantallas>`; el script vuelve a generar todos los videos, guías y hojas de Excel con la marca QSG.
