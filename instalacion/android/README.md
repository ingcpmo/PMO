# QSG Campo para Android

App Android para los técnicos. Abre la app de campo de QSG PMO (`/campo`) a pantalla completa, con el **GPS** y la **cámara** del teléfono. Requiere un servidor de QSG PMO funcionando (por ejemplo, la PC de la carpeta `pc/`).

Hay cuatro formas de instalarla. Para la primera prueba recomendamos **descargar el APK listo**.

## Descargar el APK listo (sin construir nada)

1. En el celular abra **[QSG-Campo.apk](https://github.com/ingcpmo/PMO/releases/download/qsg-campo-android/QSG-Campo.apk)** (página: [QSG Campo para Android](https://github.com/ingcpmo/PMO/releases/tag/qsg-campo-android)). No hace falta cuenta de GitHub.
2. Ábralo y permita **Instalar apps desconocidas** cuando Android lo pida.
3. Abra **QSG Campo** y escriba la dirección de su servidor; la app la recuerda y al abrirla de nuevo entra sola (con la opción **Cambiar servidor** durante un segundo y medio):
   - **GitHub Codespaces:** la dirección del puerto 8080, que termina en `.app.github.dev`. En la pestaña *Ports* ponga el 8080 como **Public**, o inicie sesión en GitHub cuando la app lo pida.
   - **PC en la red local:** por ejemplo `http://192.168.1.50:8080` (sin https el GPS del navegador no funciona; para GPS en la red local use la opción A o B, que guardan la dirección dentro del APK).
4. Entre con su usuario (demostración: `tecnico@qsg.pr` / `Campo2026!`, o su propia cuenta) y acepte los permisos de **ubicación** y **cámara**.

Este APK lo publica el flujo **App Android (descarga directa)** cada vez que cambia esta carpeta. Si Android no deja instalar una versión nueva encima de la anterior, desinstálela primero.

## A. Construir el APK en la nube (no instala nada en su PC)

1. Averigüe la IP de la PC donde instaló QSG PMO: en Windows abra *Símbolo del sistema* y escriba `ipconfig` (línea *Dirección IPv4*, por ejemplo `192.168.1.50`).
2. En GitHub abra el repositorio → pestaña **Actions** → **App Android (APK)** → **Run workflow**.
3. En *Dirección de QSG PMO* escriba `http://192.168.1.50:8080` (con su IP) → **Run workflow**.
4. Espere 5–8 minutos a que salga en verde, ábralo y descargue **QSG-Campo-apk** en *Artifacts*.
5. Descomprima el ZIP y pase `QSG-Campo.apk` al celular (cable, Google Drive o WhatsApp).
6. En el celular, abra el archivo y acepte **Instalar apps de origen desconocido** cuando lo pida.
7. Abra **QSG Campo**, entre con `tecnico@qsg.pr` / `Campo2026!` y acepte los permisos de **ubicación** y **cámara**.

> La acción en la nube solo aparece en *Actions* cuando estos archivos están en la rama principal (después de aprobar el PR). Antes de eso, use la opción B o C.

## B. Construir el APK en su PC

Requisitos: **Android Studio** (ábralo una vez para que descargue el SDK) y **Node.js 22** o superior.

| Windows | Mac / Linux |
|---|---|
| `construir-apk.bat http://192.168.1.50:8080` | `./construir-apk.sh http://192.168.1.50:8080` |

El APK queda en `salida/QSG-Campo.apk`. Instálelo como en los pasos 5 a 7 de la opción A.

## C. Sin APK: instalar desde Chrome

1. En el celular abra Chrome en `http://192.168.1.50:8080/campo` y entre.
2. Menú ⋮ → **Agregar a la pantalla principal**.

Funciona igual que la app, pero sin GPS mientras el servidor no tenga **https**.

## Cambiar de servidor

La dirección del servidor queda dentro del APK. Si cambia la IP de la PC, o cuando pasen al servidor definitivo con dominio y https (por ejemplo `https://pmo.qsg.pr`), construya el APK otra vez con la nueva dirección. Las actualizaciones de la app de campo **no** requieren un APK nuevo: la app carga las pantallas desde el servidor, así que basta con actualizar el servidor.

## Qué hace cada archivo

| Archivo | Para qué |
|---|---|
| `construir-apk.bat` / `.sh` | Construye el APK con la dirección del servidor que le indique |
| `preparar.mjs` | Escribe la configuración (servidor fijo, o `--preguntar` para el APK de descarga directa) y ajusta permisos e icono del proyecto Android |
| `package.json` | Versiones de Capacitor (el envoltorio nativo) |
| `www/index.html` | Pantalla para escribir el servidor (APK de descarga directa) y la que se muestra si no hay conexión |
| `../../.github/workflows/android-apk.yml` | La construcción en la nube (opción A) |
| `../../.github/workflows/android-descarga.yml` | Construye y publica el APK de descarga directa |

Versión de prueba: el APK va firmado con la clave de depuración. Para publicarlo en Google Play hará falta firmarlo con la clave de la empresa.
