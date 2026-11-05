# Investigación profunda (v2): plataforma PMO para cuadrillas HFC/FTTH con asignación óptima

**Fecha:** 4 de noviembre de 2026
**Complementa a:** [`pmo-tooling-report.md`](pmo-tooling-report.md) (v1). Esta versión agrega el roadmap completo del producto, el ranking por popularidad en GitHub, motores de optimización, la búsqueda en Hugging Face y una clasificación de cada link.

**Método:** API de búsqueda de GitHub (estrellas, forks, issues abiertos, licencia y último push tomados el 2026-11-04), lectura de READMEs, búsqueda web y búsqueda en Hugging Face. La API de Hugging Face estaba bloqueada por la red del entorno, así que en HF se buscó a través del buscador web (limitación declarada). Las capacidades de cada producto salen de su documentación pública; antes de comprometer la base hay que confirmarlas con una prueba de concepto.

---

## 1. Respuesta corta

| Pregunta | Respuesta |
|---|---|
| **¿Cuál se acomoda más a la necesidad?** | **Frappe Framework + ERPNext** (con Frappe HR, Helpdesk e Insights) más la app **Beveren FSM**. Cubre total o parcialmente las 10 capacidades del roadmap y es la más fácil de extender. |
| **¿Cuál tiene más estrellas en GitHub?** | Entre herramientas de gestión: **Plane** (62k★), **Twenty CRM** (60k★), **Odoo** (55.5k★), **ERPNext** (40.9k★), **Appsmith/ToolJet** (41k★). Ninguna de las más populares es de servicio en campo; la popularidad no equivale a encaje. |
| **¿Cuál es la más competente en campo (FSM)?** | **Odoo Community + OCA Field Service**: ~40 módulos de campo (territorios, rutas, habilidades, subcontratación, validación por etapa). Su punto débil es la app móvil (la buena es de pago). |
| **¿Existe algo listo para HFC/FTTH de contratista?** | No. Lo telecom que existe son piezas (diseño de fibra, inventario de empalmes, aprovisionamiento DOCSIS/FTTH, facturación de ISP), no gestión de cuadrillas de un contratista. |
| **¿Y la asignación óptima automática?** | Ninguna plataforma FSM abierta la trae de verdad. Se resuelve agregando un **motor de optimización** probado: **VROOM** (técnicos con habilidades y ventanas de tiempo), **Google OR-Tools** o **Timefold**, alimentado con tiempos de viaje reales de Puerto Rico vía **OSRM** con mapas de OpenStreetMap. |
| **¿Hugging Face sirve?** | Solo como investigación: hay modelos neuronales de rutas (RL4CO, RouteFinder) y demos, pero nada listo para producción. Para despacho real se recomiendan los solvers clásicos. |

**Base recomendada:** Frappe/ERPNext + Beveren FSM (núcleo) + VROOM/OSRM (asignación óptima) + PWA offline o ODK Collect (campo).
**Alternativa:** Odoo Community 18 + OCA Field Service + el mismo motor de optimización.

---

## 2. Roadmap objetivo del producto (cómo se evaluó)

Servicios: instalaciones y reparaciones **HFC** y **FTTH**, última milla, **reconectorizaciones en hogares** (cambio o reponchado de conectores F/SC-APC, drops), residencial y empresarial, para **Liberty Puerto Rico**.

