# QSG PMO: documento de diseño (v0.1)

**Producto:** QSG PMO, herramienta de gestión de proyectos y operación de cuadrillas para instalaciones y reparaciones **HFC** y **FTTH** (última milla, reconectorizaciones, residencial y empresarial) en **Puerto Rico**, con **Liberty** como primer cliente.
**Base tecnológica:** Frappe Framework v16 + ERPNext v16 (decisión tomada a partir de [`research/pmo-deep-research-v2.md`](../../research/pmo-deep-research-v2.md)).
**Fecha:** 4 de noviembre de 2026.

---

## 1. Decisión de arquitectura: app propia, no fork de ERPNext

En el ecosistema Frappe **no se modifica el código de Frappe ni de ERPNext**. Se crea una **app propia** (`qsg_pmo`) que se instala encima, igual que ERPNext se instala encima de Frappe:

```
frappe-bench/
├── apps/
│   ├── frappe      ← framework (MIT), sin cambios, se actualiza con upstream
│   ├── erpnext     ← ERP (GPL-3), sin cambios, se actualiza con upstream
│   └── qsg_pmo     ← ESTE REPOSITORIO: todo lo nuestro
└── sites/
    └── qsg.local   ← base de datos de la instalación
```

Ventajas:
- Las actualizaciones de seguridad y versiones de Frappe/ERPNext se aplican sin conflictos.
- Todo lo específico (Liberty, HFC/FTTH, SLAs, asignación) queda en un solo repositorio versionado: `ingcpmo/PMO`.
- Lo que necesitamos de ERPNext (clientes, proveedores, bodegas, artículos, seriales, facturación, empleados) se **reutiliza por enlace**, no se copia.

La app Beveren FSM (recomendada en la investigación) se tomará como **referencia de UI del tablero de despacho**, no como dependencia: el modelo de órdenes de QSG PMO es propio porque el flujo de un contratista de operador (orden que llega del cliente, ventana de cita, códigos de cierre, evidencia obligatoria) difiere del flujo de venta de servicio que modela Beveren.

---

## 2. Qué se reutiliza de ERPNext

| Necesidad | DocType de ERPNext | Uso en QSG PMO |
|---|---|---|
| Cliente (Liberty y futuros) | `Customer` | Cada orden enlaza al cliente. Multi-cliente desde el día uno. |
| Contratistas | `Supplier` | Cada `QSG Contratista` enlaza a su proveedor (para órdenes de compra y pagos). |
| Técnicos | `Employee` | Miembros de cuadrilla propios. Subcontratistas pueden registrarse solo por nombre. |
| Bodega central y almacén móvil por cuadrilla | `Warehouse` | Cada cuadrilla tiene su almacén (su camión). |
| Materiales y equipos | `Item`, `Serial No` | Drop de fibra/coax, conectores, ONT, módems con serial. |
| Recogida en bodega | `Material Request` (transferencia) → `Pick List` → `Stock Entry` | Generada automáticamente por el plan de despacho. |
| Facturación al cliente | `Sales Invoice` | Fase 2, desde la rate card de tipos de trabajo. |
| Pago a contratistas | `Purchase Invoice` | Fase 2. |
| Tableros | Dashboard, Number Card, Report Builder | KPIs en tiempo real. |
| Integración | REST API, `Webhook`, Scheduler | Entrada de órdenes y salida de cierres. |

---

## 3. Modelo de datos propio (módulo "QSG PMO")

Convención: los DocTypes llevan prefijo `QSG` para no chocar con ERPNext (por ejemplo, ERPNext ya tiene un `Work Order` de manufactura). Etiquetas en español, nombres de campo en inglés.

### 3.1 Catálogos

