#!/usr/bin/env bash
# Instala y arranca QSG PMO en esta computadora (Mac o Linux). Requiere Docker.
set -euo pipefail
cd "$(dirname "$0")"
PUERTO="${PUERTO:-8080}"

if ! command -v docker >/dev/null 2>&1; then
  echo "No encuentro Docker. Instale Docker Desktop: https://www.docker.com/products/docker-desktop/"
  exit 1
fi
if ! docker info >/dev/null 2>&1; then
  echo "Docker está instalado pero no está corriendo. Abra Docker Desktop y vuelva a ejecutar este archivo."
  exit 1
fi

# Contraseñas propias de esta instalación (nunca las de fábrica). Se guardan en .env,
# que no se sube al repositorio. Si ya existe, se conservan.
if [ ! -f .env ]; then
  gen() { LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom 2>/dev/null | head -c 20 || true; }
  if docker volume inspect qsg-pmo_db-data >/dev/null 2>&1; then
    echo "Hay una base de datos de una instalación anterior sin .env; se conserva su contraseña."
    DB_PW=admin
  else
    DB_PW="$(gen)"
  fi
  ADM_PW="${ADMIN_PASSWORD:-Qsg-$(gen)}"
  printf 'DB_ROOT_PASSWORD=%s\nADMIN_PASSWORD=%s\n' "$DB_PW" "$ADM_PW" > .env
  chmod 600 .env
  echo "==> Contraseñas nuevas generadas en instalacion/pc/.env"
fi
ADMIN_PW="$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-)"

echo "==> Construyendo la imagen de QSG PMO (la primera vez tarda 5-15 minutos)..."
docker compose build
echo "==> Arrancando los servicios..."
PUERTO="$PUERTO" docker compose up -d

echo "==> Creando el sitio y cargando la demostración (la primera vez tarda 3-6 minutos)..."
until [ "$(docker inspect -f '{{.State.Status}}' qsg-pmo-create-site-1 2>/dev/null)" = "exited" ]; do
  printf "."; sleep 5
done
echo
if [ "$(docker inspect -f '{{.State.ExitCode}}' qsg-pmo-create-site-1)" != "0" ]; then
  echo "La creación del sitio falló. Revise: docker compose logs create-site"
  exit 1
fi

# Reinicia el servidor para que lea la configuración final del sitio (clave de cifrado incluida)
docker compose restart backend queue-short queue-long scheduler websocket >/dev/null
docker compose restart frontend >/dev/null

IP=$( (ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}') | head -1 )
cat <<MSG

QSG PMO está listo.

  En esta computadora:  http://localhost:$PUERTO
      Usuario: Administrator   Contraseña: $ADMIN_PW
      (guardada en instalacion/pc/.env; cámbiela al entrar si lo desea)
      La primera vez complete el asistente: idioma Español, país Puerto Rico, moneda USD.

  En el celular (misma Wi-Fi):  http://${IP:-<IP-de-esta-PC>}:$PUERTO/campo
      Técnico de prueba: tecnico@qsg.pr   Contraseña: Campo2026!

  Para detener:  ./detener.sh      Para actualizar: ./actualizar.sh
MSG
(command -v open >/dev/null && open "http://localhost:$PUERTO") || (command -v xdg-open >/dev/null && xdg-open "http://localhost:$PUERTO") || true
