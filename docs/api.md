# API de QSG PMO

Todo lo que se ve en pantalla también se puede hacer por API. Hay tres capas:

1. **API REST genérica de Frappe**: leer, crear y editar cualquier DocType (`/api/resource/...`).
2. **API de campo** (`qsg_pmo.api`): la que usa la app del técnico en el celular.
3. **API de integración** (`qsg_pmo.api`): para que Liberty u otro sistema nos envíe órdenes y consulte su estado.

## Autenticación

| Forma | Cuándo | Cómo |
|---|---|---|
| Sesión | App de campo en el navegador del celular | `POST /api/method/login` con `usr` y `pwd`; la cookie queda guardada. Las llamadas `POST` llevan la cabecera `X-Frappe-CSRF-Token`. |
| Token | Integraciones servidor a servidor | En el usuario: *Configuración → Claves API → Generar*. Cabecera `Authorization: token <api_key>:<api_secret>`. |

Cree un usuario de integración solo con el rol **QSG Despachador** para Liberty; nunca use el Administrador.

## Permisos

- Un usuario con rol **QSG Tecnico** (y ningún rol de gestión) solo ve las órdenes de las cuadrillas en las que figura como miembro (*QSG Cuadrilla → Miembros → Usuario*). Aplica en el escritorio, en la API REST y en la app de campo.
- `recibir_orden` requiere QSG Despachador, QSG Gerente o System Manager.
- `resumen` requiere un rol de gestión.

## API de campo

Base: `https://<servidor>/api/method/qsg_pmo.api.`

| Método | HTTP | Parámetros | Devuelve |
|---|---|---|---|
| `yo` | GET | — | usuario, nombre, cuadrillas, si es supervisor |
| `mis_ordenes` | GET | `fecha` (AAAA-MM-DD, por defecto hoy), `cuadrilla`, `incluir_cerradas` (1) | lista de órdenes del día ordenada por secuencia de ruta |
| `orden` | GET | `name` | detalle completo: datos de red, checklist, materiales, kit, historial |
| `codigos_cierre` | GET | — | códigos con su resultado (Completada / No completada) y causa |
| `cambiar_estado` | POST | `name`, `estado` (`En ruta` o `En sitio`), `lat`, `lng` | la orden actualizada; en `En sitio` calcula la distancia a la dirección |
| `guardar_checklist` | POST | `name`, `filas` = `[{"name": fila, "value": "...", "photo": "/private/files/..."}]` | la orden con el cumplimiento de cada paso |
| `cerrar` | POST | `name`, `codigo`, `notas`, `firma` (data URL PNG), `materiales` = `[{"item","qty","serial_no"}]`, `lat`, `lng` | la orden cerrada; aplica las mismas reglas del escritorio |

Las fotos se suben primero con el método estándar de Frappe y luego se guardan en la fila:

```bash
curl -X POST https://<servidor>/api/method/upload_file \
  -H "Authorization: token KEY:SECRET" \
  -F file=@cto-antes.jpg -F doctype="QSG Orden" -F docname=QSG-ORD-2026-00002 -F is_private=1
# → {"message": {"file_url": "/private/files/cto-antes.jpg", ...}}
```

### Ejemplo: un día del técnico

```bash
S=https://pmo.qsg.pr
curl -c c.txt -X POST $S/api/method/login -d usr=tecnico@qsg.pr -d pwd='Campo2026!'
curl -b c.txt "$S/api/method/qsg_pmo.api.mis_ordenes?fecha=2026-11-05"
curl -b c.txt -X POST $S/api/method/qsg_pmo.api.cambiar_estado \
  -H "X-Frappe-CSRF-Token: <token>" -H "Content-Type: application/json" \
  -d '{"name":"QSG-ORD-2026-00002","estado":"En sitio","lat":18.4201,"lng":-66.0600}'
curl -b c.txt -X POST $S/api/method/qsg_pmo.api.cerrar \
  -H "X-Frappe-CSRF-Token: <token>" -H "Content-Type: application/json" \
  -d '{"name":"QSG-ORD-2026-00002","codigo":"COMP-OK","notas":"Rx -18.4 dBm","firma":"data:image/png;base64,..."}'
```

Errores: HTTP 417 con el mensaje en `_server_messages` (por ejemplo, *«No se puede completar: faltan … pasos obligatorios»*); HTTP 403 si la orden no es de su cuadrilla.

## API de integración (Liberty)

| Método | HTTP | Parámetros | Devuelve |
|---|---|---|---|
| `recibir_orden` | POST | `customer` (opcional si hay cliente por defecto en *QSG Configuracion*), `external_order_id` y cualquier campo de *QSG Orden* (`work_type`, `subscriber_name`, `account_number`, `phone`, `address`, `municipality`, `zone`, `latitude`, `longitude`, `appointment_date`, `window_start`, `window_end`, `priority`, `hfc_node`, `olt`, `pon_port`, `splitter_cto`…) | `{name, status, created, sla_due}` |
| `estado_orden` | GET | `external_order_id`, `customer` | estado, SLA, ventana, contratista, cuadrilla, llegada estimada, cierre, retrabajo |
| `resumen` | GET | `fecha` | contadores del tablero: abiertas, SLA en riesgo, SLA vencido, en campo, programadas y completadas del día, retrabajos |

`recibir_orden` es idempotente: si la orden ya existe (mismo cliente y número), la actualiza mientras siga en *Recibida*, *Asignada a contratista* o *Reprogramada*; si ya está en campo o cerrada, responde con error. No permite tocar estado, cuadrilla, contratista ni cierre.

```bash
curl -X POST https://pmo.qsg.pr/api/method/qsg_pmo.api.recibir_orden \
  -H "Authorization: token KEY:SECRET" -H "Content-Type: application/json" \
  -d '{"external_order_id":"LPR-560001","work_type":"FTTH-INST-RES","subscriber_name":"Ana Meléndez",
       "address":"Calle Del Parque 352","municipality":"San Juan","zone":"Metro",
       "latitude":18.4489,"longitude":-66.0632,"appointment_date":"2026-11-06",
       "window_start":"08:00","window_end":"12:00"}'
# → {"message": {"name": "QSG-ORD-2026-00009", "status": "Recibida", "created": true, "sla_due": "2026-11-06 12:00:00"}}
```

## API REST genérica

Cualquier DocType se puede leer y escribir con la API estándar de Frappe, respetando permisos:

```
GET  /api/resource/QSG Orden?filters=[["status","=","Programada"]]&fields=["name","crew","sla_status"]
GET  /api/resource/QSG Orden/QSG-ORD-2026-00002
POST /api/resource/QSG Disponibilidad        {"crew":"CUA-FTTH-02","from_date":"2026-11-10","to_date":"2026-11-12","reason":"Vehículo averiado"}
PUT  /api/resource/QSG Orden/QSG-ORD-2026-00002   {"priority":"Urgente"}
GET  /api/method/frappe.desk.query_report.run?report_name=Capacidad por Contratista&filters={"date":"2026-11-05"}
```

Métodos de despacho que también se pueden llamar por API (`/api/method/run_doc_method` o desde el botón):
`QSG Plan de Despacho.generate_proposal`, `QSG Plan de Despacho.approve`, `QSG Orden.reassign` y
`qsg_pmo.qsg_pmo.doctype.qsg_orden.qsg_orden.assign_contractor`.
