#!/usr/bin/env bash
# Detiene QSG PMO sin borrar datos. Para volver a arrancar: ./instalar.sh
cd "$(dirname "$0")" && docker compose stop && echo "QSG PMO detenido. Sus datos se conservan."