| DocType | Propósito | Campos clave |
|---|---|---|
| **QSG Zona** | Zona operativa | `zone_name`, `parent_zone`, `municipalities` (tabla `QSG Zona Municipio`), `latitude`, `longitude` |
| **QSG Habilidad** | Habilidad técnica | `skill_name` (FTTH-RES, FTTH-EMP, HFC-RES, HFC-EMP, FUSION, OTDR, ALTURA, RECONECT) |
| **QSG Contratista** | Empresa contratista o cuadrilla propia | `contractor_name`, `supplier` → Supplier, `is_internal`, `status`, `insurance_expiry`, `current_score`, `current_grade` |
| **QSG Cuadrilla** | Unidad que sale a campo | `crew_code`, `contractor`, `leader_name`, `members` (tabla), `base_zone`, `warehouse` → Warehouse, `skills` (tabla multiselección), `start_latitude/longitude`, `shift_start`, `shift_end`, `max_orders_per_day`, `active` |
| **QSG Tipo de Trabajo** | Catálogo de trabajos con su "receta" | `work_type_code`, `technology` (FTTH/HFC), `segment` (Residencial/Empresarial), `category` (Instalación, Reparación, Reconectorización, Upgrade, Traslado, Desconexión), `duration_minutes`, `required_skills` (tabla), `checklist_template`, `material_kit` (tabla Item + cantidad), `sla_hours`, `rate` |
| **QSG Codigo de Cierre** | Códigos de cierre del operador | `code`, `description`, `result` (Completada/No completada), `cause` (Cliente/Red/Otro), `stops_sla`, `billable`, `requires_reschedule` |
| **QSG Plantilla Checklist** | Pasos y evidencia por tipo de trabajo | `template_name`, `items` (tabla `QSG Item Checklist`: `description`, `item_type` Foto/Medición/Sí-No/Texto, `mandatory`, `unit`, `min_value`, `max_value`) |
| **QSG Configuracion** (single) | Parámetros globales | `central_warehouse`, `sla_risk_minutes`, `assignment_engine` (Reglas/VROOM), `vroom_url`, `osrm_url`, `average_speed_kmh`, pesos del scorecard, `outbound_webhook_enabled` |

### 3.2 Transacciones

**QSG Orden** (el centro del sistema). Serie `QSG-ORD-.YYYY.-.#####`.

| Grupo | Campos |
|---|---|
| Origen | `customer`, `external_order_id` (número de Liberty, único por cliente), `received_on`, `source` (Manual/Importación/API) |
| Trabajo | `work_type`, `technology`, `segment`, `category` (traídos del tipo), `priority` (Baja/Normal/Alta/Crítica) |
| Suscriptor | `subscriber_name`, `account_number`, `phone`, `address`, `municipality`, `zone`, `latitude`, `longitude` |
| Cita y SLA | `appointment_date`, `window_start`, `window_end`, `sla_due`, `sla_status` (En tiempo/En riesgo/Vencido/Cumplido/Incumplido) |
| Despacho | `crew`, `contractor` (traído de la cuadrilla), `dispatch_plan`, `route_sequence`, `estimated_arrival` |
| Ejecución | `status`, `arrived_on`, `started_on`, `finished_on`, `arrival_latitude/longitude` |
| Red | `hfc_node`, `tap`, `olt`, `pon_port`, `splitter_cto`, `equipment_serial` |
| Evidencia | `checklist` (tabla `QSG Resultado Checklist`: ítem, tipo, obligatorio, valor, foto, cumple), `materials_used` (tabla `QSG Material Consumido`: Item, cantidad, serial) |
| Cierre | `closure_code`, `closure_notes`, `customer_signature`, `survey_sent`, `customer_rating` |

**Estados y transiciones** (v0.2)

```
Recibida → Asignada a contratista → Programada → En ruta → En sitio → Completada
    │               │                    │                      └──→ No completada → Reprogramada → (plan)
    └───────────────┴────────────────────┴──→ Reasignación (con motivo) / Cancelada
```

