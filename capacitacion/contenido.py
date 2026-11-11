"""Contenido de la biblioteca de capacitación QSG (FTTH y HFC).

Fuente de verdad para guías, guiones, videos y catálogo. Los rangos marcados
"PMO" salen de las plantillas de checklist de QSG PMO (qsg_pmo/install.py).
Los marcados "Referencia" son prácticas de la industria: se deben confirmar
contra el manual técnico vigente de Liberty Puerto Rico, que prevalece.
"""

YT = "https://www.youtube.com/watch?v="

# Licencias usadas en el catálogo
LIC_ENLACE = "Solo enlace (derechos del autor)"
LIC_FOA = "Solo enlace (FOA: permite enlazar; copiar requiere permiso)"
LIC_OSHA = "Solo enlace (gobierno de EE. UU.; verificar contenido de terceros antes de copiar)"

ACTIVIDADES = [
	{
		"num": "01",
		"carpeta": "01-Seguridad-en-campo",
		"titulo": "Seguridad en campo",
		"tecnologia": "FTTH y HFC",
		"duracion_video": "≈3 min",
		"objetivo": "Que cada técnico llegue, trabaje y se vaya sin lesiones, sin dañar la propiedad del cliente y sin poner en riesgo a terceros.",
		"epp": [
			"Casco con barbiquejo y chaleco reflectivo",
			"Gafas de seguridad (obligatorias al cortar o clivar fibra)",
			"Guantes dieléctricos o de trabajo según la tarea",
			"Botas con puntera y suela antideslizante",
			"Escalera de fibra de vidrio (nunca de aluminio cerca de líneas eléctricas)",
			"Arnés y línea de vida para trabajo en altura",
			"Conos y señalización para trabajo cerca de la vía",
			"Recipiente rotulado para residuos de fibra",
		],
		"pasos": [
			("Evalúa el sitio antes de bajar herramientas", "Mira líneas eléctricas, perros, tráfico, terreno blando y clima. Si hay riesgo que no puedes controlar, no trabajes: cierra con el código SEG."),
			("Señaliza el área", "Conos y chaleco si trabajas junto a la vía. El vehículo con luces de emergencia y estacionado de forma segura."),
			("Distancia a líneas eléctricas", "Mantén al menos 3 m (10 pies) de cualquier línea energizada, incluida la escalera y las herramientas. Trata toda línea como energizada."),
			("Escalera bien puesta", "Relación 4 a 1 (un pie de base por cada cuatro de altura), que sobresalga 1 m (3 pies) del punto de apoyo y amarrada. Siempre tres puntos de contacto."),
			("Trabajo en altura con arnés", "Por encima de la altura que defina el programa de seguridad, arnés anclado a un punto certificado. Nunca te ancles al cable de comunicaciones."),
			("Fibra: ojos y residuos", "Nunca mires el extremo de una fibra o un conector, aunque creas que está apagada. Los restos de fibra van al recipiente, nunca al piso ni a la ropa."),
			("Calor y lluvia", "En Puerto Rico el calor es un riesgo real: agua cada 15 a 20 minutos, sombra en las pausas. Con tormenta eléctrica se baja de la escalera y se suspende (código CLIMA)."),
			("Dentro de la casa", "Cubrebotas, pide permiso antes de perforar, verifica que no haya tubería ni cableado eléctrico detrás de la pared."),
			("Reporta todo incidente", "Cualquier casi-accidente se reporta al supervisor el mismo día. Reportar no se castiga; ocultar sí."),
		],
		"criterios": [
			"EPP completo visible en la foto de fachada o del área de trabajo",
			"Ninguna escalera ni herramienta a menos de 3 m de líneas energizadas",
			"Área limpia al terminar, sin restos de fibra ni de cable (foto obligatoria en la app)",
			"Toda suspensión por riesgo se cierra con código SEG o CLIMA, nunca como 'completada'",
		],
		"errores": [
			"Recostar la escalera en el cable de comunicaciones o en el poste sin amarrar",
			"Clivar fibra sin gafas o tirar los restos al piso",
			"Trabajar con tormenta eléctrica 'para no perder la orden'",
			"Perforar paredes sin revisar qué hay detrás",
		],
		"evidencia_app": [
			"Foto de fachada / número de la dirección",
			"Foto del área de trabajo limpia al terminar",
			"Código de cierre SEG o CLIMA si se suspende por riesgo",
		],
		"codigos": ["SEG", "CLIMA"],
		"preguntas": [
			("¿Cuál es la distancia mínima a una línea eléctrica energizada?", ["1 m", "2 m", "3 m (10 pies)", "No hay mínimo si uso guantes"], 2),
			("La relación correcta de la base de una escalera de extensión es:", ["1 a 1", "4 a 1", "2 a 1", "La que sea cómoda"], 1),
			("Empieza una tormenta eléctrica a mitad de la instalación. ¿Qué haces?", ["Termino rápido", "Bajo, suspendo y cierro con CLIMA", "Sigo si tengo guantes", "Llamo al cliente para que decida"], 1),
			("¿Dónde van los restos de fibra clivada?", ["Al piso", "Al bolsillo", "Al recipiente rotulado", "A la basura del cliente"], 2),
		],
		"videos": [
			("FOA Lecture 2: Safety When Working With Fiber Optics", YT + "qhqclWudh7s", "Fiber Optic Association", "Inglés", LIC_FOA, "Riesgos reales de la fibra: ojos, astillas, químicos. Base para la regla de gafas y recipiente."),
			("5 Things to Know about Ladder Safety", YT + "GuPdykagKMg", "OSHA", "Inglés", LIC_OSHA, "Inspección, ángulo y tres puntos de contacto."),
			("Electrocution: Work Safely with Ladders Near Power Lines", YT + "4QcctfnUeOM", "OSHA", "Inglés", LIC_OSHA, "Caso real de electrocución con escalera; refuerza la regla de 3 m."),
			("5 Ways to Prevent Workplace Falls", YT + "Qpowg5Ynh0w", "OSHA", "Inglés", LIC_OSHA, "Resumen de 41 segundos para charla de 5 minutos."),
			("Remembering Tim: A life lost to heat illness at work", YT + "o3ULhPd0KQg", "OSHA", "Inglés", LIC_OSHA, "Golpe de calor: síntomas y prevención. Muy relevante en Puerto Rico."),
			("Biblioteca de videos de OSHA", "https://www.osha.gov/video/", "OSHA", "Inglés / Español", LIC_OSHA, "Índice oficial; varios videos tienen versión en español."),
		],
	},
	{
		"num": "02",
		"carpeta": "02-FTTH-Tendido-de-drop",
		"titulo": "Tendido de drop óptico",
		"tecnologia": "FTTH",
		"duracion_video": "≈3 min",
		"objetivo": "Llevar el drop desde la CTO (caja terminal) hasta la roseta del cliente sin exceder el radio de curvatura, con herrajes correctos y un recorrido limpio y fotografiable.",
		"epp": [
			"Drop óptico del tipo y largo indicados en la orden",
			"Herrajes: abrazaderas de retención (tipo S o cuña), ganchos, grapas para drop",
			"Escalera de fibra de vidrio, arnés si aplica",
			"Taladro, broca y pasamuros con sello",
			"Etiquetas de identificación",
		],
		"pasos": [
			("Confirma puerto y CTO", "Verifica en la orden el ID de la CTO y el puerto asignado. Si la CTO no tiene puerto libre, no improvises: cierra con RED-SINPUERTO."),
			("Foto de la CTO antes", "Toma la foto 'antes' con la caja abierta y los puertos visibles, antes de tocar nada."),
			("Planifica el recorrido", "Ruta más corta y segura, lejos de líneas eléctricas, sin cruzar techos de terceros. Mide para no dejar exceso."),
			("Ancla en el poste", "Abrazadera de retención en el herraje del poste. El drop nunca se amarra directo al cable de la red."),
			("Respeta el radio de curvatura", "Nunca dobles el drop en ángulo. Regla práctica: radio mínimo de 10 veces el diámetro sin tensión y 20 veces con tensión (confirma la ficha del cable)."),
			("Tensión controlada", "Deja una flecha moderada en el vano. Sin tirones: tirar del drop puede romper la fibra sin que se vea por fuera."),
			("Anclaje en fachada y entrada", "Abrazadera en la fachada, lazo de goteo antes del pasamuros para que el agua no entre, y sello en el orificio."),
			("Recorrido interior", "Grapas cada 30 a 40 cm sin aplastar el cable, siguiendo esquinas y zócalos. Deja una reserva enrollada sin doblar en la roseta."),
			("Etiqueta en ambos extremos", "Etiqueta en la CTO y en la roseta con el número de cuenta u orden."),
			("Foto del recorrido y de la CTO después", "Recorrido completo del drop y la CTO cerrada con el puerto ocupado."),
		],
		"criterios": [
			"Drop anclado con herraje en poste y fachada, nunca amarrado al cable de red",
			"Sin dobleces visibles ni grapas que aplasten el cable",
			"Lazo de goteo y sello en el pasamuros",
			"Etiqueta en la CTO y en la roseta",
			"Fotos de CTO antes, CTO después y recorrido del drop (obligatorias en la app)",
		],
		"errores": [
			"Engrapar el drop con grapa de coaxial que lo aplasta",
			"Dejar el sobrante enrollado en un rollo apretado detrás de un mueble",
			"No dejar lazo de goteo: el agua entra por el drop a la casa",
			"Usar un puerto distinto al asignado sin actualizarlo en la orden",
		],
		"evidencia_app": [
			"Foto de CTO / splitter antes",
			"Foto de CTO / splitter después",
			"Foto del recorrido del drop",
		],
		"codigos": ["RED-SINPUERTO", "RED-CONSTR", "PERM"],
		"preguntas": [
			("La CTO asignada no tiene puertos libres. ¿Qué haces?", ["Uso el puerto de un vecino", "Cierro con RED-SINPUERTO", "Abro otra CTO cualquiera", "Dejo el drop sin conectar"], 1),
			("¿Para qué sirve el lazo de goteo antes del pasamuros?", ["Estética", "Que el agua no entre por el cable", "Dar reserva de fibra", "Ninguna"], 1),
			("¿Dónde se ancla el drop en el poste?", ["Al cable de la red", "En el herraje con abrazadera de retención", "Al poste con alambre", "Al transformador"], 1),
		],
		"videos": [
			("FOA Lecture 66: FTTH Network Installation and Test", "https://youtu.be/EOme0pvgnoc", "Fiber Optic Association", "Inglés", LIC_FOA, "Cómo se instala y prueba una red FTTH completa; contexto para el drop."),
			("FOA Lecture 8: Fiber Optic Installation", YT + "K1m8I7VzLF0", "Fiber Optic Association", "Inglés", LIC_FOA, "Buenas prácticas generales de instalación y manejo del cable."),
			("FOA: ejemplos de mala instalación aérea (fotos)", "https://www.thefoa.org/tech/ref/install/Bad_Aerial.html", "Fiber Optic Association", "Inglés", LIC_FOA, "Galería de errores reales. Útil para que el técnico reconozca qué no hacer."),
			("OFS: video de instalación de cableado drop FTTH y MDU", "https://www.cablinginstall.com/design-install/article/16472191/ofs-training-video-breaks-down-installation-of-ftth-mdu-drop-cabling-system", "OFS (vía Cabling Installation)", "Inglés", LIC_ENLACE, "Instalación de drop en edificios multifamiliares."),
			("Corning: resumen de instalación de cableado drop FTTH", "https://cablinginstall.com/design-install/cabling-installation/article/16478288/corning-video-provides-installation-overview-for-ftth-drop-cabling", "Corning (vía Cabling Installation)", "Inglés", LIC_ENLACE, "Recorrido de poste a casa con drop preconectorizado."),
		],
	},
	{
		"num": "03",
		"carpeta": "03-FTTH-Empalme-por-fusion",
		"titulo": "Empalme por fusión",
		"tecnologia": "FTTH",
		"duracion_video": "≈3 min",
		"objetivo": "Hacer empalmes de fusión con pérdida baja y repetible, protegidos y ordenados en la bandeja, con el dato de pérdida registrado.",
		"epp": [
			"Empalmadora de fusión calibrada (electrodos con vida útil vigente)",
			"Cortadora de precisión (clivadora) y peladora de fibra",
			"Alcohol isopropílico de 99 % y paños sin pelusa",
			"Protectores termocontraíbles (manguitos)",
			"Gafas de seguridad y recipiente para residuos",
		],
		"pasos": [
			("Prepara el puesto", "Superficie estable, limpia y a la sombra. Viento y polvo dañan el empalme. Haz una descarga de arco o calibración si la máquina lo pide."),
			("Coloca el manguito primero", "Pasa el protector termocontraíble por una de las fibras antes de cortar. Olvidarlo obliga a repetir todo."),
			("Pela el recubrimiento", "Retira el recubrimiento de 250 µm con la peladora, sin raspar el vidrio."),
			("Limpia con alcohol", "Un paso con paño y alcohol isopropílico. Desde aquí no toques la fibra desnuda."),
			("Clivado", "Corta con la clivadora a la longitud que indica la máquina. Un mal clivado es la causa número uno de pérdida alta."),
			("Coloca en la empalmadora", "Fibras en las ranuras en V sin tocar los electrodos. Cierra la tapa y deja que la máquina alinee."),
			("Revisa la imagen y la pérdida estimada", "Si la máquina rechaza el ángulo de corte o la pérdida supera el límite, repite desde el pelado."),
			("Protege el empalme", "Centra el manguito sobre el empalme y llévalo al horno. Espera a que enfríe antes de moverlo."),
			("Ordena en la bandeja", "Acomoda la fibra en la bandeja respetando el radio de curvatura, sin cruces ni tensión."),
			("Registra", "Anota la pérdida estimada. En la orden, toma la foto de la CTO o cierre con la bandeja ordenada."),
		],
		"criterios": [
			"Pérdida por empalme de fusión: objetivo ≤ 0,10 dB (Referencia; confirma con Liberty)",
			"Manguito centrado y contraído por completo",
			"Bandeja ordenada, sin fibras sueltas ni cruzadas",
			"Cero residuos de fibra en el sitio",
		],
		"errores": [
			"Olvidar el manguito antes de empalmar",
			"Volver a tocar la fibra después de limpiarla",
			"Usar una clivadora con la cuchilla gastada (girar o cambiar la cuchilla)",
			"Mover el empalme caliente fuera del horno",
		],
		"evidencia_app": [
			"Foto de CTO / splitter después (bandeja ordenada)",
			"Inspección y limpieza de conectores realizada",
		],
		"codigos": ["MAT", "RED-AVERIA"],
		"preguntas": [
			("¿Cuál es la causa más común de pérdida alta en un empalme?", ["El color de la fibra", "Mal clivado", "La marca del manguito", "La hora del día"], 1),
			("¿Cuándo se coloca el manguito termocontraíble?", ["Después de empalmar", "Antes de clivar, en una de las fibras", "No es necesario", "Al final del día"], 1),
			("La máquina estima 0,35 dB. ¿Qué haces?", ["Lo acepto", "Repito desde el pelado y clivado", "Caliento dos veces el manguito", "Cambio de puerto"], 1),
		],
		"videos": [
			("Fusion Splicing", YT + "kfYNj3nIPV8", "Fiber Optic Association", "Inglés", LIC_FOA, "Proceso completo paso a paso; corto y claro."),
			("Mechanical Splicing", YT + "haey8XdILf0", "Fiber Optic Association", "Inglés", LIC_FOA, "Alternativa mecánica para cuando no hay empalmadora."),
			("AFL Classroom: Fusion Splicing 101", "https://learn.aflglobal.com/afl-classroom/fusion-splicing-101", "AFL", "Inglés", LIC_ENLACE, "Fundamentos: pelado, limpieza, clivado y fusión."),
			("Mastering Fusion Splicing: AFL Fujikura 45S", "https://learn.aflglobal.com/youtube-all-videos/mastering-fusion-splicing-afl-fujikura-45s-comprehensive-guide", "AFL / Fujikura", "Inglés", LIC_ENLACE, "Guía de una empalmadora de campo común."),
			("Learn how to perform a Fusion splice with Sumitomo and VIAVI", "https://video.viavisolutions.com/detail/video/1796700894089027763/learn-how-to-perform-a-fusion-splice-with-sumitomo-and-viavi", "VIAVI / Sumitomo", "Inglés", LIC_ENLACE, "Empalme más verificación con equipo de prueba."),
		],
	},
	{
		"num": "04",
		"carpeta": "04-FTTH-Conectores-inspeccion-y-limpieza",
		"titulo": "Conectores ópticos: inspección y limpieza",
		"tecnologia": "FTTH",
		"duracion_video": "≈3 min",
		"objetivo": "Que ningún conector se conecte sin inspeccionar. La suciedad en la cara del conector es la causa principal de pérdida y de fallas repetidas.",
		"epp": [
			"Microscopio o sonda de inspección de conectores",
			"Limpiador tipo 'click' para conectores y adaptadores SC",
			"Paños sin pelusa y alcohol isopropílico (limpieza húmedo-seco)",
			"Tapas protectoras",
			"Conectores de campo (prepulidos) si hay que conectorizar",
		],
		"pasos": [
			("Inspecciona primero", "Antes de limpiar, mira la cara del conector con el microscopio. Así sabes si está sucio, rayado o dañado."),
			("Limpieza en seco", "Usa el limpiador tipo click o el paño en un solo sentido. Nunca soples el conector."),
			("Vuelve a inspeccionar", "Si sigue sucio, limpieza húmedo-seco: paño con alcohol y de inmediato la parte seca."),
			("Conecta solo si pasa", "Conecta únicamente cuando la zona del núcleo esté limpia. Un conector rayado o picado se reemplaza."),
			("Limpia también el adaptador", "El adaptador de la roseta o de la ONT se limpia con el limpiador de puerto."),
			("APC con APC", "Los conectores verdes (APC) solo se conectan con adaptadores verdes. Mezclar APC con UPC (azul) daña ambos."),
			("Tapas siempre", "Todo conector o puerto sin usar queda con su tapa puesta."),
			("Conector de campo", "Si conectorizas en sitio, sigue el procedimiento del fabricante y verifica con el medidor de potencia."),
		],
		"criterios": [
			"Inspección y limpieza registradas en la app ('Sí' en el checklist)",
			"Solo APC con APC",
			"Conectores sin uso con tapa",
			"Pérdida verificada con medición de potencia después de conectar",
		],
		"errores": [
			"Soplar el conector o limpiarlo con la camisa",
			"Quitar la tapa y dejar el conector expuesto mientras se hace otra tarea",
			"Conectar un conector APC en un adaptador UPC",
			"Limpiar sin inspeccionar después",
		],
		"evidencia_app": [
			"Inspección y limpieza de conectores realizada (Sí/No)",
			"Foto de roseta / punto de terminación óptica",
			"Reconectorización: foto del conector dañado antes y del nuevo instalado",
		],
		"codigos": ["COMP-OK", "MAT"],
		"preguntas": [
			("¿Cuál es el orden correcto?", ["Limpiar y conectar", "Inspeccionar, limpiar, inspeccionar, conectar", "Conectar y medir", "Soplar y conectar"], 1),
			("¿Qué color identifica un conector APC?", ["Azul", "Verde", "Negro", "Beige"], 1),
			("El conector tiene un rayón en el núcleo. ¿Qué haces?", ["Lo limpio más fuerte", "Lo reemplazo", "Lo conecto igual", "Le pongo alcohol"], 1),
		],
		"videos": [
			("FOA Lecture 57: Fiber Optic Connector Inspection and Cleaning", "https://youtu.be/Fhq9E4xthmA", "Fiber Optic Association", "Inglés", LIC_FOA, "Por qué se inspecciona y cómo se limpia."),
			("Visual Inspection of Connectors With A Microscope", "http://youtu.be/IyumH8CiUPQ", "Fiber Optic Association", "Inglés", LIC_FOA, "Cómo se ve un conector bueno y uno malo."),
			("VIAVI Inspect Before You Connect, Ep. 4: inspeccionar conectores nuevos", "https://video.viavisolutions.com/detail/videos/inspect-before-you-connect_/video/5662282204001/viavi-inspect-before-you-connect:-episode-4---the-importance-of-inspecting-new-fiber-connectors", "VIAVI", "Inglés", LIC_ENLACE, "Hasta un conector nuevo puede venir sucio."),
			("AFL: Dry and Wet-to-Dry Cleaning of Optical Connectors", "https://learn.aflglobal.com/test-inspection/dry-and-wet-to-dry-cleaning-of-optical-connectors", "AFL", "Inglés", LIC_ENLACE, "Limpieza en seco y húmedo-seco."),
			("Prepolished/Splice Connector Termination (Corning Unicam)", YT + "vloHJnHmjnY", "Fiber Optic Association", "Inglés", LIC_FOA, "Conector de campo prepulido."),
			("AFL: FASTConnect LC, ST and SC connectors", "https://learn.aflglobal.com/mdus/video-instructions-for-fastconnect-lc-st-and-sc-connectors-on-2-or-3mm-cable", "AFL", "Inglés", LIC_ENLACE, "Otro conector de campo común."),
		],
	},
	{
		"num": "05",
		"carpeta": "05-FTTH-Instalacion-de-ONT",
		"titulo": "Instalación de ONT",
		"tecnologia": "FTTH",
		"duracion_video": "≈3 min",
		"objetivo": "Dejar la ONT instalada, aprovisionada y con servicio verificado, en un lugar ventilado, con energía estable y con su serial registrado en la orden.",
		"epp": [
			"ONT asignada (serial registrado en la orden)",
			"Patch cord SC/APC",
			"Roseta óptica",
			"Medidor de potencia óptica PON",
			"Teléfono o laptop para prueba de velocidad",
		],
		"pasos": [
			("Ubicación con el cliente", "Acuerda el sitio: ventilado, cerca de un tomacorriente, lejos de humedad y fuera del piso."),
			("Instala la roseta", "Fija la roseta y acomoda la reserva de fibra sin dobleces. Toma la foto de la roseta."),
			("Mide antes de conectar la ONT", "Mide la potencia en el patch cord que irá a la ONT. Si está fuera de rango, el problema está antes: no conectes todavía (ver actividad 06)."),
			("Conecta la ONT", "Inspecciona y limpia el conector, conecta el patch cord APC y la energía."),
			("Espera la sincronización", "Verifica las luces de la ONT según el modelo (PON fija, sin LOS en rojo)."),
			("Registra el serial", "Foto de la etiqueta de la ONT con el serial visible. Verifica que coincide con el de la orden."),
			("Aprovisionamiento", "Confirma con el centro de soporte que la ONT quedó activa en el perfil correcto."),
			("Prueba de velocidad", "Por cable cuando sea posible. Registra los Mbps de bajada y toma la foto."),
			("Configura el Wi-Fi con el cliente", "Nombre de red y clave con el cliente presente. Explica dónde están las luces y qué significan."),
		],
		"criterios": [
			"Potencia recibida a 1490 nm entre −8 y −25 dBm (PMO)",
			"Serial de la ONT visible en foto y coincidente con la orden",
			"Prueba de velocidad registrada en Mbps",
			"ONT en lugar ventilado, no en el piso",
		],
		"errores": [
			"Conectar la ONT sin medir la potencia antes",
			"Instalar la ONT dentro de un mueble cerrado o en el piso",
			"Prueba de velocidad por Wi-Fi lejos de la ONT",
			"Serial de la foto distinto al de la orden",
		],
		"evidencia_app": [
			"Foto de roseta / punto de terminación óptica",
			"Potencia recibida en ONT a 1490 nm (−25 a −8 dBm)",
			"Foto de la ONT con serial visible",
			"Prueba de velocidad (Mbps de bajada) y su foto",
		],
		"codigos": ["COMP-OK", "COMP-PARCIAL", "RED-SINSENAL", "CLI-AUS"],
		"preguntas": [
			("¿Cuál es el rango aceptado de potencia a 1490 nm en la ONT?", ["0 a −5 dBm", "−8 a −25 dBm", "−30 a −40 dBm", "Cualquier valor"], 1),
			("¿Cuándo se mide la potencia?", ["Solo si el cliente se queja", "Antes de conectar la ONT", "Al día siguiente", "Nunca"], 1),
			("¿Qué debe verse en la foto de la ONT?", ["El cliente", "El serial", "La caja", "El router"], 1),
		],
		"videos": [
			("FOA Lecture 64: FTTH Passive Optical Networks (PONs)", "https://youtu.be/lgNJRAPsLTg", "Fiber Optic Association", "Inglés", LIC_FOA, "Qué es una red PON y dónde encaja la ONT."),
			("FOA Lecture 68: Fiber Optic PON Demonstration", "https://youtu.be/oQPMlyCnf8s", "Fiber Optic Association", "Inglés", LIC_FOA, "Demostración práctica de una PON funcionando."),
			("FOA Lecture 63: FTTH Network Architectures", "https://youtu.be/MzhXWafuTiU", "Fiber Optic Association", "Inglés", LIC_FOA, "Arquitecturas FTTH: dónde están los splitters."),
		],
	},
	{
		"num": "06",
		"carpeta": "06-FTTH-Medicion-de-potencia-optica",
		"titulo": "Medición de potencia óptica",
		"tecnologia": "FTTH",
		"duracion_video": "≈3 min",
		"objetivo": "Medir correctamente la potencia que llega al cliente, interpretar el resultado y saber qué hacer si está fuera de rango.",
		"epp": [
			"Medidor de potencia PON (mide 1490 nm y, si aplica, 1550 nm de video)",
			"Patch cords de referencia SC/APC limpios",
			"Microscopio y limpiadores",
		],
		"pasos": [
			("Usa un medidor PON", "En una red GPON usa un medidor PON que separa las longitudes de onda. Un medidor de banda ancha suma todo y da una lectura engañosa."),
			("Limpia antes de medir", "Inspecciona y limpia el conector y el adaptador del medidor. Un conector sucio da una lectura falsa."),
			("Mide en la CTO", "Mide en el puerto asignado de la CTO para tener la referencia de lo que entrega la red."),
			("Mide en la roseta", "Mide al final del drop. La diferencia con la CTO es la pérdida de tu instalación."),
			("Interpreta", "Entre −8 y −25 dBm está en rango (PMO). Más cerca de −25 hay poco margen: revisa conectores y curvas antes de cerrar."),
			("Si está bajo", "Busca curvas fuertes en el drop, conectores sucios o dañados, y empalmes. Corrige y vuelve a medir."),
			("Si no hay señal en la CTO", "El problema es de red, no de tu instalación: cierra con RED-SINSENAL y reporta."),
			("Registra el valor", "Escribe el valor en la app. Si está fuera de rango, la app no deja cerrar como completada."),
		],
		"criterios": [
			"1490 nm en la ONT: −8 a −25 dBm (PMO)",
			"Diferencia CTO a roseta: objetivo ≤ 1,5 dB (Referencia; confirma con Liberty)",
			"Valor registrado en la app con la foto del medidor cuando se pida",
		],
		"errores": [
			"Medir con un medidor de banda ancha en lugar de uno PON",
			"Medir sin limpiar los conectores",
			"Escribir un valor 'que pase' sin haber medido: el historial guarda hora y GPS",
			"Cerrar con poco margen sin revisar curvas",
		],
		"evidencia_app": [
			"Potencia recibida en ONT a 1490 nm (la app valida el rango)",
			"Medición después del cambio (reconectorización y reparación)",
		],
		"codigos": ["RED-SINSENAL", "RED-AVERIA"],
		"preguntas": [
			("Mides −27 dBm en la roseta y −18 dBm en la CTO. ¿Dónde está el problema?", ["En la red", "En tu drop, conectores o curvas", "En la ONT", "En el medidor"], 1),
			("¿Por qué se usa un medidor PON?", ["Es más barato", "Separa las longitudes de onda", "Pesa menos", "No importa"], 1),
			("No hay señal en el puerto de la CTO. ¿Qué código usas?", ["COMP-OK", "CLI-AUS", "RED-SINSENAL", "MAT"], 2),
		],
		"videos": [
			("FOA Lecture 14: Testing Optical Power", YT + "Fd9RhGafSWE", "Fiber Optic Association", "Inglés", LIC_FOA, "Cómo funciona un medidor de potencia y qué es el dBm."),
			("FOA Lecture 16: Insertion Loss Testing", YT + "LW1QtChMmJ0", "Fiber Optic Association", "Inglés", LIC_FOA, "Medición de pérdida de un enlace."),
			("FOA Lecture 49: Attenuation In A Fiber Optic Link", "https://youtu.be/QEzHQoTM1KM", "Fiber Optic Association", "Inglés", LIC_FOA, "De dónde sale la pérdida: fibra, conectores, empalmes, splitters."),
			("FOA Lecture 17: OTDR Testing", YT + "0h_KHvl0AxI", "Fiber Optic Association", "Inglés", LIC_FOA, "Para supervisores y técnicos de reparación."),
			("FOA: Testing FTTH PON networks (guía)", "https://www.thefoa.org/tech/ref/install/Testing%20FTTH%20PON%20network.html", "Fiber Optic Association", "Inglés", LIC_FOA, "Guía escrita de pruebas en redes PON."),
		],
	},
	{
		"num": "07",
		"carpeta": "07-HFC-Cable-coaxial-y-conectores-F",
		"titulo": "HFC: cable coaxial, conectores F y tierra",
		"tecnologia": "HFC",
		"duracion_video": "≈3 min",
		"objetivo": "Instalar el drop coaxial desde el tap con conectores de compresión bien preparados, bloque de tierra conectado y sin entradas de ruido.",
		"epp": [
			"Cable RG6 (o RG11 en drops largos) según la orden",
			"Peladora coaxial y herramienta de compresión",
			"Conectores F de compresión para exteriores",
			"Bloque de tierra y alambre de cobre de tierra",
			"Llave de torque para conector F",
		],
		"pasos": [
			("Foto del tap antes", "Toma la foto del tap con los puertos visibles antes de tocarlo."),
			("Prepara el cable", "Con la peladora: deja el dieléctrico y el conductor central a la medida que pide el conector (típico 1/4 x 1/4 de pulgada). Sin cortar la malla ni rayar el centro."),
			("Dobla la malla", "Dobla la malla hacia atrás de forma pareja, sin hilos sueltos que toquen el conductor central."),
			("Inserta y comprime", "Empuja el conector hasta que el dieléctrico quede al ras por dentro. El conductor central debe sobresalir poco. Comprime con la herramienta correcta."),
			("Ajuste en el tap", "Aprieta a mano y luego con la llave hasta el torque especificado (referencia de la industria ≈ 20–30 lb·pulg). Ni flojo ni pasado de fuerza."),
			("Puertos sin uso con terminador", "Todo puerto del tap sin usar lleva su terminador de 75 ohmios."),
			("Bloque de tierra", "Instala el bloque de tierra a la entrada de la casa, conectado a la tierra eléctrica del edificio con un alambre lo más corto posible."),
			("Lazo de goteo y sello", "Lazo de goteo antes de entrar a la casa y sello en el pasamuros."),
			("Foto del tap después", "Tap cerrado con el conector nuevo y los terminadores."),
		],
		"criterios": [
			"Conectores F comprimidos y ajustados (Sí en la app)",
			"Tierra del drop instalada (Sí en la app)",
			"Puertos sin uso del tap con terminador",
			"Fotos de tap antes y después",
		],
		"errores": [
			"Hilos de malla tocando el conductor central (corto o ruido)",
			"Conectores de rosca o de crimpar en exteriores",
			"Bloque de tierra sin conectar o conectado a una tubería de agua sin continuidad",
			"Dejar puertos del tap abiertos: entrada de ruido para todo el nodo",
		],
		"evidencia_app": [
			"Foto del tap antes",
			"Foto del tap después",
			"Tierra del drop instalada (Sí/No)",
			"Conectores F comprimidos y ajustados (Sí/No)",
		],
		"codigos": ["RED-SINPUERTO", "RED-SINSENAL", "MAT"],
		"preguntas": [
			("¿Qué va en un puerto del tap que no se usa?", ["Nada", "Un terminador de 75 ohmios", "Cinta aislante", "Un conector suelto"], 1),
			("¿Para qué sirve el bloque de tierra?", ["Amplificar señal", "Proteger contra descargas y cumplir el código eléctrico", "Decoración", "Dividir la señal"], 1),
			("¿Qué conector se usa en exteriores?", ["De rosca", "De crimpar", "De compresión", "Cualquiera"], 2),
		],
		"videos": [
			("Belden Snap & Seal: conector F de compresión en RG6", "https://www.showmecables.com/blog/post/how-to-install-belden-snap-and-seal-f-type-compression-connector-for-rg6", "ShowMeCables", "Inglés", LIC_ENLACE, "Preparación y compresión paso a paso."),
			("Holland: conector F de compresión en RG6 cuádruple malla", "https://www.showmecables.com/blog/post/how-to-install-holland-f-type-compression-connector-for-rg6-quad-shield", "ShowMeCables", "Inglés", LIC_ENLACE, "Malla cuádruple: cómo doblarla bien."),
			("RG6 dual shield: pelado y terminación", "https://www.truecable.com/blogs/cable-academy/how-to-rg6-u-dual-shield-coaxial-strip-and-termination", "TrueCable", "Inglés", LIC_ENLACE, "Medidas de pelado con fotos."),
			("Viasat: guía de tierra de la instalación (job aid)", "https://eguide.field.viasat.com/installation-grounding-job-aid/", "Viasat", "Inglés", LIC_ENLACE, "Buen esquema de bloque de tierra y conductor (aplica igual a coaxial)."),
		],
	},
	{
		"num": "08",
		"carpeta": "08-HFC-Niveles-de-senal",
		"titulo": "HFC: niveles de señal",
		"tecnologia": "HFC",
		"duracion_video": "≈3 min",
		"objetivo": "Medir e interpretar los niveles del módem (bajada, MER/SNR y subida), corregir lo que está en la casa y cerrar solo con valores en rango.",
		"epp": [
			"Medidor de señal CATV/DOCSIS",
			"Módem asignado (MAC y serial en la orden)",
			"Divisores y atenuadores de repuesto",
		],
		"pasos": [
			("Mide en el tap", "Mide primero en el puerto del tap. Si el tap ya está mal, el problema es de red (RED-SINSENAL o RED-AVERIA)."),
			("Mide en la entrada de la casa", "En el bloque de tierra. La diferencia con el tap es la pérdida de tu drop."),
			("Conecta el módem y espera el registro", "El módem debe quedar en línea. Toma la foto con la MAC o el serial visible."),
			("Nivel de bajada", "Entre −7 y +7 dBmV (PMO). Muy alto: atenuador. Muy bajo: revisa conectores, divisores y largo del cable."),
			("MER / SNR", "35 dB o más (PMO). Un MER bajo con nivel bueno indica ruido: conectores flojos, malla dañada o puertos abiertos."),
			("Nivel de subida", "Entre 35 y 51 dBmV (PMO). Muy alto (cerca de 51) indica demasiada pérdida en el camino de retorno: quita divisores innecesarios."),
			("Menos divisores, mejor señal", "Cada divisor de 2 vías pierde unos 3,5 dB. Usa solo los que el cliente necesita."),
			("Prueba de velocidad y registro", "Registra los tres niveles y la velocidad en la app."),
		],
		"criterios": [
			"Downstream: −7 a +7 dBmV (PMO)",
			"MER / SNR downstream: ≥ 35 dB (PMO)",
			"Upstream: 35 a 51 dBmV (PMO)",
			"Foto del módem con MAC / serial y prueba de velocidad",
		],
		"errores": [
			"Cerrar con el upstream en 52 o más 'porque navega'",
			"Dejar divisores en cascada sin necesidad",
			"Medir solo en el módem y no en el tap",
			"Ignorar un MER bajo con nivel de bajada bueno",
		],
		"evidencia_app": [
			"Nivel downstream en el módem (−7 a +7 dBmV)",
			"MER / SNR downstream (≥ 35 dB)",
			"Nivel de transmisión upstream (35 a 51 dBmV)",
			"Foto del módem con MAC / serial visible",
			"Prueba de velocidad (Mbps de bajada)",
		],
		"codigos": ["COMP-OK", "RED-SINSENAL", "RED-AVERIA"],
		"preguntas": [
			("El upstream marca 54 dBmV. ¿Qué significa?", ["Todo bien", "Demasiada pérdida en el retorno", "Señal muy fuerte en bajada", "El módem está apagado"], 1),
			("Downstream +2 dBmV pero MER 28 dB. ¿Qué buscas?", ["Nada", "Ruido: conectores flojos, malla, puertos abiertos", "Un amplificador", "Cambiar de cliente"], 1),
			("¿Cuánto pierde aprox. un divisor de 2 vías?", ["0,5 dB", "3,5 dB", "10 dB", "20 dB"], 1),
		],
		"videos": [
			("VIAVI: Cable Subscriber Installation Test Guide (PDF)", "https://www.viavisolutions.com/en-uk/literature/cable-subscriber-installation-test-guide-brochures-en.pdf", "VIAVI", "Inglés", LIC_ENLACE, "Guía de pruebas de instalación de suscriptor HFC."),
			("VIAVI: entrenamiento OneExpert CATV (ONX-630)", "https://www.viavisolutions.com/en-uk/node/113609", "VIAVI", "Inglés", LIC_ENLACE, "Si la cuadrilla usa este medidor."),
			("Cómo leer los niveles del módem: SNR, potencia y T3/T4", "https://www.modemguides.com/blogs/modemguides-blog/modem-signal-levels-snr-power-t3-t4-timeouts-explained", "ModemGuides", "Inglés", LIC_ENLACE, "Explicación sencilla para técnicos nuevos."),
		],
	},
	{
		"num": "09",
		"carpeta": "09-Cierre-y-evidencia-QSG-Campo",
		"titulo": "Cierre y evidencia en la app QSG Campo",
		"tecnologia": "FTTH y HFC",
		"duracion_video": "≈3 min",
		"objetivo": "Que cada orden se cierre en la app con la evidencia completa, el código de cierre correcto y la firma del cliente, sin retrabajos por falta de soporte.",
		"epp": [
			"Teléfono con la app QSG Campo y batería suficiente",
			"GPS activado",
			"Datos móviles o Wi-Fi (la app avisa si no hay conexión)",
		],
		"pasos": [
			("Revisa tu ruta", "Abre 'Mi ruta' al empezar el día: órdenes en orden de visita, con ventana horaria."),
			("Marca 'En ruta'", "Al salir hacia el cliente. Queda registrada la hora y el GPS."),
			("Marca 'En sitio'", "Al llegar. Si estás a más de 300 m de la dirección, la app lo marca para revisión."),
			("Llena el checklist", "Fotos de antes y después, mediciones y preguntas Sí/No según el tipo de trabajo."),
			("Mediciones con rango", "La app valida el rango (por ejemplo −25 a −8 dBm en FTTH). Fuera de rango no deja cerrar como completada."),
			("Datos de red y equipo", "Serial de ONT o MAC del módem, puerto de CTO o tap."),
			("Firma del cliente", "El cliente firma en la pantalla. Explícale qué quedó instalado."),
			("Código de cierre correcto", "COMP-OK si quedó. Si no: CLI-AUS, CLI-RECH, RED-SINPUERTO, etc. El código define si cuenta para SLA y si se cobra."),
			("Cliente ausente", "Foto de fachada, intento de llamada y código CLI-AUS. La orden se reprograma."),
			("Garantía de 30 días", "Si el cliente vuelve a llamar en 30 días, la orden nueva se marca retrabajo y se atribuye a quien instaló. Los retrabajos propios no se pagan."),
		],
		"criterios": [
			"100 % de los ítems obligatorios del checklist",
			"Llegada dentro de 300 m de la dirección",
			"Firma del cliente",
			"Código de cierre que refleja lo que pasó realmente",
		],
		"errores": [
			"Cerrar desde la casa o desde el vehículo lejos del sitio",
			"Usar fotos de otra orden",
			"Cerrar como completada una orden que quedó pendiente",
			"Olvidar marcar 'En ruta' y 'En sitio': afecta el SLA y tu calificación",
		],
		"evidencia_app": [
			"Todo el checklist del tipo de trabajo",
			"Firma del cliente",
			"Historial con hora y GPS de cada cambio de estado",
		],
		"codigos": ["COMP-OK", "COMP-PARCIAL", "CLI-AUS", "CLI-RECH", "CLI-REPROG", "CLI-DIR", "RED-SINPUERTO", "RED-SINSENAL", "RED-AVERIA", "RED-CONSTR", "PERM", "CLIMA", "SEG", "MAT"],
		"preguntas": [
			("Llegas y el cliente no está. ¿Qué haces?", ["Me voy sin registrar", "Foto de fachada, llamada y CLI-AUS", "Cierro como completada", "Espero 3 horas"], 1),
			("¿Qué pasa si el cliente llama otra vez a los 15 días?", ["Nada", "Es retrabajo y se atribuye a quien instaló", "Se cobra doble", "Se cancela la cuenta"], 1),
			("¿Por qué la app pide GPS al marcar 'En sitio'?", ["Por gusto", "Para verificar la llegada (300 m)", "Para el clima", "Para el tráfico"], 1),
		],
		"videos": [],
	},
]