| # | Capacidad | Qué significa en la operación |
|---|---|---|
| C1 | Recepción de órdenes del cliente | Recibir las órdenes de Liberty de forma automática (API, archivo o portal) y normalizarlas. |
| C2 | Asignación automática y óptima | Proponer o asignar la cuadrilla según habilidad (FTTH/HFC/empresarial), zona, capacidad, ventana de cita y distancia. |
| C3 | Programación de cuadrillas | Calendario por cuadrilla, ventanas AM/PM, reprogramaciones, tablero de despacho. |
| C4 | Evaluación de calidad de contratistas | Scorecard por contratista y cuadrilla: cumplimiento de cita, primera visita exitosa, re-trabajo, encuestas, auditorías. |
| C5 | Recogida de materiales en bodega | Generar la lista de materiales del día por cuadrilla (pick list), reservar, despachar y conciliar seriales (ONT, módems). |
| C6 | Checklist de cumplimiento | Verificar en sitio que se cumplieron los pasos y mediciones antes de permitir el cierre. |
| C7 | Reporte en sitio con fotos | App móvil (ideal offline) con fotos geolocalizadas, firma y mediciones. |
| C8 | Satisfacción y finalización | Encuesta al cliente y acta/reporte de finalización generado automáticamente. |
| C9 | Tablero en tiempo real | Estado de todas las órdenes y cuadrillas, SLA en riesgo, mapa, KPIs para el gerente. |
| C10 | Integración automática | Enviar cierres, evidencias y métricas al sistema de Liberty o de terceros (API, webhooks, archivos). |

---

## 3. Ranking por popularidad y madurez en GitHub

Datos del 2026-11-04. "Encaje" resume la clasificación de la sección 4.

### 3.1 Plataformas de gestión (posibles bases)

