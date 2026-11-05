# QSG Campo para iPhone

La app de iPhone es la misma app de campo de QSG PMO (`/campo`) a pantalla completa, con **GPS**, **cámara** y envío de ubicación al tablero de despacho. Usa el mismo envoltorio (Capacitor 8) que la app de Android.

Hay tres caminos. Para empezar a probar, el **A** no requiere nada.

## A. Desde Safari (hoy, sin instalar nada)

1. En el iPhone abra Safari en `https://<su-servidor>/campo` y entre.
2. Botón **Compartir** → **Agregar a inicio**.

Se abre a pantalla completa con el icono de QSG, cámara, firma y GPS. El GPS del iPhone exige **https** (servidor definitivo, o un túnel como `cloudflared` para pruebas).

## B. Construir la app en la nube (sin Mac)

1. En GitHub abra el repositorio → **Actions** → **App iPhone (iOS)** → **Run workflow**.
2. Escriba la dirección del servidor (`https://pmo.qsg.pr`) → **Run workflow**.
3. En 10 a 20 minutos descargue **QSG-Campo-ios** en *Artifacts*. Trae:
   - `QSG-Campo-simulador.zip`: la app para probar en el simulador de Xcode.
   - `QSG-Campo-sin-firma.ipa`: la app para iPhone, **sin firmar**.

Apple no deja instalar una app sin firma. Para llevar el `.ipa` a los teléfonos de los técnicos:

| Opción | Qué hace falta | Para quién |
|---|---|---|
| **TestFlight** (recomendada) | Cuenta Apple Developer de la empresa (99 USD/año). Se sube el `.ipa` firmado y se invita a cada técnico por correo. | Todas las cuadrillas, actualizaciones automáticas |
| **Ad Hoc** | La misma cuenta y el identificador (UDID) de cada iPhone, hasta 100 por año. | Pilotos cortos |
| **Apple Business Manager / MDM** | Si Liberty o QSG ya administran los iPhones. | Teléfonos de la empresa |

> La acción **Run workflow** aparece en *Actions* cuando estos archivos están en la rama principal. Antes de eso, la construcción también corre sola cada vez que cambia la carpeta `instalacion/ios/`.

## C. Construir en una Mac

Requisitos: **Xcode** (App Store) y **Node.js 22** o superior.

```bash
./construir-ios.sh https://pmo.qsg.pr
```

Deja la app del simulador en `salida/`. Para iPhones: abra `ios/App` en Xcode → *Signing & Capabilities* → elija el equipo de la cuenta Apple Developer → **Product → Archive → Distribute App** (TestFlight o Ad Hoc).

## Permisos que pide la app

- **Ubicación (mientras se usa)**: registrar la llegada a la orden y mostrar la ruta del día al despacho.
- **Cámara y fotos**: evidencia de la instalación.

Los textos que ve el técnico están en `preparar.mjs` (`--ios`).

## Qué hace cada archivo

| Archivo | Para qué |
|---|---|
| `construir-ios.sh` | Construye la app en una Mac con la dirección del servidor que le indique |
| `preparar.mjs` | Escribe la configuración (servidor) y agrega los permisos al proyecto iOS |
| `package.json` | Versiones de Capacitor |
| `www/index.html` | Pantalla que se muestra si no hay conexión con el servidor |
| `../../.github/workflows/ios-app.yml` | La construcción en la nube (opción B) |

Las mejoras de la app de campo **no** requieren publicar una versión nueva: la app carga las pantallas desde el servidor.
