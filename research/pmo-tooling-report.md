# Reporte de investigación: base open-source para la PMO de cuadrillas HFC/FTTH (Liberty Puerto Rico)

**Fecha:** 4 de noviembre de 2026
**Alcance:** fase de investigación y decisión de base. No incluye código del producto.
**Actualización:** ver la investigación profunda [`pmo-deep-research-v2.md`](pmo-deep-research-v2.md), con el roadmap completo, ranking por estrellas, motores de asignación óptima, Hugging Face y la clasificación de cada link.
**Fuentes:** búsqueda en GitHub (API de búsqueda, datos de estrellas y última actividad tomados el 2026-11-04), READMEs de los repositorios y búsqueda web general. Las fuentes web están al final.

---

## 1. Resumen ejecutivo

**Recomendación principal:** construir sobre **Frappe Framework + ERPNext**, usando la app **Beveren FSM** como punto de partida del módulo de campo y el módulo nativo de **Service Level Agreement** de ERPNext/Frappe Helpdesk para los SLAs.

**Alternativa:** **Odoo Community + OCA Field Service** (`OCA/field-service`), que es la suite FSM open-source más madura que existe hoy, pero con una app móvil más débil y un núcleo comercial (Odoo Enterprise) que tira hacia el pago.

Razones de la recomendación, en corto:

1. **Ya resuelve la mitad del problema sin código**: órdenes de servicio, citas, asignación de técnicos, consumo de materiales, inventario serializado (ONT, módems), SLAs con tiempos de respuesta/resolución, flujos de aprobación (Workflow), check-in con geolocalización (Frappe HR) y reportería.
2. **Es la más fácil de "reingenierizar"**: en Frappe un modelo de datos nuevo (DocType) se define desde la UI o en JSON, con API REST, permisos y formularios generados automáticamente. Agregar "Medición óptica", "Código de cierre Liberty" o "Cuadrilla" es configuración más algo de Python, no una reescritura.
3. **Comunidad grande y activa** (ERPNext ~41k estrellas, Frappe ~11k, ambos con commits hoy) y fuerte presencia de integradores en Latinoamérica.
4. **Licencia manejable**: el framework es MIT; ERPNext es GPL-3; Beveren FSM y Helpdesk son AGPL-3. Para uso interno de la PMO (y dando acceso a Liberty a un portal) no hay problema; solo implica que si se modifica el código y se ofrece como servicio a terceros, hay que publicar esas modificaciones.

**Lo que ninguna opción trae y habrá que construir** (en cualquier base): el "lenguaje del operador" — códigos de cierre de Liberty, captura de mediciones ópticas y DOCSIS, checklist de evidencia fotográfica obligatoria, cálculo de penalidades/cumplimiento SLA por ventana de cita, y facturación por rate card (unidad de trabajo) al cliente.

**No encontré** ningún proyecto open-source maduro que sea "PMO de contratista de instalaciones HFC/FTTH" listo para usar. Lo que existe para telecom son piezas (diseño de planta en QGIS, inventario de fibra/empalmes sobre NetBox, aprovisionamiento DOCSIS/FTTH) o apps muy pequeñas y recientes (0–30 estrellas). Por eso la estrategia correcta es una plataforma FSM general + capa telecom propia.

---

## 2. Contexto del caso (requisitos usados para evaluar)

| Área | Requisito |
|---|---|
| Operación | Coordinación de cuadrillas propias y subcontratadas en todo Puerto Rico (zonas/municipios). |
| Tipos de trabajo | Instalación FTTH residencial y empresarial, conexión HFC de última milla (drop coaxial, tap, módem DOCSIS), reparaciones/averías, upgrades, desconexiones. |
| Cliente | Liberty Puerto Rico (Liberty Latin America). Liberty está a la vez expandiendo fibra (Guaynabo, Caguas, San Juan, entre otros) y modernizando su HFC con arquitectura de acceso distribuido (Aurora DAA, julio 2026), así que habrá volumen en ambas tecnologías. |
| SLAs | Ventanas de cita (AM/PM o franjas), tiempo de respuesta y de resolución por prioridad, cumplimiento de cita, reprogramaciones con motivo, re-trabajo/reincidencia, penalidades. |
| Campo | App móvil para técnico, idealmente offline (zonas rurales y montañosas con cobertura irregular), fotos de evidencia, GPS, firma del cliente, mediciones. |
| Materiales | Drop de fibra/coax, conectores, ONT/módems serializados, consumo por orden. |
| Reportería | KPIs por cuadrilla, zona y tipo de orden; cierre diario; facturación al cliente por unidades. |
| Idioma | Español e inglés (Liberty PR opera en ambos). |