CODIGOS_CIERRE = [
	("COMP-OK", "Trabajo completado", "Completada", "", "No", "Sí", "No"),
	("COMP-PARCIAL", "Completado parcial, pendiente segundo equipo", "Completada", "", "No", "Sí", "No"),
	("CLI-AUS", "Cliente ausente", "No completada", "Cliente", "Sí", "Sí", "Sí"),
	("CLI-RECH", "Cliente rechaza el servicio", "No completada", "Cliente", "Sí", "Sí", "No"),
	("CLI-REPROG", "Cliente solicita otra fecha", "No completada", "Cliente", "Sí", "No", "Sí"),
	("CLI-DIR", "Dirección incorrecta o no localizada", "No completada", "Cliente", "Sí", "No", "Sí"),
	("RED-SINPUERTO", "CTO / tap sin capacidad", "No completada", "Red", "No", "No", "Sí"),
	("RED-SINSENAL", "Sin señal en el punto de acceso", "No completada", "Red", "No", "No", "Sí"),
	("RED-AVERIA", "Avería de planta, escalada", "No completada", "Red", "No", "No", "Sí"),
	("RED-CONSTR", "Requiere construcción u obra", "No completada", "Red", "No", "No", "Sí"),
	("PERM", "Falta permiso o servidumbre", "No completada", "Otro", "Sí", "No", "Sí"),
	("CLIMA", "Condiciones climáticas", "No completada", "Otro", "Sí", "No", "Sí"),
	("SEG", "Riesgo de seguridad", "No completada", "Otro", "Sí", "No", "Sí"),
	("MAT", "Falta material o equipo", "No completada", "Otro", "No", "No", "Sí"),
]

