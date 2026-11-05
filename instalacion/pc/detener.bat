@echo off
REM Detiene QSG PMO sin borrar datos. Para volver a arrancar: instalar.bat
cd /d "%~dp0"
docker compose stop
echo QSG PMO detenido. Sus datos se conservan.
pause