---

## 3. Candidatos evaluados

### 3.1 Plataformas completas

#### A. Frappe Framework + ERPNext (+ Frappe HR, Helpdesk)
- **Repos:** <https://github.com/frappe/frappe> (11k★, MIT), <https://github.com/frappe/erpnext> (40.9k★, GPL-3.0), <https://github.com/frappe/hrms> (9k★, GPL-3.0), <https://github.com/frappe/helpdesk> (3.5k★, AGPL-3.0). Actividad: commits el 2026-11-04.
- **Stack:** Python, MariaDB/PostgreSQL, Redis, JavaScript/Vue (frappe-ui).
- **Cubre:** módulo Support con *Service Level Agreement* (tiempos de respuesta/resolución por prioridad, calendario laboral, pausa por estado), Maintenance Visit / Maintenance Schedule, Projects con tareas y timesheets, Stock con números de serie y almacenes (un almacén por camión de cuadrilla), Workflow de aprobaciones configurable, Employee Checkin con geolocalización (Frappe HR), portal de clientes, reportes y dashboards sin código, API REST automática, multi-compañía.
- **Le falta:** tablero de despacho visual tipo "Gantt de cuadrillas" (lo trae Beveren FSM), app móvil offline robusta (la PWA de Frappe necesita conexión), el modelo telecom.
- **Adaptación:** alta facilidad. Ver plan en la sección 6.

#### B. Beveren FSM (app de Field Service para ERPNext)
- **Repo:** <https://github.com/Beveren-Software-Inc/Field_Service_Management> (28★, AGPL-3.0, último push 2026-10-06). Stack TypeScript/Vue + Frappe.
- **Cubre:** flujo completo *Service Request → Quotation (opcional) → Service Order → Service Appointments → Ejecución → Factura*, vista de despacho ("PilotView Schedule"), asignación de técnicos por prioridad y disponibilidad, inicio/fin de trabajo desde la cita, consumo de repuestos.
- **Le falta:** madurez (pocos usuarios/estrellas), SLAs (se toman del núcleo ERPNext), evidencia fotográfica estructurada, mediciones.
- **Adaptación:** buena como *fork* inicial: es pequeña, legible, y ya está atada a ERPNext. Riesgo: depende de un solo proveedor; si se abandona, nos quedamos con el fork (aceptable porque lo vamos a reingenierizar).
- Otras apps FSM de Frappe encontradas, más pequeñas o recientes, para revisar ideas: `vinaymishraofficial/swiftservice` (GPS tracking, GPL-3.0), `kodlyft/fsm` (MIT), `karani-gk/fieldpro-frappe` (MIT, ERPNext v16), `aidgoc/fibertrack-pro` (MIT, gestión de construcción de fibra sobre Frappe con PWA offline y mapas Leaflet; prototipo, 0★, pero el dominio es justo el nuestro).