# Pantallas reales de la app QSG Campo (qsg-pmo/celular) para el video 09
PANTALLAS_APP = [
	("1-mi-ruta.png", "Mi ruta", "Tus órdenes del día, en orden de visita y con ventana horaria."),
	("2-detalle-orden.png", "Detalle de la orden", "Cliente, dirección, tipo de trabajo, equipo y materiales."),
	("3-en-ruta.png", "En ruta", "Al salir hacia el cliente. Se guarda hora y GPS."),
	("4-en-sitio-checklist.png", "En sitio y checklist", "Al llegar se abre el checklist del tipo de trabajo."),
	("5-evidencia-fotos.png", "Fotos de evidencia", "Antes y después: CTO o tap, recorrido, equipo con serial."),
	("5b-evidencia-mediciones.png", "Mediciones con rango", "La app valida el rango. Fuera de rango no deja cerrar."),
	("6-datos-red.png", "Datos de la orden", "Cuenta, tecnología, SLA, cuadrilla y contratista. Verifica antes de cerrar."),
	("7-cierre-firma.png", "Firma del cliente", "El cliente firma. Explícale qué quedó instalado."),
	("8-orden-completada.png", "Orden completada", "Código COMP-OK y evidencia completa."),
	("11-bloqueo-sin-evidencia.png", "Sin evidencia no se cierra", "Si falta un ítem obligatorio, la app lo indica."),
	("12-no-completada.png", "No completada", "Elige el código que refleja lo que pasó realmente."),
	("13-cliente-ausente.png", "Cliente ausente", "Foto de fachada, llamada y CLI-AUS. Se reprograma."),
	("9-historial.png", "Historial", "Cada cambio queda con usuario, hora y GPS."),
]


