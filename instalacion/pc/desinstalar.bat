@echo off
REM Elimina QSG PMO de esta computadora, INCLUIDA la base de datos y las fotos.
cd /d "%~dp0"
set /p R=Esto borra todos los datos de QSG PMO en esta PC. Escriba BORRAR para continuar: 
if not "%R%"=="BORRAR" (
  echo Cancelado.
  pause
  exit /b 0
)
docker compose down -v
echo QSG PMO eliminado.
pause
