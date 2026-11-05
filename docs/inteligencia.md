# Inteligencia operativa de QSG PMO (v0.4)

**Qué agrega:** que la PMO procese las solicitudes y tome decisiones para que las cuadrillas rindan más, manejen menos, no se queden con material en el camión, recojan en bodega lo justo y no dejen pendientes en ninguna instalación. Todo sobre lo que ya existía: **ningún flujo anterior cambió**. Las funciones nuevas son opcionales y se activan en *QSG Configuracion IA*.

## 1. Cómo decide

```
Solicitud de Liberty ──► interpretación (reglas + IA opcional) ──► QSG Orden
                                                                     │
           clima NWS · apagones LUMA · vías cerradas ──► incidencias por zona
                                                                     ▼
 historial de órdenes ──► afinidad cuadrilla-zona ──►  OPTIMIZADOR  ◄── GPS: velocidad real por zona
 stock del camión ─────► materiales netos ─────────►  (propone)    ◄── terreno, ferry, B2B
                                                                     │
                                                   el despachador aprueba (como siempre)
                                                                     ▼
 app de campo ──► GPS cada 2 min ──► tablero /despacho ──► alertas y recomendaciones
                                   (llegará tarde → mejor cuadrilla; detenida; sin señal;
                                    pendientes de evidencia; materiales; mover cuadrillas)
```

**Regla de oro:** la inteligencia **propone y explica**; una persona **aprueba**. El modelo de lenguaje nunca asigna órdenes ni cambia datos.

## 2. Qué hace cada pieza

| Pieza | Qué resuelve | Dónde |
|---|---|---|
| **Optimizador de rutas** | Parte del plan del motor por reglas y lo mejora: reordena paradas, mueve órdenes entre cuadrillas e inserta las que quedaron fuera. Nunca devuelve un plan peor que el de reglas. | Botón **Inteligencia → Optimizar rutas** en el plan de despacho |
| **Terreno de Puerto Rico** | La cordillera central se maneja al 65 % de la velocidad (configurable); Vieques y Culebra solo con cuadrillas habilitadas para la lancha. El motor anterior asumía la misma velocidad en toda la isla y prometía llegadas imposibles en la montaña. | `inteligencia/territorio.py`, `rutas.py` |
| **B2B vs. hogares** | El atraso con un cliente empresarial pesa el doble (configurable). Se agregó «Reparación HFC empresarial», que faltaba. | Optimizador, semilla |
| **GPS de las cuadrillas** | La app de campo envía la ubicación cada 2 minutos (con la app abierta, de 6:00 a 20:00). Sin señal, guarda las lecturas y las envía después. También puede leer rastreadores Traccar de los vehículos. | `public/js/campo_gps.js`, `QSG Ubicacion` |
| **Alertas de seguimiento** | *Llegará tarde* (con la mejor cuadrilla alternativa), *detenida fuera de ruta*, *sin señal*, *en sitio sin marcar llegada*. | Tablero `/despacho`, `QSG Recomendacion` |
| **Mejor cuadrilla** | Para una avería urgente o una orden atrasada: quién llega antes desde donde está ahora, con capacidad, habilidad y afinidad con la zona, y por qué. Se asigna con un clic (queda el motivo en el historial). | Botón **Mejor cuadrilla** en la orden y en el tablero |
| **Zonas** | Puntaje 0–100 por zona (primera visita, SLA, productividad, retrabajo, visitas fallidas) con observaciones accionables; demanda contra capacidad de mañana y qué cuadrillas mover desde zonas vecinas holgadas. | Asistente, recomendaciones cada hora |
| **Materiales** | Qué recoger en bodega **descontando lo que ya trae el camión**, qué devolver (equipos con serial nunca sobran en el camión), qué falta en la bodega central, equipos estancados más de 7 días y cuadrillas que gastan mucho más que el kit. | Recomendaciones, botón en el plan aprobado, casilla en la configuración |
| **Pendientes** | Antes de cerrar y durante el día: evidencia que falta, mediciones fuera de rango, serial del equipo, firma, órdenes trabadas, fallidas sin reprogramar, cierres sin salida de inventario, materiales sin recoger. | Recomendaciones, asistente |
| **Clima e incidencias** | Alertas del NWS de San Juan → *Suspender* (huracán, inundación repentina), *Sin altura* (viento: no postes ni escaleras) o *Precaución*. Apagones de LUMA, inundaciones y vías cerradas se registran a mano. Una zona con incidencia no recibe trabajo en el plan. | `QSG Incidencia Zona` |
| **Órdenes desde texto** | Pegue el correo o mensaje de Liberty: sale la orden con tipo, prioridad, municipio, zona, fecha, ventana, teléfono y cuenta. Pegar dos veces el mismo texto no la duplica. | Tablero → Asistente |
| **Resumen del día y asistente** | Estado general, acciones priorizadas y números clave; preguntas en lenguaje natural («¿qué cuadrillas van atrasadas?»). | Tablero |

