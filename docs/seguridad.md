# Seguridad de QSG PMO

El módulo de seguridad (`qsg_pmo/seguridad/`) se activa solo al instalar o migrar. Una petición
cruza seis capas antes de llegar a la base de datos, y todo rechazo queda registrado.

| Capa | Qué hace | Código |
|---|---|---|
| 1. Acceso | 5 intentos fallidos bloquean usuario e IP 10 minutos; contraseñas con puntaje 3 o más; sesión de 12 h; sin auto-registro; token CSRF en cada POST. | `seguridad/endurecimiento.py` (Frappe aplica el CSRF) |
| 2. Límite de peticiones | 120 por minuto por usuario y método (la integración, 600). Después responde 429. | `seguridad/limites.py` |
| 3. Permisos | Matriz por rol en cada tabla y permisos por fila: técnico solo su cuadrilla, supervisor solo su contratista. | definición de cada DocType, `permissions.py` |
| 4. Validación | Texto sin HTML, GPS posible, firma PNG, mediciones numéricas, campos permitidos de Liberty, IPs de Liberty. Fotos y adjuntos: se revisa el contenido real (JPG, PNG, WEBP, HEIC o PDF), hasta 10 MB. | `seguridad/validacion.py`, `seguridad/archivos.py` |
| 5. Integridad | Orden cerrada bloqueada (salvo reprogramar una visita fallida); historial que solo crece; la foto de evidencia tiene que ser de esa orden. | `qsg_orden.py`, `api.py` |
| 6. Respuesta | CSP estricta en `/campo`, anti-clickjacking, nosniff, Referrer-Policy, Permissions-Policy, HSTS con HTTPS, sin caché en la API, errores sin traza. | `seguridad/cabeceras.py` |

## Matriz de permisos

L = leer, E = escribir, C = crear, B = borrar.

| Tabla | Administrador y Gerente | Despachador | Supervisor contratista | Técnico | Bodega |
|---|---|---|---|---|---|
| Orden | LECB | LEC | LE (su contratista) | L (su cuadrilla) | L |
| Plan de Despacho | LECB | LEC | L | — | L |
| Cuadrilla | LECB | LEC | LE (su contratista) | — | L |
| Disponibilidad | LECB | LECB | LEC (su contratista) | — | — |
| Encuesta | LECB | LEC | L (su contratista) | — | — |
| Evaluación Contratista | LECB | L | L (su contratista) | — | — |
| Contratista | LECB | L | L (el suyo) | — | L |
| Catálogos (código de cierre, habilidad, plantilla, tipo de trabajo, zona) | LECB | L | L | L | L |
| Configuración | LE (Administrador y Gerente) | — | — | — | — |
| Evento Seguridad | L (Gerente); LB (Administrador) | — | — | — | — |

El técnico cambia órdenes solo por la API de campo (`qsg_pmo.api`), que valida cada paso. Cada
supervisor necesita un *User Permission* de QSG Contratista; sin él no ve nada.

## Registro de seguridad

*QSG Evento Seguridad* guarda tipo, severidad, usuario, IP, método, orden y detalle de cada
acceso denegado, límite superado, archivo rechazado, dato inválido, IP no permitida, intento de
alterar una orden cerrada y llegada fuera de rango. El evento se guarda aunque la petición termine
en error, y nadie lo puede editar.

## Autodiagnóstico

*Reporte → Estado de Seguridad* (Gerente y Administrador), o:

```bash
bench --site <sitio> execute qsg_pmo.seguridad.verificar.ejecutar
```

18 controles con OK, ALERTA o FALLA y la acción a tomar: modo desarrollador, HTTPS, trazas,
planificador, contraseña del Administrador, usuarios de demostración, bloqueo, política de
contraseñas, sesión, auto-registro, doble factor, permisos del técnico, supervisores ligados,
cabeceras, filtro de archivos, límite de peticiones, IPs de la integración y eventos graves.

## Configuración (*QSG Configuracion → Seguridad*)

| Campo | Por defecto |
|---|---|
| Peticiones por minuto | 120 |
| Tamaño máximo de foto | 10 MB |
| Exigir doble factor a gerencia y despacho | no |
| IPs permitidas para la integración | vacío = cualquiera con token válido |

## Antes de operar con datos reales

1. Publicar con dominio y HTTPS y definir `host_name` con `https://`.
2. Desactivar `tecnico@qsg.pr` y los usuarios de prueba.
3. Activar el doble factor para gerencia y despacho.
4. Cargar las IPs de Liberty.
5. Crear el *User Permission* de cada supervisor.
6. Revisar *Estado de Seguridad* hasta que no queden fallas.

## Pruebas de ataque y simulación

La carpeta `auditoria/` tiene 34 ataques por HTTP y la simulación de una orden de Liberty de
inicio a fin. Úselas solo en sitios de prueba: crean usuarios y órdenes.

```bash
bench --site <sitio> execute qsg_pmo.seguridad.auditoria.preparar | tail -1 > datos.json
python3 auditoria/ataques.py --base http://localhost:8080 --datos datos.json --salida ataques.json
python3 auditoria/simulacion.py --base http://localhost:8080 --datos datos.json --salida simulacion.json
```

Con la instalación de PC: `docker compose exec backend bench --site frontend execute qsg_pmo.seguridad.auditoria.preparar`.
El ataque de fuerza bruta deja la IP bloqueada 10 minutos; `preparar` limpia el bloqueo.
