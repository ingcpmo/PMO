# QSG PMO: cobertura del flujo end-to-end (v0.2)

**Fecha:** 4 de noviembre de 2026
**Pregunta del gerente:** ¿la herramienta cubre todo el ciclo, desde que el cliente asigna la orden hasta que el servicio termina, incluyendo seguimiento post-operación, calificación del contratista y control de capacidad de cada contratista?

Leyenda: ✅ cubierto y probado · 🟡 cubierto en parte · ⏭️ planificado para una próxima versión.
"Antes" indica cómo estaba en v0.1; "Ahora" es esta versión.

## 1. Matriz de cobertura

| # | Paso del flujo | Antes (v0.1) | Ahora (v0.2) | Dónde está |
|---|---|---|---|---|
| 1 | **El cliente asigna la orden** (Liberty → QSG) | 🟡 manual o API | 🟡 manual, API REST e importación masiva con *Data Import* de Frappe; número de orden del cliente único por cliente | `QSG Orden` (`external_order_id`) · ⏭️ adaptador al formato de Liberty cuando lo tengamos |
| 2 | **Yo asigno la orden a un contratista** | ❌ solo se asignaba directo a cuadrilla | ✅ estado **«Asignada a contratista»**; asignación individual o masiva desde la lista (*Acciones → Asignar a contratista*) | `QSG Orden.contractor`, `assign_contractor` |
| 3 | **Reasignación** a otro contratista o cuadrilla | ❌ | ✅ botón **Reasignar** con motivo obligatorio; queda en el historial; no se puede poner a mano una cuadrilla de otro contratista | `QSG Orden.reassign`, tabla `QSG Evento Orden` |
| 4 | **Programación** (cuadrilla, día, secuencia, hora) | ✅ | ✅ el plan respeta al contratista ya asignado, excluye cuadrillas ausentes y contratistas con seguro vencido, descuenta lo ya programado y favorece contratistas A | `QSG Plan de Despacho`, `assignment/engine.py` |
| 5 | **Asignación de materiales en bodega** | 🟡 solicitud por cuadrilla | ✅ al aprobar el plan se crea una **Solicitud de materiales** por cuadrilla (bodega central → camión) y queda enlazada en cada orden; al **completar** la orden se crea la **salida de inventario** del camión con los materiales y seriales usados (en borrador para que bodega la valide) | `create_material_requests`, `QSG Orden.create_stock_issue` |
| 6 | **Seguimiento del servicio** | 🟡 | ✅ estados Programada → **En ruta** → **En sitio** → Completada / No completada, con hora de salida, llegada, inicio y fin; botones de campo; **historial** de cada cambio con usuario y GPS; **verificación de llegada** (marca si el técnico llegó a más de 300 m de la dirección) | `QSG Orden` (sección Ejecución e Historial) |
| 7 | **Evidencia antes y después** | ✅ | ✅ checklist por tipo de trabajo con fotos de *antes* y *después* (CTO, tap, conector), mediciones con rango, firma del cliente; no deja cerrar si falta algo | `QSG Plantilla Checklist`, `QSG Resultado Checklist` |
| 8 | **Cierre del servicio** | ✅ | ✅ código de cierre que define si cuenta para SLA, si se cobra y si se reprograma | `QSG Codigo de Cierre` |
| 9 | **Seguimiento post-operación / fallas** | ❌ | ✅ cada orden completada tiene **garantía** (30 días configurable); si entra otra orden de la misma cuenta dentro de la garantía se marca **retrabajo**, se enlaza a la orden original, se le atribuye al **contratista que la ejecutó** y sube a prioridad Alta. Los retrabajos propios **no se pagan** en la liquidación | `QSG Orden` (sección Post-operación) |
| 10 | **Satisfacción del cliente** | ✅ | ✅ encuesta (estrellas y NPS) ligada a orden, contratista y cuadrilla | `QSG Encuesta` · ⏭️ enlace público por SMS |
| 11 | **Calificación del contratista** | 🟡 | ✅ puntaje ponderado: cumplimiento de ventana, primera visita exitosa, SLA, evidencia completa, **sin retrabajo** y satisfacción → categoría A/B/C; **el motor la usa** para preferir contratistas A y penalizar C | `QSG Evaluacion Contratista`, `QSG Configuracion` (pesos) |
| 12 | **Cuántas cuadrillas tiene cada contratista** | ❌ | ✅ campo *Cuadrillas activas* en el contratista y reporte **Capacidad por Contratista** (activas, disponibles hoy, capacidad, programadas, cupos libres, ocupación, órdenes abiertas, calificación, vencimiento de seguro) | reporte `Capacidad por Contratista` |
| 13 | **Agenda de cada cuadrilla** | ❌ | ✅ vista **Calendario** de órdenes filtrable por cuadrilla o contratista, y columna *Agenda* (hora, cliente, estado) en el reporte de ocupación | `qsg_orden_calendar.js` |
| 14 | **Ocupación y disponibilidad** | ❌ | ✅ registro de **ausencias** (vacaciones, vehículo averiado, capacitación…) que el motor respeta; reporte **Ocupación de Cuadrillas** por día: disponibilidad, capacidad, programadas, cupos libres, horas agendadas y % de ocupación | `QSG Disponibilidad`, reporte `Ocupacion de Cuadrillas` |
| 15 | **Tablero en tiempo real** | ❌ | ✅ espacio de trabajo **QSG PMO** con contadores en vivo (órdenes abiertas, SLA en riesgo, SLA vencido, cuadrillas en campo, retrabajos abiertos) y accesos a todo lo anterior | Workspace `QSG PMO` |
| 16 | **Liquidación** (lo que se cobra y lo que se paga) | ❌ | ✅ reporte **Liquidación de Contratistas** por período: completadas, visitas fallidas cobrables, retrabajos (no se pagan), tarifa al cliente, pago al contratista y margen | reporte `Liquidacion de Contratistas`, `QSG Tipo de Trabajo.contractor_rate` |

