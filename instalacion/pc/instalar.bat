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

set IP=
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do if not defined IP set IP=%%a
set IP=%IP: =%

echo.
echo QSG PMO esta listo.
echo.
echo   En esta computadora:  http://localhost:%PUERTO%
echo       Usuario: Administrator   Contrasena: admin
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
