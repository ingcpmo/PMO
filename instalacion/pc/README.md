# QSG PMO en una PC

Instala el servidor completo de QSG PMO (ERPNext v16 + QSG PMO) en su computadora, con datos de demostración. Funciona en Windows 10/11, macOS y Linux.

## Antes de empezar (una sola vez)

1. Instale **Docker Desktop**: https://www.docker.com/products/docker-desktop/
   - En Windows, acepte cuando le pida activar WSL 2 y reinicie.
2. Ábralo y espere a que diga **Engine running**.
3. Necesita unos **8 GB de RAM** libres y **10 GB de disco**.
4. Descargue este repositorio: botón verde **Code → Download ZIP** en GitHub y descomprímalo, o `git clone https://github.com/ingcpmo/PMO`.

## Instalar

| Windows | Mac / Linux |
|---|---|
| Doble clic en `instalar.bat` | En la Terminal: `./instalar.sh` |

La primera vez tarda entre 10 y 20 minutos (descarga ERPNext, crea la base de datos y carga la demostración). Al terminar abre el navegador y muestra:

- **Oficina**: `http://localhost:8080`, usuario `Administrator`, contraseña `admin`.
  La primera vez aparece el asistente de ERPNext: elija **Español**, país **Puerto Rico**, zona horaria **America/Puerto_Rico**, moneda **USD** y el nombre de la empresa (QSG). Esto crea la compañía y las bodegas que usa QSG PMO.
- **Celular** (misma Wi-Fi): `http://<IP-de-la-PC>:8080/campo`, técnico `tecnico@qsg.pr`, contraseña `Campo2026!`.

Si Windows pregunta por el **Firewall**, permita el acceso en redes privadas; si no, el celular no podrá conectarse.

## Otros archivos

| Archivo | Para qué |
|---|---|
| `detener.bat` / `detener.sh` | Apaga QSG PMO. Los datos se conservan. Vuelva a arrancar con `instalar`. |
| `actualizar.bat` / `actualizar.sh` | Trae la última versión de GitHub, reconstruye y migra la base de datos. |
| `pruebas.bat` / `pruebas.sh` | Corre las 25 pruebas automáticas en un sitio aparte, sin tocar sus datos. |
| `desinstalar.bat` / `desinstalar.sh` | Borra QSG PMO y **todos sus datos** de la PC (pide confirmación). |
| `docker-compose.yml`, `Dockerfile` | Configuración de los servicios. No hace falta editarlos. |

## Opciones

- **Otro puerto**: si el 8080 está ocupado, en Windows `set PUERTO=8090` y luego `instalar.bat`; en Mac/Linux `PUERTO=8090 ./instalar.sh`.
- **Sin demostración**: `CARGAR_DEMO=0` antes de instalar.
- **Otra contraseña de administrador**: `ADMIN_PASSWORD=...` antes de la primera instalación.

## Si algo falla

| Síntoma | Solución |
|---|---|
| «No encuentro Docker» | Instale Docker Desktop y reinicie la PC. |
| «Docker está instalado pero no está corriendo» | Abra Docker Desktop y espere a *Engine running*. |
| El navegador muestra *502 Bad Gateway* | Aún está arrancando; espere un minuto y recargue. |
| El celular no abre la página | Misma Wi-Fi, IP correcta (`ipconfig` en Windows) y firewall permitido. |
| Quiero ver qué pasa | `docker compose logs -f backend` dentro de esta carpeta. |

## GPS en la prueba con PC

Los navegadores solo dan la ubicación en páginas **https**. Con `http://<IP>:8080/campo` en el navegador del celular todo funciona menos el GPS. Para probar el GPS use la **app Android** de la carpeta `android/` (usa el GPS nativo y funciona con http en la red local).