Cada cambio de estado o de asignación queda en la tabla `QSG Evento Orden` (fecha, usuario, de, a, motivo y GPS). Ver la cobertura completa del flujo en [`cobertura-end-to-end.md`](cobertura-end-to-end.md).

Reglas al cerrar (validación en servidor, no solo en pantalla):
- `Completada` exige un código de cierre con resultado *Completada*, todos los ítems obligatorios del checklist con valor o foto, mediciones dentro de rango y al menos un material o equipo registrado si el tipo de trabajo tiene kit.
- `No completada` exige un código de cierre con resultado *No completada*; si el código marca `requires_reschedule`, la orden pasa a la cola de reprogramación.
- El SLA se recalcula en cada guardado y cada 15 minutos con el planificador.

**QSG Plan de Despacho**: un plan por fecha (y opcionalmente por zona).

| Campo | Descripción |
|---|---|
| `plan_date`, `zones` | Alcance del plan |
| `engine` | Reglas (incluido) o VROOM |
| `status` | Borrador → Propuesto → Aprobado |
| `assignments` (tabla `QSG Asignacion`) | orden, cuadrilla, secuencia, llegada estimada, km estimados, motivo |
| `unassigned` | órdenes que no cupieron y por qué |

Acciones: **Generar propuesta** (corre el motor), **Aprobar y publicar** (escribe la cuadrilla, la secuencia y la llegada estimada en cada orden, la pasa a *Asignada* y crea una `Material Request` de transferencia por cuadrilla, desde la bodega central hacia su almacén, sumando los kits de materiales de los tipos de trabajo).

**QSG Encuesta**: orden, cliente, contratista, cuadrilla, `rating` (estrellas), `nps` (0–10), `comments`, `channel`. Al guardarse copia la calificación a la orden. El formulario web público con enlace para el suscriptor llega en v0.2.

**QSG Evaluacion Contratista**: un registro por contratista y período (mensual). Métricas calculadas: cumplimiento de ventana, primera visita exitosa (FTR), re-trabajo a 30 días, satisfacción promedio, cumplimiento de evidencia y SLA. `score` ponderado (pesos en Configuración) y `grade` A/B/C. El puntaje alimenta al motor de asignación en fase 2.

---

## 4. Motor de asignación

Ubicación: `qsg_pmo/assignment/`. Funciones puras de Python, sin dependencia de la base de datos, para poder probarlas y cambiar de motor.

### 4.1 Motor por reglas (incluido en v0.1)
Algoritmo voraz determinista:
1. Ordena las órdenes por urgencia: prioridad, luego vencimiento del SLA, luego inicio de ventana.
2. Para cada orden, filtra cuadrillas **elegibles**: tienen todas las habilidades requeridas, no superan su máximo diario y pueden llegar dentro de la ventana de cita y terminar dentro del turno.
3. Entre las elegibles elige la de **menor costo**: minutos de viaje desde su última parada (distancia haversine × factor de sinuosidad / velocidad media), más penalización por carga (balanceo) y bonificación si la zona coincide.
4. Si ninguna es elegible, la orden queda en `unassigned` con el motivo (sin habilidad, sin capacidad, fuera de ventana).