#### C. Odoo Community + OCA Field Service
- **Repos:** <https://github.com/odoo/odoo> (55.5k★, LGPL-3 para Community), <https://github.com/OCA/field-service> (204★, AGPL-3.0, push 2026-11-02, rama 18.0), <https://github.com/OCA/helpdesk> (263★), <https://github.com/OCA/project> (428★).
- **Stack:** Python, PostgreSQL, OWL/JS.
- **Cubre (es lo más completo en FSM abierto):** ~40 módulos — órdenes, ubicaciones y trabajadores (`fieldservice`), territorios/regiones (`base_territory`), rutas diarias (`fieldservice_route`), habilidades del técnico (`fieldservice_skill`), disponibilidad y días bloqueados (`fieldservice_availability`), vehículos/flotas, stock y equipos serializados, **subcontratación con órdenes de compra automáticas** (`fieldservice_subcontracting`, muy útil para cuadrillas contratistas), validación por etapa (`fieldservice_stage_validation`, sirve para exigir fotos/mediciones antes de cerrar), mapa OSM (`fieldservice_geoengine`), portal, timesheets. SLA vía `helpdesk_mgmt_sla` en OCA/helpdesk.
- **Le falta:** app móvil nativa/offline en Community (la app "Field Service" con hojas de trabajo y firma es de Odoo Enterprise, de pago), el modelo telecom. Las actualizaciones de versión mayor de Odoo son costosas (migrar módulos cada año).
- **Adaptación:** media. Mucho viene hecho, pero el desarrollo en Odoo es más pesado que en Frappe y la presión comercial hacia Enterprise es real.

#### D. Atlas CMMS
- **Repo:** <https://github.com/Grashjs/cmms> (855★, AGPL-3.0, push 2026-10-27). Stack: Java/Spring Boot, React web y **app móvil React Native**.
- **Cubre:** órdenes de trabajo, solicitudes, asignación a equipos, **fotos, firmas, checklists** desde el móvil, inventario de partes, mantenimiento preventivo, reportes.
- **Le falta:** está pensado para mantenimiento de activos de planta, no para citas con clientes; sin SLA por ventana de cita, sin despacho por zona, sin facturación.
- **Adaptación:** media-baja como base; **muy buena como referencia o donante** de la experiencia móvil (fotos/checklists).

#### E. Fleetbase
- **Repo:** <https://github.com/fleetbase/fleetbase> (4.5k★, AGPL-3.0, push 2026-11-02). Stack: PHP/Laravel + Ember, app de conductor "Navigator" (React Native).
- **Cubre:** despacho, órdenes con prueba de entrega (foto/firma), tracking GPS en vivo, zonas de servicio, flotas, multi-organización.
- **Le falta:** es logística (paquetes/entregas), no servicio técnico: sin SLAs de servicio, sin materiales por orden, sin modelo de mediciones.
- **Adaptación:** media-baja. Útil si se priorizara tracking en vivo por encima de todo.

#### F. OpenProject
- **Repo:** <https://github.com/opf/openproject> (17k★, GPL-3.0, activo hoy). Stack Ruby on Rails.
- **Cubre:** gestión de portafolio/programas, Gantt, presupuestos, tiempos, reportes de PMO clásica.
- **Le falta:** todo lo de campo (despacho, móvil, evidencia, SLAs).
- **Rol sugerido:** solo si se quiere una capa de PMO "de programa" (avance por municipio/nodo, hitos de expansión de fibra). No como base.

#### G. Plane
- **Repo:** <https://github.com/makeplane/plane> (62k★, AGPL-3.0, activo). Stack TypeScript/Django.
- **Cubre:** gestión de proyectos moderna (tipo Jira/Linear), ciclos, vistas.
- **Le falta:** campo, SLAs, materiales. Popular, pero no encaja con operación de cuadrillas.

#### H. GLPI (y Zammad)
- **Repos:** <https://github.com/glpi-project/glpi> (6.5k★, GPL-3.0), <https://github.com/zammad/zammad> (6k★, AGPL-3.0).
- **Cubre:** ticketing ITIL con **SLA/OLA**, escalamiento, reglas de negocio, inventario (GLPI), reportería.
- **Le falta:** despacho de cuadrillas, móvil de campo, citas con cliente.
- **Rol sugerido:** referencia para el diseño del motor de SLA; no como base.

### 3.2 Componentes telecom y de campo (para ensamblar)