# ---------------------------------------------------------------- v2: normas de PR, ítems críticos y módulos nuevos

FUENTES_NORMAS = [
	("NEC 2017 (NFPA 70) y Reglamento Complementario al Código Eléctrico", "Código de Construcción de Puerto Rico 2018 (vigente desde el 15 de noviembre de 2018)", "https://www.icc-nta.org/code-update/puerto-rico-commonwealth-code-alert/"),
	("OSHA 29 CFR 1910.268 (Telecomunicaciones)", "Adoptada por PR OSHA; exige capacitación certificada con nombre, firma del instructor y fecha", "https://www.osha.gov/laws-regs/regulations/standardnumber/1910/1910.268"),
	("OSHA 29 CFR 1926.1053 (Escaleras)", "Ángulo 4 a 1, extensión de 3 pies sobre el apoyo", "https://www.osha.gov/laws-regs/regulations/standardnumber/1926/1926.1053"),
	("SCTE Broadband Premises Installer (BPI)", "Liberty Puerto Rico la exige a sus técnicos de servicio", "https://www.scte.org/bpi/"),
	("Red de Liberty Puerto Rico", "HFC con DOCSIS 3.1 y FTTH en expansión (DPL News, abril de 2023)", "https://dplnews.com/puerto-rico-liberty-actualiza-su-red-fija-y-ofrece-velocidad-de-hasta-1000-mbps/"),
]

