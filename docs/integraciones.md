# Integraciones: qué se conectó y qué se recomienda (v0.4)

**Fecha:** 5 de noviembre de 2026. Complementa la investigación de [`research/`](../research/).
Leyenda: ✅ conectado en v0.4 · 🟡 listo para conectar con configuración · ⏭️ recomendado para la próxima versión.

| Sistema | Para qué | Estado | Cómo |
|---|---|---|---|
| **Liberty** (órdenes y cierres) | Recibir órdenes y devolver estados | ✅ API existente (`recibir_orden`, `estado_orden`) · ✅ órdenes desde texto libre (correo, ticket) · ⏭️ webhook de cierre | Ver §1 |
| **NWS San Juan** (clima) | Suspender trabajo o trabajo en altura por alertas | 🟡 casilla en *QSG Configuracion IA* | `api.weather.gov/alerts/active?area=PR`, cada hora |
| **LUMA** (energía) | No mandar cuadrillas a zonas sin luz | ✅ incidencias manuales por zona | No hay API pública (§3) |
| **OSRM + OpenStreetMap de PR** | Tiempos de viaje reales por carretera | 🟡 campo `osrm_url` (ya existía en *QSG Configuracion*) | §4 |
| **Traccar** | GPS continuo de los vehículos | 🟡 servidor, usuario y dispositivos en la configuración | §5 |
| **Claude (Anthropic)** | Interpretar textos, resumen del día, asistente | 🟡 clave de API en la configuración | SDK oficial `anthropic`, modelo `claude-opus-5-5` |
| **Ollama** (modelo local) | Lo mismo sin que los datos salgan | 🟡 dirección del servidor Ollama | `/api/chat` con herramientas y JSON |
| **ERPNext** (bodega) | Stock del camión y de la bodega central, seriales | ✅ lectura de `Bin` y `Serial No` | Ya instalado |
| **VROOM** | Optimización a gran volumen | ⏭️ el optimizador propio cubre el volumen actual | Campo `vroom_url` ya existe |
| **WhatsApp Business / SMS** | «Su técnico va en camino», confirmar la cita el día antes | ⏭️ | Reduce las visitas fallidas por cliente ausente que mide el puntaje de zona |

## 1. Liberty

No se encontró documentación pública del sistema de órdenes de campo de Liberty en Puerto Rico. Las ofertas de empleo de Liberty Latin America mencionan herramientas internas como un sistema de gestión de red (NMCS), *Access Care*, un CIS/CRM y la programación de citas en un sistema CSG, sin confirmar cuál entrega las órdenes a los contratistas. Por eso QSG PMO ofrece tres entradas que no dependen de ese detalle:

1. **API** (`qsg_pmo.api.recibir_orden`): idempotente por número de orden del cliente, con campos permitidos e IPs autorizadas.
2. **Importación** de archivos con *Data Import* de Frappe.
3. **Texto libre** (nuevo): se pega el correo o el ticket en el tablero y sale la orden; si se pega dos veces no se duplica.

Para los cierres se recomienda un **Webhook** de Frappe sobre `QSG Orden` (estado, código de cierre, mediciones y enlaces a las fotos) cuando Liberty indique el destino.

## 2. Clima: Servicio Nacional de Meteorología

- Fuente: `https://api.weather.gov/alerts/active?area=PR` (GeoJSON, sin clave; exige un *User-Agent*).
- El área de cada alerta trae municipios o regiones del pronóstico («Northeast», «San Juan and Vicinity»); QSG las traduce a sus zonas.
- Impacto: *Suspender* (huracán, tormenta tropical, inundación repentina, tornado, marejada, viento extremo), *Sin altura* (vigilancias, viento fuerte, tronadas severas) o *Precaución* (inundación menor, calor).
- Por defecto llega como **recomendación** para que despacho decida; se puede pedir que cree la incidencia sola.
- En el entorno de desarrollo la salida a `api.weather.gov` estaba bloqueada: la lectura se probó con alertas de ejemplo con la misma forma de la API. En un servidor con internet funciona sin cambios.

## 3. LUMA

LUMA publica los clientes sin servicio en su portal, y la prensa reporta esas cifras a diario, pero no hay una API pública documentada; en 2023 pidió a un agregador independiente que dejara de extraer esos datos. Por eso las interrupciones se registran como **QSG Incidencia Zona** (tipo *Apagón LUMA*). Con impacto *Suspender*, la zona no recibe trabajo en el plan, y la orden queda sin asignar con el motivo visible.

## 4. Tiempos reales con OSRM

Geofabrik publica a diario el extracto de OpenStreetMap de Puerto Rico (en la lista de estados de EE. UU. y dentro del extracto de Centroamérica). Para levantar OSRM en el mismo servidor:

