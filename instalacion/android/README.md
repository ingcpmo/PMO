# QSG Campo para Android

App Android para los técnicos. Abre la app de campo de QSG PMO (`/campo`) a pantalla completa, con el **GPS** y la **cámara** del teléfono. Requiere un servidor de QSG PMO funcionando (por ejemplo, la PC de la carpeta `pc/`).

Hay tres formas de instalarla. Para la primera prueba recomendamos la **A**.

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
| `preparar.mjs` | Escribe la configuración (servidor) y ajusta permisos e icono del proyecto Android |
| `package.json` | Versiones de Capacitor (el envoltorio nativo) |
| `www/index.html` | Pantalla que se muestra si no hay conexión con el servidor |
| `../../.github/workflows/android-apk.yml` | La construcción en la nube (opción A) |

Versión de prueba: el APK va firmado con la clave de depuración. Para publicarlo en Google Play hará falta firmarlo con la clave de la empresa.
