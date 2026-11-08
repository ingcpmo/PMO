#!/usr/bin/env bash
# Primer arranque en GitHub Codespaces: instala QSG PMO (ERPNext v16 + la app) con Docker, carga la
# demostración, crea usuarios por rol y deja lista la jornada simulada. Tarda 10 a 15 minutos.
# El puerto 8080 se abre al final, cuando la app ya responde: así el navegador no muestra errores.
set -euo pipefail
AQUI="$(cd "$(dirname "$0")" && pwd)"
cd "$AQUI/../instalacion/pc"

aleatorio() { openssl rand -hex "$1" 2>/dev/null || head -c "$1" /dev/urandom | od -An -tx1 | tr -d ' \n'; }
if [ ! -f .env ]; then
  printf 'DB_ROOT_PASSWORD=%s\nADMIN_PASSWORD=%s\n' "$(aleatorio 16)" "Qsg-$(aleatorio 6)" > .env
  chmod 600 .env
fi

# Imágenes base. Si Docker Hub limita las descargas, se usa su espejo público de Google.
traer() {
  docker image inspect "$1" >/dev/null 2>&1 && return 0
  docker pull -q "$1" >/dev/null 2>&1 && return 0
  local espejo="mirror.gcr.io/$1"
  [[ "$1" == */* ]] || espejo="mirror.gcr.io/library/$1"
  docker pull -q "$espejo" >/dev/null && docker tag "$espejo" "$1"
}
echo "==> Descargando las imágenes base..."
ERPNEXT_VERSION="$(sed -n 's/^ *ERPNEXT_VERSION: *//p' docker-compose.yml | head -1)"
for imagen in "frappe/erpnext:${ERPNEXT_VERSION}" $(docker compose config --images | grep -v '^qsg-pmo' | sort -u); do
  traer "$imagen" || echo "Aviso: no se pudo descargar ${imagen}; se intentará al construir."
done

echo "==> Construyendo la imagen de QSG PMO..."
docker compose build
echo "==> Arrancando los servicios..."
mapfile -t SERVICIOS < <(docker compose config --services | grep -vx frontend)
PUERTO=8080 docker compose up -d "${SERVICIOS[@]}"

echo "==> Creando el sitio y cargando la demostración (la parte más larga)..."
until [ "$(docker inspect -f '{{.State.Status}}' qsg-pmo-create-site-1 2>/dev/null)" = "exited" ]; do sleep 5; done
if [ "$(docker inspect -f '{{.State.ExitCode}}' qsg-pmo-create-site-1)" != "0" ]; then
  docker compose logs create-site | tail -40
  echo "La creación del sitio falló."
  exit 1
fi
docker compose restart backend queue-short queue-long scheduler websocket >/dev/null

BENCH=(docker compose exec -T backend bench --site frontend)
"${BENCH[@]}" set-config qsg_demo_vivo 1 >/dev/null
"${BENCH[@]}" execute qsg_pmo.inteligencia.demo_vivo.preparar_sitio >/dev/null
"${BENCH[@]}" execute qsg_pmo.inteligencia.demo_vivo.reiniciar >/dev/null

echo "==> Abriendo el puerto 8080..."
PUERTO=8080 docker compose up -d frontend
until curl -sf http://localhost:8080/api/method/ping >/dev/null; do sleep 3; done
ADMIN_PW="$(grep '^ADMIN_PASSWORD=' .env | cut -d= -f2-)"
URL="http://localhost:8080"
if [ -n "${CODESPACE_NAME:-}" ]; then
  URL="https://${CODESPACE_NAME}-8080.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
fi
cat <<MSG

QSG PMO está listo: ${URL}

  Tablero de despacho:  ${URL}/despacho     despacho@qsg.pr / Demo-QSG-2026!
  App del técnico:      ${URL}/campo        tecnico@qsg.pr / Campo2026!
  Gerencia:             gerente@qsg.pr / Demo-QSG-2026!
  Administrador:        Administrator / ${ADMIN_PW}   (guardada en instalacion/pc/.env)

En el tablero, «Simular jornada» mueve las cuadrillas, cierra órdenes y a mitad del día entra
una avería urgente sin asignar: ábrala en «Sin asignar» y use «Mejor cuadrilla».

App Android para el celular: https://github.com/ingcpmo/PMO/releases/tag/qsg-campo-android
(al abrirla, escriba la dirección de arriba; ponga antes el puerto 8080 como Public).
MSG

# Cuenta propia con su correo, si al crear el Codespace lo indicó en QSG_CORREO
if [ -n "${QSG_CORREO:-}" ]; then
  bash "$AQUI/crear-cuenta.sh" "$QSG_CORREO" \
    || echo "Aviso: no se pudo crear su cuenta; ejecute: bash .devcontainer/crear-cuenta.sh su-correo"
else
  echo
  echo "Para su propia cuenta con su correo: bash .devcontainer/crear-cuenta.sh su-correo@ejemplo.com"
fi
