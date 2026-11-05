# Cómo probar QSG PMO

Hay tres niveles de prueba. Puede hacer solo el primero para ver la herramienta funcionando, o los tres.

| Nivel | Qué prueba | Tiempo |
|---|---|---|
| 1. Probar la aplicación | Las pantallas de escritorio y la app del técnico en su celular, con datos de demostración | 30–60 min la primera vez |
| 2. Probar el código | Las 43 pruebas automáticas (motor, SLA, flujo completo, API, permisos y seguridad) | 2 min |
| 3. Probar en campo | Un técnico real con su celular, GPS y cámara, sobre un servidor con HTTPS | medio día |

---

## 1. Probar la aplicación

### Opción A: con Docker (recomendada, cualquier computadora)

**La forma más simple:** ejecute `instalacion/pc/instalar.bat` (Windows) o `instalacion/pc/instalar.sh` (Mac/Linux). Hace todo lo de abajo automáticamente. Para el celular Android, vea `instalacion/android/README.md`.

Paso a paso, si prefiere hacerlo a mano con frappe_docker:

Requisitos: Docker Desktop (Windows o Mac) o Docker en Linux, 8 GB de RAM libres.

```bash
git clone https://github.com/frappe/frappe_docker
cd frappe_docker

# 1) Lista de apps a incluir en la imagen
cat > apps.json <<'EOF'
[
  {"url": "https://github.com/frappe/erpnext", "branch": "version-16"},
  {"url": "https://github.com/ingcpmo/PMO", "branch": "main"}
]
EOF
# Si el repositorio es privado, use https://<usuario>:<token>@github.com/ingcpmo/PMO

# 2) Construir la imagen con ERPNext + QSG PMO
docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-16 \
  --build-arg=APPS_JSON_BASE64=$(base64 -w 0 apps.json) \
  --tag=qsg-pmo:latest \
  --file=images/layered/Containerfile .

# 3) Usar esa imagen en el ejemplo de un solo archivo
sed -i 's#frappe/erpnext:v[0-9.]*#qsg-pmo:latest#g' pwd.yml
sed -i 's#--install-app erpnext#--install-app erpnext --install-app qsg_pmo#' pwd.yml
docker compose -p qsg -f pwd.yml up -d

# 4) Esperar a que termine de crear el sitio (2–5 min) y cargar la demostración
docker compose -p qsg -f pwd.yml logs -f create-site      # hasta ver que termina
docker compose -p qsg -f pwd.yml exec backend bench --site frontend execute qsg_pmo.demo.crear
```

Abra **http://localhost:8080** con usuario `Administrator` y contraseña `admin`. En Mac, cambie `base64 -w 0` por `base64 -i apps.json`.

### Opción B: con bench (servidor Ubuntu 24.04)

```bash
# requisitos: Python 3.14, Node 24, MariaDB 11, Redis, yarn
pip install frappe-bench
bench init --frappe-branch version-16 frappe-bench && cd frappe-bench
bench get-app erpnext --branch version-16
bench get-app https://github.com/ingcpmo/PMO --branch main
bench new-site qsg.local --admin-password admin --install-app erpnext --install-app qsg_pmo
bench --site qsg.local execute qsg_pmo.demo.crear
bench start        # http://qsg.local:8000  (agregue "127.0.0.1 qsg.local" a /etc/hosts)
```

### Recorrido sugerido (escritorio)

La demostración crea 2 contratistas, 4 cuadrillas, 8 órdenes de hoy, un plan de despacho aprobado y el técnico `tecnico@qsg.pr` / `Campo2026!` en la cuadrilla CUA-FTTH-01.

1. **Tablero**: menú *QSG PMO*. Verá los contadores de órdenes abiertas, SLA y cuadrillas en campo.
2. **Órdenes**: abra una; vea el SLA, la ventana, la cuadrilla, el checklist y el historial.
3. **Asignar a contratista**: en la lista, marque órdenes *Recibida* → *Acciones → Asignar a contratista*.
4. **Plan de despacho**: *QSG Plan de Despacho → Nuevo* → fecha de mañana → *Generar propuesta* → revise → *Aprobar y publicar*.
5. **Reasignar**: en una orden programada, *Despacho → Reasignar*, escriba el motivo y vea el historial.
6. **Ausencia**: cree una *QSG Disponibilidad* para una cuadrilla y vuelva a generar un plan: el motor ya no la usa.
7. **Reportes**: *Ocupación de Cuadrillas*, *Capacidad por Contratista*, *Liquidación de Contratistas*.
8. **Calidad**: cree una *QSG Encuesta* para una orden completada y una *QSG Evaluacion Contratista* del mes.

### Recorrido sugerido (celular)