NORMAS = {
	"01": ["OSHA 1910.268 (telecomunicaciones): capacitación certificada, primeros auxilios y RCP", "OSHA 1926.1053 (escaleras)", "Distancia a líneas: 10 pies (3 m) hasta 50 kV (OSHA)", "Reglas de LUMA para trabajo en postes de uso conjunto"],
	"02": ["NEC 2017, Art. 770 (cables de fibra óptica)", "Reglas de LUMA para herrajes en postes de uso conjunto", "Manual de construcción de Liberty (prevalece)"],
	"03": ["Especificación de pérdida de Liberty (prevalece)", "Prácticas FOA de empalme"],
	"04": ["IEC 61300-3-35 (criterio de limpieza de la cara del conector)"],
	"05": ["Manual de aprovisionamiento de Liberty (prevalece)"],
	"06": ["Rangos de la PMO QSG (validados por la app)", "Manual técnico de Liberty (prevalece)"],
	"07": ["NEC 2017, Art. 820.93: la malla del coaxial se conecta a tierra lo más cerca posible de la entrada", "NEC 2017, Art. 820.100: conductor de cobre de 14 AWG o más; hasta 6 m (20 pies) en viviendas de una o dos familias", "SCTE BPI: bonding and grounding"],
	"08": ["Red DOCSIS 3.1 de Liberty", "Rangos de la PMO QSG (validados por la app)"],
	"09": ["Procedimiento QSG PMO", "OSHA 1910.268: registro de capacitación"],
}