| Componente | Repo | Licencia / actividad | Para qué nos sirve |
|---|---|---|---|
| **NetBox + netbox-fms** | <https://github.com/netbox-community/netbox> (21.8k★), <https://github.com/jsenecal/netbox-fms> (26★, alpha) | Apache-2.0 / AGPL-3.0, activos | Inventario de planta de fibra: cables, buffers, hilos, **planes de empalme**, circuitos de fibra. Solo si la PMO debe documentar empalmes y puertos de splitter. |
| **FiberQ** (plugin QGIS) | <https://github.com/vukovicvl/fiberq> (31★) | GPL-3.0, release v1.5.0 sep-2026 | Diseño FTTH/GPON en mapa (rutas, cámaras, reservas de cable). Útil para la parte de construcción/expansión, no para instalaciones. |
| **NMS Prime Community** (CableLabs) | <https://github.com/cablelabs/os-provisioning> (91★) | Apache-2.0, push jun-2026 | OSS de aprovisionamiento DOCSIS/FTTH. Liberty ya tiene su propio OSS, así que esto es referencia de modelo de datos (CPE, módem, modem state), no algo a desplegar. |
| **ODK Central / KoboToolbox** | <https://github.com/getodk/central>, <https://github.com/kobotoolbox/kpi> | Apache-2.0 / AGPL-3.0, activos | Formularios **offline** con fotos, GPS y firma en Android. Plan B rápido para la evidencia de campo si la PWA de Frappe no aguanta la falta de señal. |
| **Traccar** | <https://github.com/traccar/traccar> (8k★) | Apache-2.0, activo | Rastreo GPS de vehículos de cuadrilla (200+ protocolos de GPS). Integrable por API. |
| **InvenTree** | <https://github.com/inventree/InvenTree> (7.8k★) | MIT, activo | Inventario de materiales. Innecesario si se usa ERPNext/Odoo (ya lo traen). |
| **Kimai** | <https://github.com/kimai/kimai> (5.1k★) | AGPL-3.0, activo | Control de horas. Innecesario con ERPNext/Odoo. |
| **Otros prototipos telecom** | `mdshemul48/fiber-network-management-tool-for-isp`, `devblueray/splice_tracker`, `Azendale/FOSSFiber`, `Salamon2608/Fiberjet` | varios, 0–28★ | Ideas de modelo de datos; ninguno es base viable (abandonados o muy nuevos). |

---

## 4. Matriz de evaluación

Puntuación 1 (malo) a 5 (excelente). "Licencia permisiva": 5 = MIT/Apache, 3 = GPL/LGPL, 2 = AGPL.

| Criterio | Frappe/ERPNext + Beveren FSM | Odoo CE + OCA FSM | Atlas CMMS | Fleetbase | GLPI | Frappe Helpdesk (solo) | OpenProject | Plane |
|---|---|---|---|---|---|---|---|---|
| Coordinación de cuadrillas / despacho | 4 | 5 | 3 | 4 | 2 | 1 | 2 | 2 |
| SLAs | 4 | 3 | 2 | 1 | 5 | 5 | 1 | 1 |
| Móvil / campo | 3 | 2 | 5 | 5 | 2 | 2 | 2 | 2 |
| Evidencia foto / geo | 4 | 3 | 5 | 5 | 2 | 1 | 1 | 1 |
| Reportería | 4 | 4 | 3 | 3 | 4 | 3 | 4 | 3 |
| Multi-cliente (Liberty + futuros) | 4 | 4 | 3 | 4 | 4 | 4 | 4 | 3 |
| Extensibilidad / facilidad de reingeniería | 5 | 4 | 3 | 4 | 4 | 4 | 3 | 3 |
| Actividad del repo | 4 | 4 | 4 | 4 | 5 | 5 | 5 | 5 |
| Licencia permisiva | 4 | 3 | 2 | 2 | 3 | 2 | 3 | 2 |
| **Total (máx. 45)** | **36** | **32** | **30** | **32** | **31** | **27** | **25** | **22** |

