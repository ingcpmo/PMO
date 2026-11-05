#!/usr/bin/env bash
# Trae la última versión del repositorio, reconstruye la imagen y migra la base de datos.
set -euo pipefail
cd "$(dirname "$0")"
git -C ../.. pull --ff-only || echo "Aviso: no se pudo actualizar con git; se usa el código que ya tiene."
docker compose build
docker compose up -d
docker compose exec backend bench --site frontend migrate
echo "QSG PMO actualizado."
