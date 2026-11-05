#!/usr/bin/env bash
# Cada vez que el Codespace se reanuda: vuelve a levantar los servicios de QSG PMO.
cd "$(dirname "$0")/../instalacion/pc" || exit 0
[ -f .env ] || exit 0
PUERTO=8080 docker compose up -d >/dev/null 2>&1 || true
