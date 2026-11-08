#!/usr/bin/env bash
# Cada vez que el Codespace se reanuda: vuelve a levantar los servicios de QSG PMO y, si es otro día,
# trae la jornada de la demostración a hoy (en segundo plano, sin demorar la apertura).
cd "$(dirname "$0")/../instalacion/pc" || exit 0
[ -f .env ] || exit 0
PUERTO=8080 docker compose up -d >/dev/null 2>&1 || true
nohup bash -c 'for i in $(seq 1 120); do curl -sf http://localhost:8080/api/method/ping >/dev/null && break; sleep 5; done
  docker compose exec -T backend bench --site frontend execute qsg_pmo.inteligencia.demo_vivo.al_reanudar' \
  >/dev/null 2>&1 &