Notas:
- Frappe pierde puntos en móvil porque la PWA no es realmente offline; se mitiga con el plan de la sección 6 (o con ODK como formulario de evidencia).
- Odoo gana en despacho por la riqueza de OCA (rutas, territorios, habilidades, subcontratación), pero el móvil de campo bueno es de pago.
- La "actividad" de Frappe/ERPNext es 5 en el núcleo y 2 en Beveren FSM; se promedió en 4.
- Atlas y Fleetbase tienen la mejor experiencia móvil, pero habría que construirles casi todo lo demás.

---

## 5. Recomendación final

### Principal: Frappe Framework + ERPNext, con Beveren FSM como semilla del módulo de campo
Es la opción que más trabajo ahorra para *este* caso: el núcleo ya trae SLAs, workflow, inventario serializado, facturación y RR.HH. con geolocalización; Beveren FSM aporta el flujo de órdenes/citas/despacho; y el modelo telecom se agrega como una app propia (`liberty_fsm` o `pmo_telecom`) sin tocar el núcleo, lo que mantiene las actualizaciones simples.

### Alternativa: Odoo Community 18 + OCA field-service + OCA helpdesk SLA
Elegirla si se valora más tener rutas, territorios, habilidades y subcontratación ya hechos que la facilidad de desarrollo, o si el equipo que va a desarrollar ya sabe Odoo. Presupuestar una app móvil propia o la licencia Enterprise.

### Descartadas como base
OpenProject y Plane (PMO de escritorio, sin campo), GLPI/Zammad (ticketing sin despacho), Atlas CMMS y Fleetbase (gran móvil, pero dominio equivocado). Se reutilizan como referencia o como componentes.

---

## 6. Esbozo del plan de adaptación (sobre Frappe/ERPNext)

### 6.1 Mantener tal cual (núcleo)
- **Stock** (almacén por cuadrilla/camión, números de serie de ONT y módems, transferencias, conciliación).
- **Service Level Agreement** (prioridades, calendario, tiempos de respuesta/resolución).
- **Workflow** (aprobaciones: cierre de orden, re-trabajo, reprogramación, cargos adicionales).
- **Frappe HR** (empleados, asistencia con check-in geolocalizado, certificaciones).
- **Reportería** (Report Builder, Query Reports, dashboards) y **API REST**.
- **Facturación** (Sales Invoice) para cobrar a Liberty.

### 6.2 Extender (fork de Beveren FSM + app propia)
| DocType / función | Contenido |
|---|---|
| **Orden Liberty** (extiende Service Order) | Nº de orden Liberty, cuenta, tipo (Instalación FTTH Res/Emp, Instalación HFC, Avería, Upgrade, Traslado, Desconexión), tecnología, nodo HFC / OLT-puerto PON / splitter-CTO, municipio y zona, prioridad, ventana de cita, estado Liberty. |
| **Cuadrilla** | Líder y miembros, contratista o propia, vehículo, almacén móvil, habilidades (fusión, OTDR, DOCSIS, aéreo/soterrado, empresarial), zona base, capacidad diaria. |
| **Ventana de cita y SLA** | Franjas (p. ej. 8–12, 12–5), hora de llegada (geofence o check-in), cumplimiento de ventana, motivo de reprogramación catalogado, cálculo de penalidad. |
| **Medición FTTH** | Potencia Rx en ONT y Tx (dBm), longitud de onda, pérdida del drop, archivo OTDR (.sor) adjunto, inspección de conector, serial ONT, prueba de velocidad. |
| **Medición HFC/DOCSIS** | Niveles downstream (dBmV) y MER/SNR, nivel de transmisión upstream, errores de codeword, MAC/serial del módem, verificación de tap y tierra. |
| **Evidencia fotográfica** | Checklist obligatorio por tipo de orden (fachada/dirección, CTO o tap antes/después, recorrido del drop, roseta/punto de terminación, equipo instalado con serial visible, medición en pantalla, área limpia). Foto con GPS y hora; bloquear el cierre si falta alguna (validación por estado). |
| **Acta / cierre** | Firma del cliente, código de cierre, notas, materiales consumidos. |
| **Rate card** | Precio por código de trabajo (unidad) para facturar a Liberty y pagar a subcontratistas. |

