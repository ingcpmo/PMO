@echo off
REM Instala y arranca QSG PMO en esta computadora con Windows. Requiere Docker Desktop.
setlocal
cd /d "%~dp0"
chcp 65001 >nul
if "%PUERTO%"=="" set PUERTO=8080

where docker >nul 2>nul
if errorlevel 1 (
  echo No encuentro Docker. Instale Docker Desktop: https://www.docker.com/products/docker-desktop/
  pause
  exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
  echo Docker esta instalado pero no esta corriendo. Abra Docker Desktop, espere a que diga "Running" y vuelva a ejecutar este archivo.
  pause
  exit /b 1
)

REM Contrasenas propias de esta instalacion (nunca las de fabrica), guardadas en .env
if exist .env goto envlisto
powershell -NoProfile -ExecutionPolicy Bypass -Command "$c='ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'; $r=New-Object Security.Cryptography.RNGCryptoServiceProvider; function g { $b=New-Object byte[] 20; $r.GetBytes($b); -join ($b | ForEach-Object { $c[$_ %% $c.Length] }) }; $db=g; if (docker volume ls -q -f name=qsg-pmo_db-data) { $db='admin' }; Set-Content -Encoding ascii .env ('DB_ROOT_PASSWORD=' + $db), ('ADMIN_PASSWORD=' + $(if ($env:ADMIN_PASSWORD) { $env:ADMIN_PASSWORD } else { 'Qsg-' + (g) }))"
if errorlevel 1 goto error
echo ==^> Contrasenas nuevas generadas en instalacion\pc\.env
:envlisto
for /f "tokens=1,* delims==" %%a in (.env) do if "%%a"=="ADMIN_PASSWORD" set ADMIN_PW=%%b

echo ==^> Construyendo la imagen de QSG PMO (la primera vez tarda 5-15 minutos)...
docker compose build
if errorlevel 1 goto error
echo ==^> Arrancando los servicios...
docker compose up -d
if errorlevel 1 goto error

echo ==^> Creando el sitio y cargando la demostracion (la primera vez tarda 3-6 minutos)...
:esperar
for /f %%s in ('docker inspect -f "{{.State.Status}}" qsg-pmo-create-site-1') do set ESTADO=%%s
if not "%ESTADO%"=="exited" (
  timeout /t 5 /nobreak >nul
  goto esperar
)
for /f %%c in ('docker inspect -f "{{.State.ExitCode}}" qsg-pmo-create-site-1') do set CODIGO=%%c
if not "%CODIGO%"=="0" (
  echo La creacion del sitio fallo. Revise con: docker compose logs create-site
  goto error
)

REM Reinicia el servidor para que lea la configuracion final del sitio (clave de cifrado incluida)
docker compose restart backend queue-short queue-long scheduler websocket >nul
docker compose restart frontend >nul

set IP=
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do if not defined IP set IP=%%a
set IP=%IP: =%

echo.
echo QSG PMO esta listo.
echo.
echo   En esta computadora:  http://localhost:%PUERTO%
echo       Usuario: Administrator   Contrasena: %ADMIN_PW%
echo       (guardada en instalacion\pc\.env)
echo       La primera vez complete el asistente: idioma Espanol, pais Puerto Rico, moneda USD.
echo.
echo   En el celular (misma Wi-Fi):  http://%IP%:%PUERTO%/campo
echo       Tecnico de prueba: tecnico@qsg.pr   Contrasena: Campo2026!
echo.
echo   Para detener: detener.bat     Para actualizar: actualizar.bat
echo.
start "" http://localhost:%PUERTO%
pause
exit /b 0

:error
echo.
echo Algo fallo. Copie lo que aparece arriba y envielo para revisarlo.
pause
exit /b 1
