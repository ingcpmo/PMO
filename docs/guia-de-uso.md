# Guía de uso de QSG PMO (con inteligencia operativa)

Guía práctica por rol. Lo que ya funcionaba sigue igual; aquí se explica cómo aprovechar lo nuevo.

## Probar sin instalar nada

- **App completa con datos de demostración:** [GitHub Codespaces](https://github.com/codespaces/new?hide_repo_select=true&ref=claude%2Foptimistic-noether-2uct53&repo=1446223164&quickstart=1). En el tablero, **▶ Simular jornada** mueve las cuadrillas por GPS, cierra órdenes y a mitad del día entra una avería urgente para resolver con **Mejor cuadrilla**. Usuarios en [`.devcontainer/LEAME.md`](../.devcontainer/LEAME.md).
- **Motor inteligente:** [notebook de Google Colab](https://colab.research.google.com/github/ingcpmo/PMO/blob/claude/optimistic-noether-2uct53/docs/simulaciones/QSG_PMO_Colab.ipynb).

## Antes de empezar (una sola vez, gerencia)

1. **Cliente por defecto:** *QSG Configuracion → Cliente por defecto* = Liberty (lo usan la API y las órdenes desde texto).
2. **Cuadrillas:** cada una con **punto de salida** (latitud y longitud), **turno**, **habilidades** y, si bodega lo controla, su **almacén** (el camión).
3. **Técnicos:** cada usuario técnico agregado como **miembro** de su cuadrilla. Así la app de campo sabe a qué cuadrilla pertenece el GPS.
4. ***QSG Configuracion IA*** (todo tiene valores de fábrica razonables):
   - *Cuadrillas habilitadas para Vieques y Culebra* si alguna cruza en la lancha.
   - *Artículos con serial*: los códigos de ONT, módems y routers.
   - *Descontar el stock del camión* cuando bodega tenga el inventario de los camiones al día.
   - *Proveedor de IA*: déjelo en **Ninguno** para empezar; todo funciona con reglas.
5. Abra el **tablero de despacho**: `https://<su-servidor>/despacho`.

## Despachador

### La tarde anterior: planificar mañana

1. Revise en **QSG Recomendacion** (o en el tablero) lo que el sistema ya detectó para mañana:
   - *Movimiento de cuadrilla*: una zona pide más trabajo del que puede cubrir y otra vecina está holgada.
   - *Zona*: ni moviendo cuadrillas alcanza; pida apoyo al contratista o reprograme lo de baja prioridad.
   - *Materiales*: falta material en la bodega central para alguna cuadrilla.
2. Cree el **Plan de Despacho** de mañana → **Generar propuesta** (motor por reglas, como siempre).
3. **Inteligencia → Optimizar rutas.** En segundos verá:
   - cuántas órdenes más asigna y cuántos km por orden ahorra contra el motor por reglas,
   - una explicación en viñetas: riesgos, órdenes sin asignar y por qué, cuadrillas llenas, islas y clima.
4. Revise y **Aprobar y publicar**, igual que antes. Si no le convence, vuelva a **Generar propuesta**: el plan por reglas sigue disponible.

> Una orden sin GPS se ubica en el centro de su municipio y queda marcada como «ubicación aproximada». Confirme la dirección.

### Durante el día: el tablero `/despacho`

| Parte | Qué mirar |
|---|---|
| **Indicadores** | Órdenes del día, completadas, en campo, sin asignar, SLA en riesgo y vencido, alertas del GPS. |
| **Mapa** | Cuadrillas en su última ubicación (rojo si tienen una alerta grave, gris si no han enviado GPS hoy). Órdenes por color de estado; las empresariales más grandes; las de ubicación aproximada con borde punteado. Círculo rojo = zona con incidencia. |
| **Alertas** | *Llegará tarde*: avise al cliente o use **Mejor cuadrilla**. *Detenida fuera de ruta* y *Sin señal*: llame a la cuadrilla. *En sitio sin marcar llegada*: recuérdele marcar «En sitio». |
| **Recomendaciones** | Cada una dice qué pasó y qué hacer. Márquela **Resuelta** o **Descartar**; lo descartado no se vuelve a proponer en 12 horas. |
| **Sin asignar** | Órdenes del día sin cuadrilla → **Mejor cuadrilla** → **Asignar** (pide un motivo y queda en el historial). |
| **Asistente** | Preguntas sobre la operación (requiere un modelo de lenguaje) y **Nueva orden desde un correo o mensaje**. |
| **Resumen del día** | Estado general, acciones priorizadas y números clave, listos para el reporte. |

### Avería urgente o cliente empresarial sin servicio

1. Pegue el mensaje en **Asistente → Nueva orden desde un correo o mensaje → Interpretar**. Revise los campos (tipo, prioridad, municipio, ventana, teléfono) y **Crear la orden**.
2. En el mapa, abra la orden → **Mejor cuadrilla**: ordena las cuadrillas por cuán rápido llegan desde donde están ahora, si les queda cupo y si rinden bien en esa zona.
3. **Asignar.** La cuadrilla la ve de inmediato en su app.

### Apagón, inundación o vía cerrada

Cree una **QSG Incidencia Zona**: zona, tipo (*Apagón LUMA*, *Inundación*, *Vía cerrada*, *Alerta de clima*…), impacto e intervalo.
- **Suspender**: el plan no le asigna trabajo a esa zona y las órdenes quedan sin asignar con el motivo.
- **Sin altura**: no se programan trabajos que requieren la habilidad ALTURA (postes y escaleras).
- **Precaución**: solo aviso.

Desactívela cuando termine. Si gerencia activó el clima del NWS, las alertas llegan solas como recomendación.

## Supervisor de contratista

- El tablero `/despacho` y los pendientes le muestran **solo sus cuadrillas**.
- Revise las alertas de sus cuadrillas y los **pendientes** de evidencia: una orden no se puede completar sin las fotos y mediciones obligatorias.
- Las recomendaciones de reasignación las decide despacho.

## Técnico (app de campo)

1. Abra **QSG Campo** (app de Android, de iPhone o `/campo` en el navegador) y acepte los permisos de **ubicación** y **cámara**.
2. Con la app abierta, en horario de trabajo (6:00 a 20:00), envía su ubicación cada 2 minutos. **No tiene que hacer nada.** Si no hay señal, la guarda y la envía al volver la señal.
3. Marque **En ruta** al salir y **En sitio** al llegar. Si lleva más de 10 minutos en la dirección sin marcar, despacho recibe un recordatorio.
4. Antes de cerrar, complete el checklist: fotos, mediciones dentro de rango, serial del equipo, materiales y firma. La app no deja completar si falta algo obligatorio.

## Bodega

- **Recomendaciones de Materiales** (cada hora para el día siguiente):
  - *Falta material en bodega*: reponga o avise a despacho para reprogramar.
  - *Devolver sobrante*: el camión trae más de lo que necesita; reciba la devolución al cierre del turno.
  - *Equipo estancado*: un ONT o módem lleva más de 7 días en el camión sin instalarse.
- En un **plan aprobado**: **Inteligencia → Ajustar materiales al stock del camión** reduce las solicitudes a lo que falta en cada camión. Con la casilla de la configuración encendida, se hace sola al aprobar.

## Gerencia

- **Resumen del día** en el tablero, para el informe a Liberty.
- **Zonas:** pregúntele al asistente «¿qué zona rinde peor este mes y por qué?». El puntaje combina primera visita exitosa, SLA, productividad, retrabajo y visitas fallidas, con recomendaciones concretas (confirmar citas, escalar puntos de red sin puertos, ajustar duraciones).
- **Configuración de IA:** decida entre *Ninguno*, *Claude* (externo, por API) u *Ollama* (local). Por defecto no se envían datos personales a un modelo externo.
- Las ubicaciones GPS se borran después de 90 días (configurable).

## Preguntas frecuentes

**¿La inteligencia cambia órdenes sola?** No. Propone, explica y avisa; las asignaciones las aprueba una persona.

**¿Qué pasa si se cae internet o el modelo de lenguaje?** Todo sigue funcionando con reglas. El modelo solo mejora textos, resúmenes y el asistente.

**¿Por qué el optimizador asigna órdenes que el motor por reglas dejaba fuera?** Porque reordena las paradas e intercambia órdenes entre cuadrillas en lugar de asignarlas una por una. También al revés: puede dejar fuera una orden que el motor por reglas asignaba, si con el terreno real la cuadrilla no llegaría a tiempo.

**¿Funciona en Costa Rica o Panamá?** Sí, cargando sus municipios o cantones y zonas; vea [`integraciones.md`](integraciones.md#7-despliegues-en-centroamérica).