### 6.3 Reemplazar o construir
- **App de campo offline:** PWA propia con cola offline (IndexedDB + sincronización al recuperar señal) sobre la API de Frappe. Si el tiempo apremia, usar **ODK Collect** para el formulario de evidencia y sincronizar a ERPNext por API.
- **Tablero de despacho:** partir de la vista de Beveren y agregar mapa (Leaflet/OSM) con órdenes por estado, cuadrillas en vivo (Traccar opcional) y alertas de SLA en riesgo.
- **Integración con Liberty:** depende de cómo Liberty entregue las órdenes (portal, archivos CSV/Excel, API, correo). Se define un importador y un exportador de cierres en su formato.
- **KPIs de PMO:** cumplimiento de ventana, cumplimiento SLA de averías, *First Time Right*, reincidencia/re-trabajo a 30 días, órdenes por cuadrilla por día, backlog y antigüedad, reprogramaciones por motivo, consumo de material vs. estándar, facturación por semana.

### 6.4 Fases sugeridas
1. **Prueba de concepto (2 semanas):** levantar Frappe + ERPNext + Beveren FSM en Docker, cargar 2 cuadrillas y 20 órdenes de ejemplo, probar SLA y despacho.
2. **MVP (6–8 semanas):** DocTypes telecom, checklist de evidencia, mediciones, códigos de cierre, importador de órdenes Liberty, reportes base.
3. **Campo y escala (4–6 semanas):** PWA offline, mapa de despacho, rate card y facturación, subcontratistas.
4. **Optimización:** asignación automática por zona/habilidad, alertas SLA, integración GPS.

---

## 7. Referencias de procedimientos de operador (para que el sistema hable el idioma del sector)

> Los valores numéricos abajo son **típicos de la industria**. Los umbrales que valen son los del manual de instalación y del contrato de Liberty; hay que pedirlos y cargarlos como parámetros, no como constantes en el código.

### 7.1 FTTH / GPON / XGS-PON
- **Normas:** ITU-T G.984 (GPON) y G.9807.1 (XGS-PON) para presupuestos ópticos y clases (B+, C+); ITU-T G.657 para fibra de drop resistente a curvaturas; IEC 61300-3-35 para inspección de la cara del conector; IEC 61280-4-1/4-2 y TIA-568.3-D para medición de pérdida; IEC 61746 para OTDR.
- **Aceptación típica en instalación:** potencia recibida en la ONT dentro del rango del equipo (en GPON clase B+ suele trabajarse entre aproximadamente −8 y −27 dBm, con un margen objetivo; muchos operadores exigen, por ejemplo, mejor que −25 dBm al cerrar), inspección y limpieza de conectores antes de conectar, medición con power meter seleccionando 1490 nm (bajada) y 1310 nm (subida), OTDR para tramos nuevos o averías, registro del serial de la ONT y del puerto/CTO, prueba de velocidad al cliente.
- **Documentos que el sistema debe producir:** acta de instalación firmada, reporte de mediciones, fotos, materiales usados.

### 7.2 HFC / DOCSIS
- **Normas:** especificaciones DOCSIS 3.0/3.1 de CableLabs; prácticas de SCTE (SCTE 99 para tierras y unión, SCTE 1/2 para conectores F, prácticas recomendadas de niveles en casa del suscriptor).
- **Aceptación típica:** niveles downstream en el módem dentro de una ventana (comúnmente alrededor de −7 a +7 dBmV), MER/SNR por encima del mínimo para la modulación (≈ 35 dB o más en 256-QAM), transmisión upstream dentro del rango (comúnmente ~35 a 50 dBmV), sin errores de codeword no corregibles, tierra del drop instalada, conectores comprimidos y apretados, tap terminado. Con la arquitectura DAA de Liberty, el diagnóstico del nodo cambia, pero los parámetros de casa del cliente siguen siendo los mismos.

