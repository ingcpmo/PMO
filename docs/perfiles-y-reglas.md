# Perfiles, asignación y reglas (v0.5)

Todo se decide con reglas en el servidor. No se usa modelo de lenguaje: la recomendación sale de la ubicación GPS, la calificación del contratista y el cupo, y **siempre asigna una persona**.

## Una sola app, dos vistas

El mismo APK sirve para todos. Al iniciar sesión, el servidor mira el perfil del usuario:

| Perfil | Rol en el sistema | Entra a | Puede |
|---|---|---|---|
| **Administrador** (perfil maestro) | QSG Gerente | Tablero de despacho | Ver todo y la ubicación de todos, asignar, dar de alta usuarios (pestaña «Equipo») y cambiar las reglas (pestaña «Reglas») |
| Despachador | QSG Despachador | Tablero de despacho | Ver todo y asignar; no configura |
| Supervisor | QSG Supervisor Contratista | Tablero, solo su empresa | Ver sus cuadrillas y pendientes |
| **Contratista** | QSG Tecnico | Su ruta | Recibir el aviso de una orden nueva, confirmarla con «Recibida» y hacer todo el trabajo: en ruta, en sitio, fotos, mediciones, materiales, firma y cierre |

El contratista **no ve** a los otros contratistas, ni sus ubicaciones, ni el tablero, ni las calificaciones. Solo ve las órdenes de su cuadrilla. Esto lo controla el servidor, no el APK, y está cubierto por pruebas automáticas.

## Dar de alta a un contratista

Tablero → pestaña **Equipo** → «Agregar un usuario», perfil **Contratista**:

- correo, nombre y teléfono;
- empresa contratista (si no existe, se crea);
- municipio de salida (su punto de partida en el mapa), habilidades, órdenes por día y turno.

Al guardar se crean el usuario, la empresa y su cuadrilla, y aparece la **contraseña** una sola vez. Desde ese momento el contratista recibe recomendaciones. «Desactivar» lo saca de las recomendaciones y cierra su sesión.

## Cómo entra y se asigna una petición

1. **Entra la petición:** desde la API del cliente, pegando el correo en «Asistente», o creada a mano.
2. **Aviso al administrador:** suena el tablero y la pestaña «Sin asignar» muestra el número de pendientes.
3. **Recomendación por reglas:** cada petición trae sus 3 mejores cuadrillas con kilómetros, minutos de viaje, hora de llegada, cupos que le quedan y categoría del contratista. Tocando el nombre se ve su perfil y su calificación.
4. **El administrador asigna** con un toque. El motivo queda en el historial.
5. **Aviso al contratista:** su app suena y vibra con «Tiene una orden nueva» hasta que toca **Recibida**.
6. **Seguimiento:** si pasa el tiempo configurado sin «Recibida», el tablero lo marca en «Alertas».
7. **Trabajo y cierre** desde la app del contratista. Los cierres alimentan su calificación.

## Reglas de recomendación

Se descartan las cuadrillas que no tienen la habilidad, no tienen cupo hoy, están fuera de su turno, no llegan dentro de la ventana de la cita, están ausentes o trabajan en una zona con incidencia (apagón, inundación, vía cerrada).

Las que quedan se ordenan por un costo en minutos; gana el menor:

```
costo = minutos de viaje desde su último GPS (o su punto de salida)
      + atraso sobre el inicio de la ventana
      + órdenes que ya tiene hoy × penalización por carga
      − bonificación por ser de la misma zona
      − afinidad con la zona (cómo le ha ido ahí)
      − bonificación si el contratista es categoría A
      + penalización si es categoría C
```

Valores de fábrica, editables en la pestaña «Reglas» por el administrador:

| Regla | Valor |
|---|---|
| Velocidad media | 35 km/h |
| Factor de carretera | 1,4 |
| Penalización por carga | 10 min por orden |
| Bonificación por misma zona | 15 min |
| Afinidad con la zona | hasta 20 min |
| Bonificación categoría A | 10 min |
| Penalización categoría C | 15 min |

## Calificación del contratista

Se recalcula **cada hora**, con los cierres de los últimos 30 días:

| Factor | Peso |
|---|---|
| Llega dentro de la ventana | 20 % |
| Primera visita exitosa (no cuentan fallas atribuibles al cliente) | 20 % |
| Cumple el SLA | 20 % |
| Evidencia completa | 15 % |
| Encuesta del cliente | 15 % (solo si hay encuestas) |
| Sin retrabajo en garantía | 10 % |

Categoría **A** desde 90 puntos, **B** desde 75, **C** por debajo. Un contratista sin cierres aparece como «sin calificar» y no recibe ni bonificación ni penalización.

## Tiempos

| Tiempo | Valor |
|---|---|
| Confirmar una orden asignada | 10 min |
| Avisar SLA en riesgo | 120 min antes |
| Sin señal de GPS | según configuración |
| Detenida fuera de ruta | según configuración |
| Perímetro de llegada | 300 m |

## Dirección del servidor

Con su PC como servidor (`instalacion/linux/qsg-servidor.sh`):

- **Con Tailscale conectado:** dirección **fija** `https://<su-equipo>.<su-red>.ts.net` (Tailscale Funnel). No cambia al reiniciar la PC, así que el APK no se vuelve a configurar.
- **Sin Tailscale:** dirección temporal de Cloudflare (`…trycloudflare.com`), que cambia en cada reinicio.

Antes de invitar contratistas reales: `bash qsg-servidor.sh asegurar` apaga los usuarios y cuadrillas de demostración, cuyas contraseñas son públicas.