| # | Proyecto | ★ | Forks | Issues abiertos | Lenguaje | Licencia | Desde | Último push | Encaje |
|---|---|---|---|---|---|---|---|---|---|
| 1 | [makeplane/plane](https://github.com/makeplane/plane) | 61,982 | 6,299 | 1,107 | TypeScript | AGPL-3.0 | 2022 | 2026-11-03 | Bajo (PM de escritorio) |
| 2 | [twentyhq/twenty](https://github.com/twentyhq/twenty) | 60,438 | 9,962 | 172 | TypeScript | AGPL/comercial | 2022 | 2026-11-04 | Bajo (CRM) |
| 3 | [odoo/odoo](https://github.com/odoo/odoo) + [OCA/field-service](https://github.com/OCA/field-service) | 55,544 / 204 | 34,225 / 323 | — | Python | LGPL-3 / AGPL-3.0 | 2014 / 2018 | 2026-11-04 / 2026-11-02 | **Alto** |
| 4 | [ToolJet/ToolJet](https://github.com/ToolJet/ToolJet) | 41,191 | 5,512 | 925 | TS | AGPL-3.0 | 2021 | 2026-11-04 | Medio-bajo (constructor low-code) |
| 5 | [appsmithorg/appsmith](https://github.com/appsmithorg/appsmith) | 41,157 | 4,826 | 4,522 | TS | Apache-2.0 | 2020 | 2026-11-04 | Medio-bajo (constructor low-code) |
| 6 | [frappe/erpnext](https://github.com/frappe/erpnext) + [frappe/frappe](https://github.com/frappe/frappe) | 40,938 / 11,053 | 13,408 / 5,506 | — | Python | GPL-3.0 / MIT | 2011 | 2026-11-04 | **Muy alto** |
| 7 | [Budibase/budibase](https://github.com/Budibase/budibase) | 28,382 | 2,240 | 320 | TS | GPL/comercial | 2019 | 2026-11-04 | Medio-bajo (low-code) |
| 8 | [nocobase/nocobase](https://github.com/nocobase/nocobase) | 24,837 | 2,950 | 346 | TS | AGPL/comercial | 2020 | 2026-11-04 | Medio-bajo (low-code) |
| 9 | [opf/openproject](https://github.com/opf/openproject) | 16,990 | 3,687 | 352 | Ruby | GPL-3.0 | 2012 | 2026-11-04 | Bajo (PMO de portafolio) |
| 10 | [Leantime/leantime](https://github.com/Leantime/leantime) | 11,960 | 1,169 | 247 | PHP | AGPL-3.0 | 2015 | 2026-11-01 | Bajo |
| 11 | [frappe/hrms](https://github.com/frappe/hrms) | 9,017 | 2,864 | 482 | Python | GPL-3.0 | 2022 | 2026-11-04 | Complemento de ERPNext |
| 12 | [glpi-project/glpi](https://github.com/glpi-project/glpi) | 6,555 | 1,854 | 474 | PHP | GPL-3.0 | 2015 | 2026-11-04 | Medio-bajo (ticketing con SLA) |
| 13 | [zammad/zammad](https://github.com/zammad/zammad) | 6,081 | 1,094 | 486 | Ruby | AGPL-3.0 | 2012 | 2026-11-04 | Bajo (helpdesk) |
| 14 | [fleetbase/fleetbase](https://github.com/fleetbase/fleetbase) | 4,512 | 1,190 | 19 | JS/PHP | AGPL-3.0 | 2022 | 2026-11-02 | Medio (despacho y app móvil, dominio logística) |
| 15 | [frappe/crm](https://github.com/frappe/crm) | 3,912 | 1,577 | 293 | Vue | AGPL-3.0 | 2023 | 2026-11-04 | Complemento |
| 16 | [frappe/helpdesk](https://github.com/frappe/helpdesk) | 3,478 | 1,000 | 210 | Vue | AGPL-3.0 | 2021 | 2026-11-04 | Complemento (SLA, CSAT) |
| 17 | [cortezaproject/corteza](https://github.com/cortezaproject/corteza) | 2,186 | 531 | 25 | Go | Apache-2.0 | 2019 | 2026-10-20 | Medio-bajo (low-code) |
| 18 | [frappe/insights](https://github.com/frappe/insights) | 1,034 | 535 | 146 | Python | AGPL-3.0 | 2022 | 2026-11-04 | Complemento (tableros) |
| 19 | [itflow-org/itflow](https://github.com/itflow-org/itflow) | 1,053 | 280 | 0 | PHP | AGPL-3.0 | 2019 | 2026-11-04 | Bajo (PSA para MSP) |
| 20 | [taigaio/taiga-back](https://github.com/taigaio/taiga-back) | 858 | 322 | 98 | Python | MPL-2.0 | 2021 | 2026-11-03 | Bajo (ágil) |
| 21 | [Grashjs/cmms](https://github.com/Grashjs/cmms) (Atlas CMMS) | 855 | 250 | 103 | TS/Java | AGPL-3.0 | 2025 | 2026-10-27 | Medio (gran móvil, dominio mantenimiento) |
| 22 | [minthcm/minthcm](https://github.com/minthcm/minthcm) | 438 | 92 | — | PHP | AGPL-3.0 | — | 2026-11-04 | Bajo (RR.HH.) |
| 23 | [Resgrid/Core](https://github.com/Resgrid/Core) | 237 | 91 | — | C# | Apache-2.0 | — | 2026-11-03 | Medio-bajo (despacho de emergencias con AVL) |
| 24 | [nightflyza/Ubilling](https://github.com/nightflyza/Ubilling) | 187 | 144 | — | PHP | GPL-2.0 | — | 2026-10-23 | Medio-bajo (ISP: tareas de técnicos, bodega; pensado para el ISP, no el contratista) |
| 25 | [clawnify/OpenFieldService](https://github.com/clawnify/OpenFieldService) | 55 | 23 | — | TS | MIT | — | 2026-10-21 | Medio-bajo (FSM pequeño: despacho, checklists, materiales) |
| 26 | [Beveren FSM](https://github.com/Beveren-Software-Inc/Field_Service_Management) | 28 | 24 | 1 | TS/Python | AGPL-3.0 | 2025 | 2026-10-06 | **Alto como semilla sobre ERPNext** |
| 27 | [sys-ae/fieldopt](https://github.com/sys-ae/fieldopt) | 9 | 1 | — | PL/pgSQL | AGPL-3.0 | — | 2026-10-14 | Referencia (auto-router por habilidad, zona y capacidad; v0.0.9) |

### 3.2 Motores de asignación y rutas (para C2)

| Proyecto | ★ | Forks | Lenguaje | Licencia | Último push | Qué resuelve |
|---|---|---|---|---|---|---|
| [google/or-tools](https://github.com/google/or-tools) | 14,328 | 2,543 | C++ (Python/Java/.NET) | Apache-2.0 | 2026-11-04 | Rutas con ventanas de tiempo, capacidades, asignación (CP-SAT). El estándar de la industria. |
| [Project-OSRM/osrm-backend](https://github.com/Project-OSRM/osrm-backend) | 8,192 | 3,979 | C++ | BSD-2 | 2026-11-02 | Matriz de tiempos de viaje real sobre OpenStreetMap (Puerto Rico). |
| [graphhopper/graphhopper](https://github.com/graphhopper/graphhopper) | 6,755 | 1,972 | Java | Apache-2.0 | 2026-11-04 | Ruteo vial alternativo a OSRM. |
| [valhalla/valhalla](https://github.com/valhalla/valhalla) | 6,412 | 1,020 | C++ | MIT | 2026-11-04 | Ruteo vial con perfiles de vehículo. |
| [apache/incubator-kie-optaplanner](https://github.com/apache/incubator-kie-optaplanner) | 3,513 | 971 | Java | Apache-2.0 | 2026-07-14 | Planificación con restricciones (antecesor de Timefold; menos activo). |
| [VROOM-Project/vroom](https://github.com/VROOM-Project/vroom) | 1,910 | 448 | C++ | BSD-2 | 2026-11-04 | **Asignación de trabajos a técnicos con habilidades, ventanas de tiempo, turnos, capacidades y prioridades**, en milisegundos, vía API JSON. Ideal para el despacho diario. |
| [TimefoldAI/timefold-solver](https://github.com/TimefoldAI/timefold-solver) (+ [quickstarts](https://github.com/TimefoldAI/timefold-quickstarts), 603★) | 1,851 | 243 | Java/Python | Apache-2.0 | 2026-11-04 | Planificador con reglas de negocio (vehicle-routing, task-assigning, maintenance-scheduling, employee-scheduling). Bueno para reglas complejas y re-optimización continua. |
| [graphhopper/jsprit](https://github.com/graphhopper/jsprit) | 1,838 | 639 | Java | Apache-2.0 | 2026-09-14 | Rutas con habilidades y ventanas. Maduro, poco movimiento. |
| [ai4co/rl4co](https://github.com/ai4co/rl4co) | 919 | 157 | Python | MIT | 2026-09-14 | Investigación: aprendizaje por refuerzo para problemas de rutas. |
| [PyVRP/PyVRP](https://github.com/PyVRP/PyVRP) | 722 | 163 | Python/C++ | MIT | 2026-11-04 | Solver VRP de última generación (ventanas de tiempo). |
| [ai4co/routefinder](https://github.com/ai4co/routefinder) | 127 | 19 | Python | MIT | 2025-12-03 | Investigación: "modelo fundacional" para rutas. |
| [rodrigo-arenas/pyworkforce](https://github.com/rodrigo-arenas/pyworkforce) | 91 | 17 | Python | MIT | 2026-10-18 | Dimensionamiento de personal y turnos (cuántas cuadrillas necesito por día). |

### 3.3 Hugging Face

| Recurso | Tipo | Valor para el proyecto |
|---|---|---|
| [ai4co/rrnco](https://huggingface.co/ai4co/rrnco) | Modelo | Modelo neuronal de rutas (investigación de AI4CO). No incluye habilidades ni ventanas reales de un despacho. |
| [peterkros/cvrp-model](https://huggingface.co/peterkros/cvrp-model) | Modelo | Rutas con capacidad (CVRP) de juguete. |
| [RouteFinder (paper)](https://huggingface.co/papers/2406.15007) | Paper | Estado del arte en modelos fundacionales de rutas. Útil para leer, no para producción. |
| [Attention, Learn to Solve Routing Problems!](https://huggingface.co/papers/1803.08475) | Paper | Base académica de los solvers neuronales. |
| [blackopsrepl/vehicle-routing-python](https://huggingface.co/spaces/blackopsrepl/vehicle-routing-python) | Space | Demo interactiva de rutas en Python (estilo quickstart de Timefold). Sirve para ver el concepto. |
| [albones80/route-optimizer-demo](https://huggingface.co/spaces/albones80/route-optimizer-demo) | Space | Demo de optimización de rutas. |
| [Hugdrigo/queuescope-service-operations-lab](https://huggingface.co/spaces/Hugdrigo/queuescope-service-operations-lab) | Space | Laboratorio de colas para operaciones de servicio (dimensionamiento). |
| [Yahias21/vrp_benchmark](https://huggingface.co/datasets/Yahias21/vrp_benchmark), [qiliuchn/operations-research](https://huggingface.co/datasets/qiliuchn/operations-research) | Datasets | Benchmarks para probar un solver. |

**Conclusión HF:** no hay en Hugging Face un producto de despacho de campo. Los modelos neuronales aún no manejan bien las restricciones duras de un despacho real (habilidad FTTH vs HFC, ventana de cita del cliente, capacidad de la cuadrilla, stock en el camión), y no explican sus decisiones. Para el MVP conviene **VROOM u OR-Tools**. HF sí puede aportar más adelante con modelos de lenguaje o visión, por ejemplo para revisar automáticamente las fotos de evidencia (¿se ve el serial de la ONT?, ¿la foto es del CTO?) o para predecir la duración de cada orden.

### 3.4 Componentes de soporte

| Necesidad | Proyecto | ★ | Licencia | Nota |
|---|---|---|---|---|
| App de campo offline con fotos, GPS y firma | [getodk/collect](https://github.com/getodk/collect) + [getodk/central](https://github.com/getodk/central) | 801 / 232 | Apache-2.0 | Robusta sin señal; integrable por API. |
| | [kobotoolbox/kpi](https://github.com/kobotoolbox/kpi) | 188 | AGPL-3.0 | Basada en ODK, servidor más amigable. |
| | [opengisch/QField](https://github.com/opengisch/QField) | 1,397 | GPL-2.0 | Campo sobre mapas QGIS (más útil para construcción de red). |
| | [frappe/mobile](https://github.com/frappe/mobile) | 273 | MIT | App Flutter para Frappe; **sin actividad desde 2022**, no usar como base. |
| | [fleetbase/navigator-app](https://github.com/fleetbase/navigator-app) | 121 | AGPL-3.0 | App de conductor con prueba de entrega (fotos/firma); referencia de UX. |
| Encuestas de satisfacción | [formbricks/formbricks](https://github.com/formbricks/formbricks) | 13,217 | AGPL/comercial | Encuestas por enlace, SMS o correo, con webhooks. |
| | [LimeSurvey/LimeSurvey](https://github.com/LimeSurvey/LimeSurvey) | 3,789 | GPL | Clásico y estable. |
| Tableros en tiempo real | [apache/superset](https://github.com/apache/superset) | 75,409 | Apache-2.0 | BI empresarial. |
| | [metabase/metabase](https://github.com/metabase/metabase) | 50,164 | AGPL/comercial | BI simple para gerencia. |
| Integración con terceros | [n8n-io/n8n](https://github.com/n8n-io/n8n) | 209,572 | Sustainable Use (no OSI) | Flujos de integración visuales; uso interno permitido. |
| | [apache/nifi](https://github.com/apache/nifi) | 6,293 | Apache-2.0 | Integración de datos robusta. |
| GPS de vehículos | [traccar/traccar](https://github.com/traccar/traccar) | 8,055 | Apache-2.0 | Ubicación en vivo de cuadrillas. |
| Inventario de planta de fibra | [netbox-community/netbox](https://github.com/netbox-community/netbox) + [jsenecal/netbox-fms](https://github.com/jsenecal/netbox-fms) | 21,846 / 26 | Apache-2.0 / AGPL-3.0 | Solo si se documentan empalmes o puertos. |
| Diseño de red FTTH | [vukovicvl/fiberq](https://github.com/vukovicvl/fiberq) | 31 | GPL-3.0 | Plugin QGIS. |
| OSS/BSS de ISP | [cablelabs/os-provisioning](https://github.com/cablelabs/os-provisioning) (NMS Prime), [Masamune21-dev/KusumaVisionNMS](https://github.com/Masamune21-dev/KusumaVisionNMS) | 91 / 48 | Apache-2.0 / MIT | Aprovisionamiento DOCSIS/GPON; es terreno de Liberty, solo referencia de modelo de datos. |

---

## 4. Clasificación de cada link contra el roadmap

Leyenda: ✅ cumple de fábrica · 🟡 cumple parcialmente o con configuración · ❌ no cumple.

### 4.1 Plataformas candidatas a base

| Proyecto | C1 Órdenes | C2 Asignación óptima | C3 Programación | C4 Calidad contratistas | C5 Bodega | C6 Checklist | C7 Fotos en sitio | C8 Satisfacción/acta | C9 Tiempo real | C10 Integración | Veredicto |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Frappe/ERPNext + Beveren FSM** (+HR, Helpdesk, Insights) | 🟡 Data Import + API REST | 🟡 *Assignment Rule* (round-robin, balanceo de carga, por campo); falta optimizador | ✅ citas y vista de despacho (Beveren) | ✅ *Supplier Scorecard* para contratistas + KPIs | ✅ *Material Request*, *Pick List*, *Stock Entry*, seriales | ✅ *Quality Inspection* + Workflow que bloquea cierre | 🟡 adjuntos y geolocalización; PWA sin offline | ✅ *Quality Feedback*, Web Forms, CSAT de Helpdesk, formatos de impresión | 🟡 dashboards, actualizaciones en vivo (socket.io), Insights | ✅ API REST, webhooks, eventos | **CUMPLE PARCIAL ALTO · SIRVE DE BASE (principal)** |
| **Odoo CE 18 + OCA field-service** (+helpdesk, survey) | 🟡 importación + XML/JSON-RPC | 🟡 territorios, rutas, habilidades; falta optimizador | ✅ calendario, rutas diarias, disponibilidad | 🟡 vía subcontratación y KPIs propios | ✅ stock, pickings, equipos serializados | ✅ `fieldservice_stage_validation` | ❌/🟡 web móvil; app de campo buena es Enterprise | ✅ `survey`, reportes PDF | 🟡 tableros | ✅ API, acciones automáticas | **CUMPLE PARCIAL ALTO · SIRVE DE BASE (alternativa)** |
| Fleetbase (+Navigator) | ✅ API de órdenes | 🟡 asignación y ruteo de entregas | 🟡 | ❌ | 🟡 extensiones | 🟡 | ✅ fotos y firma en app | ❌ | ✅ mapa en vivo | ✅ API y webhooks | Parcial · no como base (dominio logística) |
| Atlas CMMS | 🟡 solicitudes y API | ❌ | 🟡 | ❌ | 🟡 repuestos | ✅ checklists | ✅ app móvil con fotos | 🟡 | 🟡 | 🟡 API | Parcial · referencia de móvil |
| sys-ae/fieldopt | ❌ | ✅ auto-router por habilidad, zona y capacidad | ✅ consola de despacho | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ consola y mapa | 🟡 PostgREST | Parcial · referencia de despacho (muy nuevo) |
| clawnify/OpenFieldService | 🟡 | ❌ | ✅ calendario semanal | ❌ | 🟡 materiales | ✅ checklists | 🟡 | 🟡 facturas | 🟡 | 🟡 | Parcial · demasiado pequeño |
| Resgrid Core | 🟡 | 🟡 despacho manual con AVL | 🟡 turnos | ❌ | ❌ | ❌ | 🟡 app responder | ❌ | ✅ | ✅ API | No cumple (emergencias) |
| Ubilling | ❌ (orientado al propio ISP) | ❌ | 🟡 gestor de tareas | 🟡 | ✅ bodega | ❌ | ❌ | ❌ | 🟡 | 🟡 | No cumple como base |
| GLPI / Zammad / Frappe Helpdesk | 🟡 correo y API | 🟡 reglas de asignación | ❌ | 🟡 | ❌/🟡 | 🟡 | ❌ | 🟡 encuestas | 🟡 | ✅ | No cumple (ticketing); Helpdesk sí como complemento |
| OpenProject / Plane / Leantime / Taiga | ❌ | ❌ | 🟡 tareas | ❌ | ❌ | 🟡 | ❌ | ❌ | 🟡 | 🟡 | No cumple (PMO de oficina) |
| Appsmith / ToolJet / Budibase / NocoBase / Corteza | 🟡 | ❌ | ❌ (hay que construirlo) | ❌ | ❌ | 🟡 | 🟡 | ❌ | 🟡 | ✅ | No cumple de fábrica; sirve para construir pantallas a medida |
| Twenty CRM / Frappe CRM | 🟡 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | 🟡 | ✅ | No cumple |

### 4.2 Componentes (se ensamblan sobre la base)

| Link | Capacidad que aporta | Veredicto |
|---|---|---|
| VROOM + OSRM (OpenStreetMap de Puerto Rico) | C2 asignación óptima con tiempos reales de viaje | **Usar** en el MVP |
| Google OR-Tools | C2, y también dimensionamiento de cuadrillas | **Usar** si las reglas superan a VROOM |
| Timefold Solver | C2 con reglas de negocio complejas y re-optimización durante el día | Alternativa a OR-Tools |
| PyVRP, jsprit, OptaPlanner, GraphHopper, Valhalla | C2 | Alternativas; no hacen falta |
| ODK Collect/Central, KoboToolbox | C6, C7 offline | **Usar** como plan B para campo si la PWA no basta |
| Formbricks / LimeSurvey | C8 encuestas | Opcional (ERPNext ya trae encuestas básicas) |
| Superset / Metabase / Frappe Insights | C9 | Insights primero; Superset si se necesita BI corporativo |
| n8n / Apache NiFi | C1, C10 conectores | n8n para integraciones rápidas con Liberty o terceros |
| Traccar | C9 ubicación de cuadrillas en vivo | Fase 2 |
| NetBox + netbox-fms, FiberQ, NMS Prime, KusumaVisionNMS | Dominio de red | Solo referencia o fase futura |
| Modelos y Spaces de Hugging Face (RL4CO, RouteFinder, rrnco, demos) | C2 investigación; visión artificial futura para validar fotos | No para el MVP |
| frappe/mobile | C7 | No usar (sin mantenimiento desde 2022) |

---

## 5. Recomendación final y arquitectura propuesta

**Base:** Frappe Framework + ERPNext (+ Frappe HR, Helpdesk e Insights), haciendo *fork* de Beveren FSM para el flujo de órdenes, citas y despacho, y una app propia `pmo_telecom` con todo lo específico de HFC/FTTH y Liberty.

¿Por qué sobre Odoo, siendo Odoo más fuerte en FSM? Por tres cosas que pesan en este roadmap:
1. **Calidad de contratistas (C4):** ERPNext ya trae *Supplier Scorecard* con criterios y pesos configurables. Encaja directo para calificar contratistas con cumplimiento de cita, re-trabajo y encuestas.
2. **Bodega (C5) y cumplimiento (C6):** *Material Request → Pick List → Stock Entry* con seriales, más *Quality Inspection* atada a un Workflow que no deja cerrar sin evidencia, están en el núcleo gratuito.
3. **Costo de extensión y licencia:** en Frappe un modelo nuevo es un DocType con API, permisos y formularios automáticos, y el framework es MIT. En Odoo, la app móvil y varias piezas útiles son Enterprise (de pago) y cada versión anual obliga a migrar módulos.

### Arquitectura

```
Liberty (portal / archivo / API)
        │  C1: importador o n8n
        ▼
┌──────────────────────── Frappe / ERPNext ────────────────────────┐
│ Orden Liberty · Cuadrilla · Contratista · Ventana/SLA · Códigos   │
│ de cierre · Mediciones FTTH/HFC · Checklist de evidencia          │
│ Stock (Pick List, seriales) · Supplier Scorecard · Quality Feedback│
│ Workflow · Webhooks · Insights (tablero)                          │
└───────┬───────────────────────────┬──────────────────────┬────────┘
        │ C2: trabajos del día      │ C7: sincronización    │ C10: cierres y
        ▼                           ▼                       ▼ evidencias
  Servicio de optimización     PWA offline de campo     Webhooks / n8n
  VROOM (u OR-Tools)           (o ODK Collect)          → Liberty / terceros
  + OSRM con mapa de PR
```

### Lógica de asignación (C2), primera versión
- **Entradas:** órdenes del día con coordenadas, tipo (FTTH/HFC, residencial/empresarial, instalación/reparación/reconectorización), ventana de cita, duración estimada, prioridad/SLA; cuadrillas con habilidades, punto de salida (bodega), horario, capacidad y stock en el camión.
- **Restricciones duras:** habilidad, ventana de cita, jornada, material disponible.
- **Objetivo:** minimizar tiempo de viaje y atraso de cita, priorizando órdenes con SLA en riesgo y balanceando carga entre cuadrillas. Más adelante, ponderar por la calificación del contratista (C4).
- **Ciclo:** propuesta nocturna para el día siguiente, aprobación del despachador en el tablero, re-optimización cuando entra una avería o una cuadrilla se atrasa.
- **Salida:** asignaciones, orden de visitas y **pick list por cuadrilla** para la recogida en bodega (C5).

### Fases sugeridas (ajuste de la v1)
1. **Prueba de concepto (2–3 semanas):** ERPNext + Beveren FSM en Docker, 3 cuadrillas y 50 órdenes de ejemplo de Puerto Rico. VROOM + OSRM con el mapa de PR proponiendo asignaciones. Medir que el plan sea razonable.
2. **MVP (8–10 semanas):** DocTypes telecom, checklist y fotos obligatorias, Pick List automática, Supplier Scorecard de contratistas, encuesta de satisfacción y acta PDF, tablero en Insights, importador de órdenes Liberty.
3. **Campo y tiempo real (4–6 semanas):** PWA offline, mapa en vivo (Traccar opcional), re-optimización durante el día, alertas de SLA.
4. **Integración e inteligencia:** webhooks hacia Liberty o terceros; modelos para estimar duración de órdenes y para validar fotos automáticamente.

---

## 6. Riesgos y cómo mitigarlos

| Riesgo | Mitigación |
|---|---|
| Beveren FSM es pequeño (28★) y de un solo proveedor | Tratarlo como semilla: se hace fork y se mantiene como propio. Todo lo crítico vive en el núcleo ERPNext. |
| Campo sin señal en zonas montañosas de PR | PWA con cola offline; ODK Collect como respaldo probado. |
| Formato de órdenes de Liberty desconocido | Importador desacoplado (n8n o script) que se adapta sin tocar el núcleo. |
| Licencias AGPL (Beveren, Helpdesk, Insights) | Sin problema para uso interno con acceso de Liberty a un portal. Si algún día se vende como SaaS, publicar las modificaciones o evitar esos módulos. |
| La optimización no refleja la realidad | Empezar con propuesta y aprobación humana; calibrar duraciones con datos reales antes de automatizar al 100 %. |

---

## Fuentes adicionales (v2)
- Datos de repositorios: API de búsqueda de GitHub, 2026-11-04 (todos los links de las secciones 3 y 4).
- README de FieldOpt: <https://github.com/sys-ae/fieldopt>
- README de OpenFieldService: <https://github.com/clawnify/OpenFieldService>
- Quickstarts de Timefold (vehicle-routing, task-assigning, maintenance-scheduling, employee-scheduling): <https://github.com/TimefoldAI/timefold-quickstarts>
- Hugging Face: <https://huggingface.co/papers?q=vehicle+routing+problems>, <https://huggingface.co/ai4co/rrnco>, <https://huggingface.co/peterkros/cvrp-model>, <https://huggingface.co/papers/2406.15007>, <https://huggingface.co/papers/1803.08475>, <https://huggingface.co/spaces/blackopsrepl/vehicle-routing-python>, <https://huggingface.co/spaces/albones80/route-optimizer-demo>, <https://huggingface.co/spaces/Hugdrigo/queuescope-service-operations-lab>, <https://huggingface.co/datasets/Yahias21/vrp_benchmark>, <https://huggingface.co/datasets/qiliuchn/operations-research>
- RL4CO: <https://github.com/ai4co/rl4co>