### 7.3 Códigos de cierre (ejemplo de catálogo a validar con Liberty)
- **Completada:** COMP-OK (instalación completa), COMP-PARCIAL (servicio parcial, pendiente segundo equipo).
- **No completada, cliente:** CLI-AUS (cliente ausente), CLI-RECH (cliente rechaza), CLI-REPROG (cliente pide otra fecha), CLI-DIR (dirección incorrecta).
- **No completada, red:** RED-SINPUERTO (CTO/tap sin capacidad), RED-SINSEÑAL (sin señal en el punto de acceso), RED-AVERIA (avería de planta, escalar), RED-CONSTR (requiere construcción u obra).
- **No completada, otros:** PERM (falta permiso o servidumbre), CLIMA, SEG (riesgo de seguridad), MAT (falta material o equipo).
- Cada código determina si la orden detiene o no el reloj del SLA, si se cobra visita y si se reprograma automáticamente.

### 7.4 SLAs típicos de contratista para un operador (plantilla a ajustar)
- Cumplimiento de ventana de cita (meta típica: ≥ 90–95 %).
- Instalaciones completadas en primera visita (≥ 85–90 %).
- Reincidencia/re-trabajo a 30 días (≤ 3–5 %).
- Averías residenciales resueltas dentro de 24–48 h; empresariales con tiempos de respuesta de pocas horas según contrato.
- Cierre de la orden en el sistema del operador el mismo día, con evidencia completa.
- Penalidades o bonos por desviación de cada métrica.

---

## 8. Preguntas abiertas para cerrar el diseño
1. ¿Cómo entrega Liberty las órdenes a la PMO (portal propio, archivo diario, API, correo) y cómo hay que devolver los cierres?
2. ¿Cuáles son los SLAs y penalidades del contrato, y el catálogo oficial de códigos de cierre de Liberty?
3. ¿Cuántas cuadrillas y cuántas órdenes por día se esperan al inicio, y qué proporción son subcontratistas?
4. ¿Hay preferencia de alojamiento (nube vs. servidor propio) y de idioma de la interfaz?

---

## Fuentes
- GitHub, datos de repositorios vía API de búsqueda (2026-11-04): repositorios citados en las secciones 3 y 4.
- README de Beveren FSM: <https://github.com/Beveren-Software-Inc/Field_Service_Management>
- README de OCA field-service (lista de módulos 18.0): <https://github.com/OCA/field-service>
- README de netbox-fms: <https://github.com/jsenecal/netbox-fms>
- README de FiberQ: <https://github.com/vukovicvl/fiberq>
- README de NMS Prime / CableLabs: <https://github.com/cablelabs/os-provisioning>
- README de FiberTrack Pro: <https://github.com/aidgoc/fibertrack-pro>
- Liberty amplía cobertura de fibra óptica en 3 municipios de Puerto Rico (DPL News): <https://dplnews.com/?p=198426>
- Liberty continues optic fiber construction work in Guaynabo, Caguas, San Juan (News is my Business): <https://newsismybusiness.com/liberty-continues-optic-fiber-construction-work-in-guaynabo-caguas-san-juan>
- Liberty Puerto Rico Deploys Aurora Networks Distributed Access Architecture (Business Wire, jul-2026): <https://www.businesswire.com/news/home/20260715598006/en/>
- Panorama de FSM para telecom (comercial, como referencia de funciones esperadas): <https://www.praxedo.com/our-industries/telecommunications/>, <https://fieldcode.com/en/industries/telecommunications>, <https://www.workyard.com/compare/telecom-field-service-management-software>
- Listados de FSM open-source: <https://buildops.com/resources/field-service-management-open-source>, <https://us.fitgap.com/search/field-service-management-software/open-source?page=1>
- Pruebas PON (referencia de prácticas de medición): <https://normann-engineering.com/support/posters/Understanding%20Passive%20Optical%20Network%20(PON)%20Testing%20(pdf)%20(1).PDF>