# Pasos cuyo incumplimiento reprueba la evaluación práctica sin importar el puntaje
CRITICOS = {
	"01": [1, 3, 4, 5, 6, 7],
	"02": [1, 4, 5],
	"03": [5, 8],
	"04": [1, 4, 6],
	"05": [3, 6],
	"06": [2, 5],
	"07": [2, 4, 7],
	"08": [4, 5, 6],
	"09": [3, 5, 8],
}

ACTIVIDADES.append(
	{
		"num": "10",
		"carpeta": "10-Atencion-al-cliente-en-el-hogar",
		"titulo": "Atención al cliente en el hogar",
		"tecnologia": "FTTH y HFC",
		"duracion_video": "≈3 min",
		"objetivo": "Que el cliente reciba una visita puntual, respetuosa y clara, entienda su servicio y no tenga motivo para volver a llamar.",
		"epp": [
			"Uniforme y carnet de identificación visibles",
			"Cubrebotas y paño para proteger el piso",
			"Teléfono con la app QSG Campo",
			"Guía rápida del servicio para dejarle al cliente",
		],
		"pasos": [
			("Confirma la cita", "Llama o escribe antes de salir hacia el cliente. Si vas a llegar tarde, avisa antes de la ventana, no después."),
			("Preséntate", "Saluda, di tu nombre, que vienes de parte de Liberty con QSG, y muestra tu identificación."),
			("Confirma el trabajo", "Repite lo que vas a hacer y pregunta dónde quiere el equipo. Explica si hay que perforar."),
			("Cuida la casa", "Cubrebotas, paño en el piso y nada de herramientas sobre los muebles. Pide permiso antes de mover algo."),
			("Comunica los cambios", "Si algo no se puede hacer como el cliente quería, explícale por qué y ofrécele una alternativa antes de hacerla."),
			("Deja todo limpio", "Recoge recortes, polvo de perforación y empaques. Toma la foto del área limpia."),
			("Enseña el servicio", "Muéstrale las luces del equipo, el nombre y la clave del Wi-Fi, y cómo reiniciarlo."),
			("Explica la encuesta", "Dile que recibirá una encuesta de satisfacción y que su opinión cuenta."),
			("Firma y despedida", "Pide la firma en la app después de que el cliente vea el servicio funcionando."),
		],
		"criterios": [
			"Llegada dentro de la ventana o aviso previo al cliente",
			"Identificación visible durante toda la visita",
			"Área limpia (foto obligatoria)",
			"Cliente sabe usar el equipo y el Wi-Fi antes de firmar",
		],
		"errores": [
			"Llegar fuera de la ventana sin avisar",
			"Perforar sin explicar ni pedir permiso",
			"Pedir la firma antes de que el cliente vea el servicio funcionando",
			"Hablar mal de la empresa, de otro técnico o de otro contratista",
		],
		"evidencia_app": [
			"Estados En ruta y En sitio a tiempo",
			"Foto del área de trabajo limpia al terminar",
			"Firma del cliente",
			"Encuesta de satisfacción (estrellas y NPS) ligada a la orden",
		],
		"codigos": ["COMP-OK", "CLI-AUS", "CLI-RECH", "CLI-REPROG"],
		"preguntas": [
			("Vas a llegar 30 minutos tarde. ¿Qué haces?", ["Nada, llego igual", "Aviso al cliente antes de la ventana", "Cancelo la orden", "Llego y me disculpo"], 1),
			("¿Cuándo se pide la firma del cliente?", ["Al llegar", "Después de que vea el servicio funcionando", "Antes de perforar", "No hace falta"], 1),
			("El cliente quiere el equipo en un lugar sin energía. ¿Qué haces?", ["Lo pongo donde yo quiera", "Le explico y le ofrezco una alternativa", "Me voy", "Lo pongo sin energía"], 1),
		],
		"videos": [
			("SCTE Broadband Premises Installer (BPI): incluye servicio al cliente", "https://www.scte.org/bpi/", "SCTE", "Inglés", LIC_ENLACE, "Certificación que Liberty exige a sus técnicos de servicio."),
		],
	}
)