## 2. Cosas que no pediste pero agregué

- **Seguro del contratista vencido = no recibe trabajo.** El motor lo excluye automáticamente.
- **Verificación de llegada por GPS**, para detectar cierres hechos lejos de la dirección.
- **Liquidación con margen**, porque al cerrar el mes necesitarás cobrarle a Liberty y pagarle a cada contratista con la misma base de datos.
- **Historial inalterable de la orden**, útil para disputas con el cliente o el contratista.
- **Lo ya programado cuenta**: si corres el plan dos veces o asignas a mano, el motor no sobrecarga la cuadrilla.

## 3. Lo que todavía falta (propuesto para v0.3)

| Tema | Por qué importa |
|---|---|
| Adaptador de órdenes de Liberty | Depende de cómo Liberty entregue las órdenes (portal, archivo o API). |
| Notificaciones al suscriptor (cita confirmada, técnico en camino, encuesta por SMS/WhatsApp) | Baja las visitas fallidas por cliente ausente. |
| Portal del contratista con permisos por contratista | Hoy se logra con *User Permission* de Frappe (cada supervisor ve solo su contratista); falta una vista simplificada. |
| App de campo offline | En zonas sin señal la versión web no guarda hasta recuperar conexión. |
| Motor VROOM con mapas reales de Puerto Rico | Mejora las rutas cuando haya volumen. |
| Mapa de despacho en vivo | Ver órdenes y cuadrillas sobre el mapa. |
| Garantía y retrabajo por número de serie del equipo | Hoy se detecta por número de cuenta. |

## 4. Cómo se verificó

- 17 pruebas del motor y del SLA y 3 pruebas de integración del flujo completo, todas en verde. La de reasignación cubre: asignación a contratista, plan que respeta al contratista, reasignación con motivo, bloqueo de cambio manual entre contratistas, ausencia que saca a la cuadrilla del plan, verificación de llegada, garantía, detección de retrabajo y los tres reportes.
- La salida de inventario y la solicitud de materiales no tienen prueba automática todavía, porque requieren configurar la empresa, la bodega central y los artículos en ERPNext; se validarán con la configuración real de bodega.
- Instalación limpia en un sitio nuevo con ERPNext v16.
