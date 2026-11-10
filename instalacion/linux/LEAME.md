# QSG PMO con su PC Linux como servidor

Su PC corre el servidor completo: ERPNext v16, QSG PMO, la API (`qsg_pmo.api`), el tablero `/despacho` y la app de campo `/campo`. El APK de Android, [QSG-Campo.apk](https://github.com/ingcpmo/PMO/releases/download/qsg-campo-android/QSG-Campo.apk), se conecta a esa PC.

## Instalar (una vez)

En la terminal de la PC:

```bash
mkdir -p "$HOME/PMO QSG" && cd "$HOME/PMO QSG"
curl -fsSLO https://raw.githubusercontent.com/ingcpmo/PMO/claude/optimistic-noether-2uct53/instalacion/linux/qsg-servidor.sh
bash qsg-servidor.sh instalar su-correo@ejemplo.com
```

El script:

1. Revisa Linux, memoria (4 GB o más) y disco (unos 12 GB). Instala `git`, `curl` y Docker si faltan; para eso pide su contraseña de `sudo`.
2. Descarga QSG PMO en `~/PMO QSG`.
3. Construye y arranca el servidor en el puerto 8080, con la demostración y la jornada simulada.
4. Crea su cuenta con su correo y le muestra la contraseña.
5. Si la PC tiene firewall (`ufw` o `firewalld`), abre el puerto 8080 para la red local.
6. Abre una dirección **https** pública con Cloudflare Tunnel, para el celular.
7. Muestra las direcciones y los usuarios.

Opciones: `--sin-demo` (servidor limpio, sin datos de prueba) y `--sin-tunel` (solo red local).

## Uso diario

| Orden | Para qué |
|---|---|
| `bash qsg-servidor.sh iniciar` | Después de reiniciar la PC: servidor y dirección https nueva |
| `bash qsg-servidor.sh tunel` | Abrir otra vez la dirección https |
| `bash qsg-servidor.sh estado` | Qué está corriendo y la dirección https actual |
| `bash qsg-servidor.sh cuenta su-correo@ejemplo.com` | Crear su cuenta o darle una contraseña nueva |
| `bash qsg-servidor.sh actualizar` | Traer la última versión de GitHub |
| `bash qsg-servidor.sh detener` | Apagar el servidor y el túnel |

Desde la segunda vez, ejecútelo como `bash ~/"PMO QSG"/instalacion/linux/qsg-servidor.sh …`. El script descargado al principio también sirve.

## El celular

1. Instale [QSG-Campo.apk](https://github.com/ingcpmo/PMO/releases/download/qsg-campo-android/QSG-Campo.apk).
2. Al abrirlo, escriba la **dirección https** que mostró el script (termina en `.trycloudflare.com`).
3. Entre con su correo y su contraseña.

La dirección https cambia cada vez que se abre el túnel. Cuando cambie, abra la app y toque **Cambiar servidor** mientras dice «Conectando».

En la misma Wi-Fi también puede usar `http://IP-de-la-PC:8080`, pero sin https el celular no entrega el GPS a la app.

## ¿Hace falta Vercel? No

El APK es una ventana a `/campo`. Llama a la API con la sesión de Frappe y necesita llegar **directo** al servidor. El problema real es que la PC está detrás del router de la casa y no tiene una dirección pública con https. Vercel no resuelve eso:

- **No llega a la PC.** Vercel publica páginas y funciones en sus servidores. Para reenviar tráfico a su PC, la PC tendría que estar expuesta en internet igual, que es justo lo que falta.
- **Rompe funciones.** Vercel no mantiene WebSockets (el tiempo real del escritorio). Además, agrega un salto y límites de tamaño y tiempo a las fotos de evidencia y a la sincronización de la app.
- **Duplica el diseño.** Habría que mantener una segunda interfaz sincronizada con la API, sin ganar nada.

Lo que sí hace falta, y el script ya lo trae, es un **túnel https**: Cloudflare Tunnel. Con él la PC sale hacia Cloudflare, no hay que abrir puertos del router y no hace falta cuenta. Da https (GPS y cámara en el APK) y mantiene los WebSockets.

```
Celular (QSG Campo) ──https──> Cloudflare (dirección .trycloudflare.com)
                                   │  túnel saliente, sin abrir puertos
                                   ▼
                       Su PC: cloudflared ──> localhost:8080 ──> ERPNext + QSG PMO (Docker)
```

**Para producción** conviene una dirección fija, por ejemplo `https://pmo.suempresa.com`. Se logra con un túnel con nombre de Cloudflare (cuenta y dominio propios) o con un servidor en la nube. Con esa dirección, construya el APK con servidor fijo desde *Actions → App Android (APK)*.

## Seguridad

- Las contraseñas del administrador y de la base de datos son únicas y quedan en `instalacion/pc/.env` (no se sube a GitHub).
- Con la dirección https abierta, cualquiera que la conozca puede intentar entrar. Los usuarios de demostración tienen contraseñas publicadas en este repositorio: para uso real, instale con `--sin-demo` o desactive esos usuarios.
- El túnel se cierra con `detener` o al apagar la PC.