ACTIVIDADES.append(
	{
		"num": "11",
		"carpeta": "11-Diagnostico-basico-de-fallas",
		"titulo": "Diagnóstico básico de fallas FTTH y HFC",
		"tecnologia": "FTTH y HFC",
		"duracion_video": "≈3 min",
		"objetivo": "Encontrar la causa de una falla de forma ordenada, del equipo del cliente hacia la red, y corregir en la primera visita lo que está en la casa.",
		"epp": [
			"Medidor de potencia PON y microscopio (FTTH)",
			"Medidor de señal DOCSIS (HFC)",
			"Conectores, patch cords, divisores y terminadores de repuesto",
			"Laptop o teléfono para prueba de velocidad por cable",
		],
		"pasos": [
			("Escucha al cliente", "Pregunta qué falla, desde cuándo y si pasa a cierta hora. Una falla intermitente cuenta otra historia que una caída total."),
			("Revisa las luces del equipo", "En la ONT: LOS en rojo indica que no llega luz. En el módem: sin registro indica nivel o ruido."),
			("Mide en el equipo", "FTTH: potencia a 1490 nm. HFC: downstream, MER y upstream. Compara con los rangos de la app."),
			("Divide el camino en mitades", "Mide en la roseta o el bloque de tierra, luego en la CTO o el tap. Así sabes si la falla está en la casa, en el drop o en la red."),
			("Revisa lo que más falla", "FTTH: conector sucio, curva fuerte, patch cord pisado. HFC: conector flojo, malla dañada, divisores de más, puerto abierto."),
			("Corrige y vuelve a medir", "Cambia una sola cosa a la vez y mide después de cada cambio. Así sabes qué lo arregló."),
			("Si la falla es de red", "Si el puerto de la CTO o del tap ya está mal, cierra con RED-SINSENAL o RED-AVERIA con la medición como evidencia."),
			("Prueba final con el cliente", "Prueba de velocidad por cable y verifica el servicio con el cliente presente."),
			("Registra la causa", "Escribe en la app qué encontraste y qué hiciste. Eso alimenta la garantía de 30 días y evita retrabajos."),
		],
		"criterios": [
			"Mediciones antes y después del arreglo registradas",
			"Causa de la falla descrita en la app",
			"Servicio verificado con el cliente",
			"Fallas de red cerradas con código y medición de evidencia",
		],
		"errores": [
			"Cambiar el equipo del cliente sin medir primero",
			"Cambiar varias cosas a la vez y no saber cuál fue la causa",
			"Cerrar como 'resuelto' sin prueba con el cliente",
			"No registrar la causa: la próxima visita empieza de cero",
		],
		"evidencia_app": [
			"Descripción de la falla encontrada",
			"Foto de la falla y foto de la corrección",
			"Medición final (dBm o dBmV)",
			"Servicio verificado con el cliente (Sí/No)",
		],
		"codigos": ["COMP-OK", "RED-SINSENAL", "RED-AVERIA", "MAT"],
		"preguntas": [
			("La ONT muestra LOS en rojo. ¿Qué significa?", ["Falta energía", "No está llegando luz", "Wi-Fi apagado", "Todo bien"], 1),
			("¿Por qué se cambia una sola cosa a la vez?", ["Para tardar más", "Para saber qué arregló la falla", "Lo exige el cliente", "No importa"], 1),
			("En el tap el nivel está bien y en la casa mal. ¿Dónde está la falla?", ["En la red", "En el drop o la casa", "En el CMTS", "En la OLT"], 1),
		],
		"videos": [
			("FOA Lecture 66: FTTH Network Installation and Test", "https://youtu.be/EOme0pvgnoc", "Fiber Optic Association", "Inglés", LIC_FOA, "Pruebas en FTTH aplicadas a la búsqueda de fallas."),
			("Cómo leer los niveles del módem: SNR, potencia y T3/T4", "https://www.modemguides.com/blogs/modemguides-blog/modem-signal-levels-snr-power-t3-t4-timeouts-explained", "ModemGuides", "Inglés", LIC_ENLACE, "Síntomas en el módem y su causa probable."),
		],
	}
)
NORMAS["10"] = ["SCTE BPI: Customer Service", "Encuesta QSG (estrellas y NPS) ligada a la orden"]
NORMAS["11"] = ["SCTE BPI: Troubleshooting and Repair", "Rangos de la PMO QSG"]
CRITICOS["10"] = [2, 4, 9]
CRITICOS["11"] = [3, 6, 8]

for _a in ACTIVIDADES:
	_a["normas"] = NORMAS.get(_a["num"], [])
	_a["criticos"] = CRITICOS.get(_a["num"], [])
	_a["duracion_video"] = "≈3 min"

# Perfiles de calificación
PERFILES = [
	("Instalador HFC (Nivel 1)", ["01", "07", "08", "09", "10"], "Licencia de conducir vigente; escalera de extensión; primeros auxilios y RCP. Recomendado SCTE BPI."),
	("Instalador FTTH (Nivel 1)", ["01", "02", "04", "05", "06", "09", "10"], "Licencia de conducir vigente; escalera de extensión; primeros auxilios y RCP. Recomendado SCTE BPI."),
	("Técnico dual FTTH y HFC (Nivel 2)", ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11"], "Nivel 1 en ambas tecnologías y 3 meses sin retrabajos atribuidos. SCTE BPI requerido (Liberty lo exige a sus técnicos de servicio)."),
]
