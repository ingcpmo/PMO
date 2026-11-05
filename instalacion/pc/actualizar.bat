@echo off
REM Trae la ultima version del repositorio, reconstruye la imagen y migra la base de datos.
cd /d "%~dp0"
git -C ..\.. pull --ff-only
docker compose build
docker compose up -d
docker compose exec backend bench --site frontend migrate
echo QSG PMO actualizado.
pause
