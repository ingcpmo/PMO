# QSG PMO

Herramienta de gestión de proyectos y operación de cuadrillas para instalaciones y reparaciones **HFC** y **FTTH** (última milla, reconectorizaciones, residencial y empresarial) en Puerto Rico. Es una app de [Frappe](https://github.com/frappe/frappe) que se instala sobre [ERPNext](https://github.com/frappe/erpnext) v16.

- Diseño: [`docs/design/qsg-pmo-design.md`](docs/design/qsg-pmo-design.md)
- Cobertura del flujo end-to-end: [`docs/design/cobertura-end-to-end.md`](docs/design/cobertura-end-to-end.md)
- Cómo probar la aplicación y el código: [`docs/pruebas.md`](docs/pruebas.md)
- API para la app de campo y para Liberty: [`docs/api.md`](docs/api.md)
- Investigación que llevó a esta base: [`research/`](research/)

## Qué incluye (v0.3)

| Área | Contenido |
|---|---|
| Catálogos | Zonas de PR con municipios, habilidades, contratistas, cuadrillas, tipos de trabajo FTTH/HFC, códigos de cierre, plantillas de checklist con rangos de medición |
| Órdenes | `QSG Orden` con cita, SLA calculado (en tiempo, en riesgo, vencido, cumplido, incumplido), checklist de evidencia copiado de la plantilla, mediciones validadas por rango, materiales y seriales, firma, código de cierre |
| Reglas de cierre | No deja completar sin la evidencia obligatoria, con mediciones fuera de rango o con un código de cierre que no corresponde |
| Despacho | `QSG Plan de Despacho`: genera una propuesta con el motor de asignación por reglas (habilidad, capacidad, ventana, distancia, zona) y, al aprobarla, asigna las órdenes y crea las solicitudes de materiales de bodega por cuadrilla |
| Calidad | `QSG Encuesta` de satisfacción y `QSG Evaluacion Contratista` con puntaje ponderado y categoría A/B/C |
| Contratistas | Asignación individual o masiva a contratista, reasignación con motivo e historial, cuadrillas activas por contratista |
| Capacidad | Ausencias de cuadrilla, agenda en calendario, reportes *Ocupación de Cuadrillas* y *Capacidad por Contratista* |
| Post-operación | Garantía configurable y detección de retrabajo atribuido al contratista original |
| Bodega | Solicitud de materiales por cuadrilla al aprobar el plan y salida de inventario al completar la orden |
| Tablero | Espacio de trabajo *QSG PMO* con contadores en vivo y reporte *Liquidación de Contratistas* |
| App de campo | `/campo`: app web para el celular del técnico, instalable en la pantalla de inicio. Ruta del día, salir y llegar con GPS, fotos con la cámara, mediciones con rango, cierre con código, materiales y firma del cliente |
| API | `qsg_pmo.api`: métodos de campo y de integración (`recibir_orden`, `estado_orden`, `resumen`), más la API REST de Frappe. Un técnico solo ve las órdenes de su cuadrilla |
| Roles | QSG Gerente, Despachador, Supervisor Contratista, Técnico, Bodega |

Los rangos de medición y los códigos de cierre de los datos semilla son **valores típicos de la industria**; hay que reemplazarlos por los del manual y el contrato de Liberty.

## Instalación

**Para probar en una PC o en Android, use la carpeta [`instalacion/`](instalacion/)**: `instalacion/pc/instalar.bat` instala todo con Docker y `instalacion/android/` genera la app QSG Campo (APK).

Instalación manual sobre un bench existente:

Requisitos: un bench de Frappe v16 (Python 3.14, Node 24, MariaDB, Redis) con ERPNext v16.

```bash
cd frappe-bench
bench get-app https://github.com/ingcpmo/PMO --branch main
bench --site <tu-sitio> install-app qsg_pmo
```

Al instalarse crea los roles y carga los datos semilla (habilidades, zonas de Puerto Rico, códigos de cierre, plantillas de checklist y tipos de trabajo).

Para cargar una demostración (contratistas, cuadrillas, órdenes de hoy, plan aprobado y el técnico `tecnico@qsg.pr` / `Campo2026!`):

```bash
bench --site <tu-sitio> execute qsg_pmo.demo.crear
```

La app del técnico queda en `https://<tu-sitio>/campo`. Instalación con Docker y recorrido de prueba: [`docs/pruebas.md`](docs/pruebas.md).

## Pruebas

```bash
bench --site <tu-sitio> set-config allow_tests true
bench --site <tu-sitio> run-tests --app qsg_pmo
```

- `qsg_pmo/tests/test_engine.py`: motor de asignación y cálculo de SLA (sin base de datos).
- `qsg_pmo/tests/test_flujo.py`: flujo completo orden → plan → aprobación → cierre → encuesta → evaluación, y asignación a contratista → reasignación → ausencias → garantía y retrabajo → reportes.
- `qsg_pmo/tests/test_api.py`: API de campo e integración y permisos del técnico por cuadrilla.

## Estructura

```
qsg_pmo/
├── api.py               # API de campo e integración
├── permissions.py       # el técnico solo ve su cuadrilla
├── demo.py              # datos de demostración
├── www/campo.*          # app de campo (/campo)
├── public/              # JS, CSS, manifest e iconos de la app de campo
├── assignment/          # motor de asignación y SLA (Python puro)
├── qsg_pmo/doctype/     # DocTypes del módulo "QSG PMO"
├── install.py           # roles y datos semilla
├── hooks.py             # dependencias, instalación y planificador (SLA cada 15 min)
└── tests/
docs/design/             # documento de diseño
research/                # investigación de herramientas
```

## Licencia

MIT