1. Conecte el celular a la misma red Wi-Fi que la computadora.
2. Averigüe la IP de la computadora (`ipconfig` en Windows, `ipconfig getifaddr en0` en Mac).
3. En el celular abra `http://<IP>:8080/campo` (Docker) o `http://<IP>:8000/campo` (bench).
4. Entre con `tecnico@qsg.pr` / `Campo2026!`.
5. Toque una orden → *Salir hacia el sitio* → *Llegué al sitio* → tome las fotos y escriba las mediciones → *Completar* → firme → *Cerrar orden*.
6. Pruebe también *No completada → CLI-AUS* y el intento de completar sin evidencia (lo bloquea).
7. Para instalarla como app: en Android, menú de Chrome → *Agregar a la pantalla principal*; en iPhone, Safari → *Compartir → Agregar a inicio*.

> **GPS en la red local.** Los navegadores solo dan la ubicación en páginas con HTTPS. Con `http://<IP>` todo funciona, excepto que la llegada se registra sin coordenadas. Para probar el GPS use el nivel 3 o un túnel HTTPS temporal: `cloudflared tunnel --url http://localhost:8080` y abra en el celular la dirección `https://….trycloudflare.com/campo` que le muestra.

En la computadora también puede ver la vista de celular: Chrome → F12 → icono de teléfono (*Toggle device toolbar*) → iPhone 14 → `http://localhost:8080/campo`.

---

## 2. Probar el código

```bash
# Docker
docker compose -p qsg -f pwd.yml exec backend bash -c \
  "bench --site frontend set-config allow_tests true && bench --site frontend run-tests --app qsg_pmo"

# bench
bench --site qsg.local set-config allow_tests true
bench --site qsg.local run-tests --app qsg_pmo
```

Resultado esperado: `Ran 8 tests … OK` (integración) y `Ran 17 tests … OK` (motor y SLA).

| Archivo | Qué comprueba |
|---|---|
| `qsg_pmo/tests/test_engine.py` | Motor de asignación (habilidad, capacidad, ventana, distancia, zona, prioridad, contratista ya asignado, bonificación por calidad, órdenes ya programadas) y cálculo del SLA. No usa base de datos. |
| `qsg_pmo/tests/test_flujo.py` | Orden → plan → aprobación → cierre con evidencia → encuesta → evaluación; asignación a contratista → reasignación con motivo → ausencia → garantía y retrabajo → reportes; orden duplicada. |
| `qsg_pmo/tests/test_api.py` | El técnico solo ve su cuadrilla (app, API REST y escritorio); flujo del técnico por API (en ruta, en sitio, checklist, cierre con firma, bloqueo sin evidencia); no completada por cliente; recepción de órdenes de Liberty (crear y actualizar); resumen del tablero. |

Para correr un solo archivo: `bench --site qsg.local run-tests --module qsg_pmo.tests.test_api`.

Para probar solo el motor y el SLA sin instalar Frappe (Python 3.11 o más):

```bash
git clone https://github.com/ingcpmo/PMO && cd PMO
python -m unittest qsg_pmo.tests.test_engine      # Ran 17 tests … OK
```

---

## 3. Probar en campo (piloto)

1. Servidor con dominio y HTTPS (por ejemplo `pmo.qsg.pr`): `bench setup production <usuario>` y `bench setup lets-encrypt <sitio>`, o Frappe Cloud.
2. Cargue los datos reales: contratistas, cuadrillas con sus miembros y **el usuario de cada técnico** (rol *QSG Tecnico*), tipos de trabajo, rangos de medición y códigos de cierre del contrato de Liberty.
3. Elija una cuadrilla y 1–2 semanas. Cada mañana el despachador aprueba el plan y el técnico trabaja solo desde `/campo`.
4. Revise al final de cada día: llegadas fuera de rango, órdenes bloqueadas por evidencia, tiempos de salida/llegada/cierre y el reporte de ocupación.
5. Anote lo que el técnico no pudo hacer desde el celular; eso define la versión siguiente (modo sin señal, notificaciones al suscriptor).

## Compatibilidad del celular

| Elemento | Soporte |
|---|---|
| Navegadores | Chrome Android 100+, Safari iOS 15+, Samsung Internet, Edge |
| Instalación | App web instalable (manifest, icono, pantalla completa); no requiere tienda |
| Cámara | Abre la cámara trasera directamente (`capture="environment"`); reduce la foto a 1600 px antes de subirla |
| GPS | Geolocalización del navegador con alta precisión (requiere HTTPS) |
| Firma | Con el dedo, en un lienzo táctil |
| Pantallas | Diseño para 360–430 px de ancho, respeta el notch y la barra inferior del iPhone; también funciona en tableta |
| Modo oscuro | Automático según el teléfono |
| Sin señal | Avisa que está sin conexión; guardar sin señal queda para la siguiente versión |
| Escritorio en el celular | Supervisores y despachadores pueden usar el escritorio de Frappe en el celular (tablero, listas, reportes), que es adaptable |