```bash
mkdir osrm && cd osrm
curl -LO https://download.geofabrik.de/north-america/us/puerto-rico-latest.osm.pbf
docker run -t -v "$PWD:/data" ghcr.io/project-osrm/osrm-backend osrm-extract -p /opt/car.lua /data/puerto-rico-latest.osm.pbf
docker run -t -v "$PWD:/data" ghcr.io/project-osrm/osrm-backend osrm-partition /data/puerto-rico-latest.osrm
docker run -t -v "$PWD:/data" ghcr.io/project-osrm/osrm-backend osrm-customize /data/puerto-rico-latest.osrm
docker run -d -p 5000:5000 -v "$PWD:/data" ghcr.io/project-osrm/osrm-backend osrm-routed --algorithm mld /data/puerto-rico-latest.osrm
```

Luego, en *QSG Configuracion*, **URL de OSRM** = `http://<servidor>:5000`. El optimizador pide una tabla de tiempos por plan (hasta 100 puntos; con más usa la estimación) y, si OSRM no responde, sigue con la estimación por terreno. Confirme la ruta exacta del archivo en Geofabrik antes de automatizar la descarga.

## 5. GPS continuo con Traccar

La app de campo envía la ubicación mientras está abierta. Para seguimiento continuo de los vehículos (también con la app cerrada), Traccar recibe rastreadores GPS o teléfonos con la app OsmAnd (protocolo OsmAnd, puerto 5055). QSG lee cada 5 minutos `GET /api/positions` de Traccar y guarda las posiciones como **QSG Ubicacion** (fuente *Traccar*). Las posiciones entran a Traccar por sus protocolos, no por su API REST.

Configuración: *QSG Configuracion IA → Seguimiento GPS*: servidor, usuario, contraseña y una línea por vehículo `deviceId=CÓDIGO-DE-CUADRILLA`.

## 6. Modelos de lenguaje

| | Claude | Ollama |
|---|---|---|
| Uso | Externo, por API | Local, en su servidor |
| Configuración | Proveedor *Claude* + clave de API | Proveedor *Ollama* + dirección (`http://ollama:11434`) |
| Modelo por defecto | `claude-opus-5-5` | `qwen2.5:7b` |
| Herramientas del asistente | Sí (solo lectura) | Sí, con modelos que soportan herramientas (Qwen 2.5, Llama 3.1+) |
| Datos personales | No se envían salvo que se active la casilla | Se quedan en su red |

Ambos son opcionales: con *Ninguno* todo funciona con reglas.

## 7. Despliegues en Centroamérica

Liberty Latin America opera también en Costa Rica (Liberty Costa Rica) y Panamá (C&W Panamá), entre otros mercados. QSG PMO quedó preparado para replicarse:

| Qué cambia por país | Dónde |
|---|---|
| Municipios o cantones con su terreno y zona sugerida | Un diccionario como `PUERTO_RICO` en `inteligencia/territorio.py` (`PAISES`) |
| Zonas operativas | *QSG Zona* (pantalla) |
| Zona horaria, moneda e idioma | Asistente de configuración de ERPNext (Costa Rica: `America/Costa_Rica`, colón; Panamá: `America/Panama`, dólar) |
| Tipos de trabajo, códigos de cierre, rangos de medición y SLA | Catálogos (pantalla), según el contrato de cada país |
| Clima | El NWS cubre Puerto Rico; en Centroamérica se usaría el servicio meteorológico de cada país con el mismo formato de incidencia |
| Terreno e islas | El factor de montaña y la regla de islas (lancha) se configuran por zona |

## Fuentes

- Geofabrik, extracto de Centroamérica (incluye Puerto Rico): <https://download.geofabrik.de/central-america.html>
- OpenStreetMap Wiki, proyectos de Puerto Rico (extracto diario en Geofabrik): <https://wiki.openstreetmap.org/wiki/Puerto_Rico_Projects>
- `osrm-extract` (manual): <https://manpages.org/osrm-extract>
- Traccar: las posiciones entran por protocolos como OsmAnd, no por la API REST: <https://www.traccar.org/forums/reply/84522/> · OsmAnd como rastreador: <https://flespi.com/devices/osmand>
- Ollama, herramientas en `/api/chat`: <https://www.caktusgroup.com/blog/2025/12/03/learning-llm-basics-ollama-function-calling/> · formato JSON: <https://zenn.dev/7shi/articles/20251231-ollama-tools?locale=en>
- API de alertas del NWS (catálogo): <https://apis.apievangelist.com/store/weather-gov-alerts-api/> · <https://www.weather.gov/>
- LUMA, datos de clientes sin servicio en su portal y en la prensa: <https://www.metro.pr/noticias/2023/06/18/mas-de-83-mil-abonados-se-encuentran-sin-servicio-de-energia-electrica-este-domingo/> · <https://www.metro.pr/noticias/2026/08/17/mas-de-93000-clientes-de-luma-energy-estan-sin-servicio/>
- Liberty Latin America, segmentos y herramientas internas en ofertas de empleo: <https://bitscale.ai/directory/liberty-latin-america> · <https://www.getclera.com/jobs/liberty-latin-america-communications-inc/line-technician-san-juan> · <https://dejobs.org/virtual-usa/installations-coordinator/621F97B33E02480F9F1AC497CBE67FEF/job>