## 3. Modelo de lenguaje: externo, local o ninguno

| Proveedor | Cuándo | Datos |
|---|---|---|
| **Ninguno** (de fábrica) | Siempre funciona: reglas y plantillas. | No salen del servidor. |
| **Claude** (Anthropic) | Mejor comprensión de textos libres, resúmenes y asistente. Modelo por defecto `claude-opus-5-5`; con respaldo automático del servidor si el modelo declina una solicitud. Requiere clave de API e internet. | Por defecto **no** se envían teléfonos, correos, cuentas, nombres ni calles (se anonimizan). Los datos del tablero que recibe son agregados. |
| **Ollama** (local) | Sin internet o cuando los datos no deben salir. Modelo sugerido `qwen2.5:7b` en un servidor con GPU o una PC potente. | No salen de su red. |

Lo que devuelve el modelo se **valida**: el tipo de trabajo tiene que existir en el catálogo y el municipio en Puerto Rico; si no, se usan las reglas.

## 4. Configuración (*QSG Configuracion IA*)

| Sección | Valores de fábrica |
|---|---|
| Modelo de lenguaje | Ninguno · sin datos personales |
| Optimización | Terreno y lancha considerados · montaña 0.65 · lancha 150 min · B2B x2 · afinidad 20 min · 5 s |
| GPS | Encendido · cada 120 s · alerta sin señal 20 min · detenida 30 min · se guarda 90 días |
| Materiales | **Ajuste al camión apagado** (el plan pide el kit completo como antes) · margen 10 % · 1 repuesto por equipo con serial |
| Clima | Apagado (requiere salida a `api.weather.gov`) · incidencias automáticas apagadas |
| Recomendaciones | Encendidas (cada 15 min hoy, cada hora para mañana) |

## 5. Lo que se cambió en archivos existentes

Solo se **agregaron** líneas; nada se borró ni cambió de comportamiento:

| Archivo | Cambio |
|---|---|
| `qsg_pmo/hooks.py` | Bloque nuevo al final: tareas programadas, semilla complementaria, botones de inteligencia y el ajuste opcional de materiales al aprobar. |
| `qsg_pmo/www/campo.html` | Una línea que carga `campo_gps.js`. |
| `qsg_pmo/tests/test_flujo.py` | La prueba del flujo ya no falla cuando el sitio tiene la demostración cargada. |
| `instalacion/pc/Dockerfile` y `pyproject.toml` | SDK `anthropic` (opcional; sin internet la imagen se construye igual). |

## 6. Cómo se verificó

- **51 pruebas sin base de datos** (motor, SLA e inteligencia) y **38 de integración** sobre ERPNext v16 real en Docker: todas en verde. Incluyen que el optimizador nunca empeora el plan del motor por reglas en 12 días simulados de Puerto Rico.
- La **auditoría de seguridad** existente sigue bloqueando los **34 de 34 ataques**, y la **simulación de una orden de Liberty** de inicio a fin pasa completa.
- El tablero se probó en Chromium: sin errores de JavaScript, mapa, pestañas, interpretación de texto y resumen del día.
- Workflow **Pruebas** en GitHub: repite todo lo anterior en cada cambio.

## 7. Límites conocidos

- Las coordenadas de los municipios son del casco urbano: sirven de respaldo cuando la orden llega sin GPS (queda marcada como «ubicación aproximada»), no para navegar.
- El factor de montaña (0.65) es un supuesto inicial: se reemplaza solo por la velocidad real que mide el GPS cuando hay suficientes datos de cada zona.
- La app abierta envía el GPS; con la pantalla apagada el teléfono puede pausarlo. Para seguimiento continuo de vehículos, use rastreadores con Traccar.
- LUMA no publica una API de apagones: las incidencias de energía se registran a mano.
- Las alertas del NWS y los tiempos de OSRM requieren salida a internet desde el servidor.
