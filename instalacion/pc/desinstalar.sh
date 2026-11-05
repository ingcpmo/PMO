#!/usr/bin/env bash
# Elimina QSG PMO de esta computadora, INCLUIDA la base de datos y las fotos.
cd "$(dirname "$0")"
read -r -p "Esto borra todos los datos de QSG PMO en esta PC. Escriba BORRAR para continuar: " r
[ "$r" = "BORRAR" ] || { echo "Cancelado."; exit 0; }
docker compose down -v && echo "QSG PMO eliminado."