### 4.2 Motor VROOM (fase PoC)
Adaptador que traduce órdenes y cuadrillas a la API JSON de [VROOM](https://github.com/VROOM-Project/vroom): órdenes → `jobs` (ubicación, `service`, `skills`, `time_windows`, `priority`); cuadrillas → `vehicles` (inicio, `skills`, `time_window` del turno, `max_tasks`). VROOM consulta tiempos de viaje reales a un servidor **OSRM** con el mapa de Puerto Rico de OpenStreetMap. La respuesta se convierte al mismo formato de asignaciones del motor por reglas.

### 4.3 Siempre con aprobación humana
El motor **propone**; el despachador aprueba o mueve asignaciones en el plan. Cuando los datos de duración y de calidad sean confiables, se podrá habilitar la publicación automática.

---

## 5. Roles y permisos

| Rol | Puede |
|---|---|
| **QSG Gerente** | Todo; aprobar planes; ver todos los contratistas y KPIs. |
| **QSG Despachador** | Crear e importar órdenes, generar y aprobar planes, reprogramar. |
| **QSG Supervisor Contratista** | Ver y actualizar las órdenes de sus cuadrillas (restringido por contratista con *User Permission*). |
| **QSG Tecnico** | Ver sus órdenes del día, cambiar estado, llenar checklist, subir fotos, registrar materiales y cerrar. |
| **QSG Bodega** | Atender solicitudes de materiales y despachos a cuadrillas. |
| **QSG Cliente (portal)** | Fase 2: Liberty consulta el estado de sus órdenes y evidencias. |

---

## 6. Integraciones

- **Entrada de órdenes (C1):** API REST de Frappe (`POST /api/resource/QSG Orden`) con `external_order_id` como llave de idempotencia, más importación por CSV/Excel. Cuando se conozca el formato de Liberty se agrega un adaptador dedicado.
- **Salida de cierres (C10):** evento `on_update` de la orden al pasar a Completada o No completada → `Webhook` de Frappe o cola hacia el sistema del cliente, con estado, código de cierre, mediciones y enlaces a fotos.
- **Optimización:** servicios VROOM y OSRM en contenedores aparte, configurados en `QSG Configuracion`.

---

## 7. App de campo

v0.1: el técnico usa la interfaz web de Frappe desde el celular (responsive) con la vista "Mis órdenes de hoy". La fase 2 agrega una **PWA offline** propia (cola local e IndexedDB, sincroniza al recuperar señal), o bien formularios ODK Collect si la falta de cobertura lo exige antes.

---

## 8. Tableros y KPIs

Number Cards y gráficos en el workspace "QSG PMO": órdenes por estado hoy, SLA en riesgo y vencidos, cumplimiento de ventana, FTR, re-trabajo, órdenes por cuadrilla, satisfacción promedio, backlog por antigüedad y mapa de órdenes del día.

---

## 9. Plan de entregas

| Versión | Contenido |
|---|---|
| **v0.1 (esta entrega)** | App instalable, 23 DocTypes, validaciones de cierre, cálculo de SLA (y refresco cada 15 min), motor de asignación por reglas, plan de despacho con aprobación y solicitudes de materiales por cuadrilla, encuesta y evaluación de contratistas, roles, datos semilla (habilidades, zonas de PR, códigos de cierre, checklists, tipos de trabajo), botón «Llegué al sitio» con GPS, 15 pruebas automáticas. |
| v0.2 | Workspace con KPIs y mapa, encuesta pública por enlace, evaluación mensual automática, importador CSV de órdenes de Liberty, restricción por contratista (User Permission) para supervisores y técnicos. |
| v0.3 | Adaptador VROOM + OSRM con mapa de PR, mapa de despacho, webhooks de salida. |
| v0.4 | PWA offline de campo, portal del cliente, facturación por rate card. |

---

## 10. Despliegue

- **Desarrollo:** entorno en la nube de Claude Code (bench de Frappe v16 con MariaDB y Redis). No requiere la máquina del usuario.
- **Pruebas y producción:** servidor local o VPS con Docker usando [`frappe_docker`](https://github.com/frappe/frappe_docker), agregando `qsg_pmo` a la lista de apps de la imagen. Requisitos orientativos: 4 vCPU, 8 GB RAM, 80 GB SSD, Ubuntu 24.04.

---

## 11. Preguntas abiertas

1. Formato y canal en que Liberty entrega las órdenes y espera los cierres.
2. Catálogo oficial de códigos de cierre, SLAs y penalidades del contrato.
3. Cantidad inicial de cuadrillas y de contratistas, y zonas de Puerto Rico a cubrir.
4. Rangos de aceptación de mediciones (potencia óptica, niveles DOCSIS) del manual de Liberty.
