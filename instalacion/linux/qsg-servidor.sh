#!/usr/bin/env bash
# QSG PMO en su PC con Linux: la PC queda como servidor de la API, del tablero y de la app Android.
#
# Primera vez (en la terminal):
#   mkdir -p "$HOME/PMO QSG" && cd "$HOME/PMO QSG"
#   curl -fsSLO https://raw.githubusercontent.com/ingcpmo/PMO/claude/optimistic-noether-2uct53/instalacion/linux/qsg-servidor.sh
#   bash qsg-servidor.sh instalar su-correo@ejemplo.com
#
# Después:
#   bash qsg-servidor.sh iniciar      tras reiniciar la PC: servidor + dirección https para el celular
#   bash qsg-servidor.sh tunel        abre la dirección https (fija con Tailscale; si no, temporal)
#   bash qsg-servidor.sh revisar      chequeo previo: qué hay instalado (no cambia nada)
#   bash qsg-servidor.sh estado       qué está corriendo y en qué direcciones
#   bash qsg-servidor.sh cuenta correo   crea o renueva su cuenta (contraseña nueva)
#   bash qsg-servidor.sh asegurar     operación real: apaga usuarios y cuadrillas de demostración
#   bash qsg-servidor.sh actualizar   trae la última versión de GitHub y la aplica
#   bash qsg-servidor.sh detener      apaga el servidor y el túnel
#
# Opciones de «instalar»: --sin-demo (sin datos de demostración) y --sin-tunel (solo red local).
# Variables: QSG_CARPETA (carpeta, por omisión "$HOME/PMO QSG"), QSG_RAMA, PUERTO (8080).
set -euo pipefail

REPO_URL="https://github.com/ingcpmo/PMO.git"
RAMA="${QSG_RAMA:-claude/optimistic-noether-2uct53}"
APK_URL="https://github.com/ingcpmo/PMO/releases/download/qsg-campo-android/QSG-Campo.apk"
PUERTO="${PUERTO:-8080}"

# Carpeta del servidor: el repositorio donde está este script, o "$HOME/PMO QSG"
AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -f "$AQUI/../pc/docker-compose.yml" ] && [ -z "${QSG_CARPETA:-}" ]; then
  CARPETA="$(cd "$AQUI/../.." && pwd)"
else
  CARPETA="${QSG_CARPETA:-$HOME/PMO QSG}"
fi
PC="$CARPETA/instalacion/pc"
ESTADO="$CARPETA/.qsg"

info() { printf '\n==> %s\n' "$*"; }
trap 'printf "\n\nInterrumpido. Puede retomar con el mismo comando: lo ya descargado se reutiliza.\n" >&2; exit 130' INT TERM
aviso() { printf 'Aviso: %s\n' "$*" >&2; }
falla() { printf '\nError: %s\n' "$*" >&2; exit 1; }
pregunta() { # pregunta "texto" -> 0 si responde sí (por omisión sí)
  local r
  [ -t 0 ] || return 0
  read -r -p "$1 [S/n] " r
  [[ -z "$r" || "$r" =~ ^[SsYy] ]]
}

# ---------------------------------------------------------------------------- requisitos
DOCKER=(docker)
usar_docker() {
  if docker info >/dev/null 2>&1; then
    DOCKER=(docker)
  elif sudo docker info >/dev/null 2>&1; then
    DOCKER=(sudo docker)
  else
    falla "Docker no responde. Pruebe: sudo systemctl start docker"
  fi
}
dc() { (cd "$PC" && "${DOCKER[@]}" compose "$@"); }

instalar_paquete() {
  if command -v apt-get >/dev/null; then sudo apt-get update -qq && sudo apt-get install -y -qq "$@"
  elif command -v dnf >/dev/null; then sudo dnf install -y -q "$@"
  elif command -v pacman >/dev/null; then sudo pacman -S --noconfirm "$@"
  else falla "Instale a mano: $*"
  fi
}

requisitos() {
  [ "$(uname -s)" = "Linux" ] || falla "Este script es para Linux."
  for p in git curl; do
    command -v "$p" >/dev/null || { info "Instalando $p"; instalar_paquete "$p"; }
  done
  if ! command -v docker >/dev/null; then
    pregunta "No encuentro Docker. ¿Lo instalo ahora (instalador oficial de docker.com, pide su contraseña)?" \
      || falla "QSG PMO necesita Docker: https://docs.docker.com/engine/install/"
    curl -fsSL https://get.docker.com | sudo sh
    sudo systemctl enable --now docker
    sudo usermod -aG docker "${USER:-$(id -un)}" \
      && aviso "Su usuario quedó en el grupo docker; desde su próxima sesión no hará falta sudo."
  fi
  usar_docker
  if ! "${DOCKER[@]}" compose version >/dev/null 2>&1; then
    info "Instalando Docker Compose"
    instalar_paquete docker-compose-plugin 2>/dev/null || instalar_paquete docker-compose-v2
  fi
  if ! "${DOCKER[@]}" buildx version >/dev/null 2>&1; then
    info "Instalando Docker Buildx (lo necesita la construcción de la imagen)"
    instalar_paquete docker-buildx-plugin 2>/dev/null || instalar_paquete docker-buildx \
      || falla "no pude instalar buildx. Instálelo a mano: sudo apt-get install -y docker-buildx"
  fi

  local mem_gb disco_gb
  mem_gb=$(awk '/MemTotal/ {printf "%d", $2/1048576}' /proc/meminfo)
  [ "${mem_gb:-0}" -ge 4 ] || aviso "la PC tiene ${mem_gb} GB de memoria; ERPNext necesita al menos 4 GB."
  mkdir -p "$CARPETA"
  disco_gb=$(df -Pk "$CARPETA" | awk 'NR==2 {printf "%d", $4/1048576}')
  [ "${disco_gb:-0}" -ge 10 ] || falla "quedan ${disco_gb} GB libres; la instalación ocupa unos 8 GB y necesita margen. Libere espacio (docker system prune)."
  [ "${disco_gb:-0}" -ge 15 ] || aviso "quedan ${disco_gb} GB libres: alcanza, pero queda justo."
}

# ---------------------------------------------------------------------------- código
obtener_codigo() {
  mkdir -p "$CARPETA"
  if [ ! -d "$CARPETA/.git" ]; then
    info "Descargando QSG PMO en «$CARPETA» (rama $RAMA)"
    git -C "$CARPETA" init -q
    git -C "$CARPETA" remote add origin "$REPO_URL"
  fi
  git -C "$CARPETA" fetch -q origin "+refs/heads/$RAMA:refs/remotes/origin/$RAMA"
  if git -C "$CARPETA" rev-parse -q --verify HEAD >/dev/null; then
    git -C "$CARPETA" merge -q --ff-only "origin/$RAMA" \
      || aviso "no se pudo actualizar el código (¿cambios locales?); se usa el que ya tiene."
  else
    git -C "$CARPETA" checkout -q -B "$RAMA" "origin/$RAMA"
  fi
  [ -f "$PC/docker-compose.yml" ] || falla "no encuentro instalacion/pc/docker-compose.yml en «$CARPETA»."
}

# ---------------------------------------------------------------------------- servidor
config_env() { # config_env CLAVE VALOR: escribe o reemplaza la línea en .env
  touch "$PC/.env"
  if grep -q "^$1=" "$PC/.env"; then sed -i "s|^$1=.*|$1=$2|" "$PC/.env"; else echo "$1=$2" >> "$PC/.env"; fi
}

traer_imagen() {
  # Primero el espejo público de Google de Docker Hub (rápido y sin límite de descargas); si falla o
  # no termina en 60 minutos, Docker Hub. Las capas ya bajadas se conservan entre intentos. La imagen queda con su nombre original.
  if "${DOCKER[@]}" image inspect "$1" >/dev/null 2>&1; then echo "  ya está: $1"; return 0; fi
  local espejo="mirror.gcr.io/$1" origen
  [[ "$1" == */* ]] || espejo="mirror.gcr.io/library/$1"
  for origen in "$espejo" "$1"; do
    echo "  descargando $origen (muestra el avance; puede tardar varios minutos)"
    if timeout 60m "${DOCKER[@]}" pull "$origen"; then
      [ "$origen" = "$1" ] || "${DOCKER[@]}" tag "$origen" "$1"
      return 0
    fi
    echo "  no se pudo con $origen; probando la otra fuente"
  done
  return 1
}

esperar_web() {
  local i
  for i in $(seq 1 120); do
    curl -sf "http://localhost:$PUERTO/api/method/ping" >/dev/null && return 0
    sleep 3
  done
  falla "el servidor no responde en el puerto $PUERTO. Revise: cd \"$PC\" && docker compose logs --tail 50"
}

bench() { dc exec -T backend bench --site frontend "$@"; }

levantar_servidor() {
  local demo="$1"
  if [ ! -f "$PC/.env" ] || ! grep -q '^ADMIN_PASSWORD=' "$PC/.env"; then
    gen() { LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c "$1" || true; }
    "${DOCKER[@]}" volume inspect qsg-pmo_db-data >/dev/null 2>&1 \
      && falla "hay una base de datos anterior sin instalacion/pc/.env. Restaure ese archivo o borre la anterior: docker volume rm qsg-pmo_db-data qsg-pmo_sites"
    config_env DB_ROOT_PASSWORD "$(gen 24)"
    config_env ADMIN_PASSWORD "Qsg-$(gen 12)"
    chmod 600 "$PC/.env"
  fi
  config_env PUERTO "$PUERTO"
  config_env CARGAR_DEMO "$demo"

  info "Descargando las imágenes base (la primera vez, unos 2 GB; se ve el avance)"
  local version imagen
  version="$(sed -n 's/^ *ERPNEXT_VERSION: *//p' "$PC/docker-compose.yml" | head -1)"
  for imagen in "frappe/erpnext:$version" $(dc config --images | grep -v '^qsg-pmo' | sort -u); do
    traer_imagen "$imagen" || falla "no se pudo descargar $imagen. Revise la conexión y repita el comando."
  done

  info "Construyendo la imagen de QSG PMO (5 a 15 minutos la primera vez)"
  dc build
  info "Creando el sitio (3 a 6 minutos la primera vez)"
  local servicios
  mapfile -t servicios < <(dc config --services | grep -vx frontend)
  dc up -d "${servicios[@]}"
  until [ "$("${DOCKER[@]}" inspect -f '{{.State.Status}}' qsg-pmo-create-site-1 2>/dev/null)" = "exited" ]; do
    printf '.'; sleep 5
  done
  echo
  [ "$("${DOCKER[@]}" inspect -f '{{.State.ExitCode}}' qsg-pmo-create-site-1)" = "0" ] \
    || { dc logs --tail 40 create-site; falla "la creación del sitio falló."; }
  dc restart backend queue-short queue-long scheduler websocket >/dev/null

  if [ "$demo" = "1" ]; then
    info "Preparando la demostración (usuarios por rol y jornada simulada)"
    bench set-config qsg_demo_vivo 1 >/dev/null
    bench execute qsg_pmo.inteligencia.demo_vivo.preparar_sitio >/dev/null
    bench execute qsg_pmo.inteligencia.demo_vivo.al_reanudar >/dev/null
  fi
  dc up -d frontend
  esperar_web
}

demo_activa() { bench execute qsg_pmo.inteligencia.demo_vivo.habilitado 2>/dev/null | grep -qx true; }

cuenta() {
  local correo="${1:-}" salida
  [ -n "$correo" ] || { [ -t 0 ] && read -r -p "Su correo: " correo; }
  correo="$(printf '%s' "$correo" | grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' | head -1 || true)"
  [[ "$correo" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]] || falla "el correo «$correo» no es válido."
  if ! demo_activa; then
    aviso "sin demostración, las cuentas se crean como Administrator en el escritorio: Usuario → Nuevo."
    return 0
  fi
  salida="$(bench execute qsg_pmo.inteligencia.demo_vivo.crear_cuenta_terminal --args "[\"$correo\"]" 2>&1)" \
    || { printf '%s\n' "$salida" | tail -5 >&2; falla "no se pudo crear la cuenta."; }
  linea_de() { printf '%s\n' "$salida" | sed -n "s/^$1: //p" | tail -1; }
  [ -z "$(linea_de ERROR)" ] || falla "no se creó la cuenta: $(linea_de ERROR)"
  printf '%s / %s\n' "$(linea_de USUARIO)" "$(linea_de CLAVE)" > "$ESTADO/cuenta.txt"
  chmod 600 "$ESTADO/cuenta.txt"
  printf '\nSu cuenta en QSG PMO:\n  Usuario:     %s\n  Contraseña:  %s\n' "$(linea_de USUARIO)" "$(linea_de CLAVE)"
}

abrir_firewall() { # solo para la red local; el túnel no necesita puertos abiertos
  if command -v ufw >/dev/null && sudo -n true 2>/dev/null && sudo ufw status 2>/dev/null | grep -q "Status: active"; then
    sudo ufw allow "$PUERTO/tcp" >/dev/null && info "Firewall: puerto $PUERTO abierto para la red local"
  elif command -v firewall-cmd >/dev/null && sudo -n true 2>/dev/null && sudo firewall-cmd --state >/dev/null 2>&1; then
    sudo firewall-cmd -q --add-port="$PUERTO/tcp" --permanent && sudo firewall-cmd -q --reload \
      && info "Firewall: puerto $PUERTO abierto para la red local"
  fi
}

# ---------------------------------------------------------------------------- dirección https
# Dos formas, sin abrir puertos del router y con websockets:
# - Tailscale Funnel (si Tailscale está instalado y conectado): dirección FIJA del equipo,
#   https://<equipo>.<red>.ts.net, que sigue igual después de reiniciar la PC.
# - Cloudflare Tunnel rápido (respaldo, sin cuenta): la dirección cambia cada vez.
# QSG_TUNEL=cloudflare fuerza el segundo.
detener_tunel() { # solo el de Cloudflare; Funnel se apaga con «detener»
  if [ -f "$ESTADO/tunel.pid" ]; then
    kill "$(cat "$ESTADO/tunel.pid")" 2>/dev/null || true
    rm -f "$ESTADO/tunel.pid"
  fi
  [ "$(cat "$ESTADO/tunel.tipo" 2>/dev/null)" = tailscale ] || rm -f "$ESTADO/tunel.url" "$ESTADO/tunel.tipo"
}

nombre_tailscale() { # equipo.red.ts.net, o vacío si Tailscale no está conectado
  command -v tailscale >/dev/null || return 0
  tailscale status --json 2>/dev/null | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    if d.get("BackendState") == "Running":
        print((d.get("Self") or {}).get("DNSName", "").rstrip("."))
except Exception:
    pass' 2>/dev/null || true
}

tunel_tailscale() {
  local dns salida
  dns="$(nombre_tailscale)"
  [ -n "$dns" ] || return 1
  info "Publicando QSG PMO con Tailscale Funnel en https://$dns (dirección fija)"
  if ! salida="$(timeout 40 sudo tailscale funnel --bg "$PUERTO" 2>&1)"; then
    printf '%s\n' "$salida" | tail -6 >&2
    if printf '%s' "$salida" | grep -qi "login.tailscale.com"; then
      aviso "Funnel no está habilitado en su red de Tailscale. Abra el enlace de arriba, habilítelo y repita: bash qsg-servidor.sh tunel"
    fi
    return 1
  fi
  echo "https://$dns" >"$ESTADO/tunel.url"
  echo tailscale >"$ESTADO/tunel.tipo"
  local i
  for i in $(seq 1 30); do curl -sf "https://$dns/api/method/ping" >/dev/null && break; sleep 2; done
}

tunel_cloudflare() {
  local bin="$ESTADO/cloudflared" arq url i
  if [ ! -x "$bin" ]; then
    case "$(uname -m)" in
      x86_64 | amd64) arq=amd64 ;;
      aarch64 | arm64) arq=arm64 ;;
      armv7l | armhf) arq=arm ;;
      *) falla "arquitectura $(uname -m) sin cloudflared; use la red local." ;;
    esac
    info "Descargando cloudflared (túnel https de Cloudflare)"
    curl -fsSL -o "$bin.tmp" "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$arq"
    chmod +x "$bin.tmp" && mv "$bin.tmp" "$bin"
  fi
  rm -f "$ESTADO/tunel.url" "$ESTADO/tunel.tipo"
  nohup "$bin" tunnel --no-autoupdate --url "http://localhost:$PUERTO" >"$ESTADO/tunel.log" 2>&1 &
  echo $! >"$ESTADO/tunel.pid"
  url=""
  for i in $(seq 1 60); do
    url="$(grep -o 'https://[a-z0-9-]*\.trycloudflare\.com' "$ESTADO/tunel.log" | grep -v '//api\.' | head -1 || true)"
    [ -n "$url" ] && break
    sleep 1
  done
  if [ -z "$url" ]; then
    tail -5 "$ESTADO/tunel.log" >&2
    aviso "no se pudo abrir el túnel; el celular puede usar la red local."
    return 0
  fi
  echo "$url" >"$ESTADO/tunel.url"
  echo cloudflare >"$ESTADO/tunel.tipo"
  for i in $(seq 1 30); do curl -sf "$url/api/method/ping" >/dev/null && break; sleep 2; done
}

tunel() {
  mkdir -p "$ESTADO"
  detener_tunel
  if [ "${QSG_TUNEL:-auto}" != cloudflare ] && tunel_tailscale; then
    return 0
  fi
  [ -n "$(nombre_tailscale)" ] && [ "${QSG_TUNEL:-auto}" != cloudflare ] \
    && aviso "se usa Cloudflare mientras tanto (dirección temporal)."
  tunel_cloudflare
}

tunel_activo() {
  case "$(cat "$ESTADO/tunel.tipo" 2>/dev/null)" in
    tailscale) command -v tailscale >/dev/null && tailscale funnel status 2>/dev/null | grep -q "$PUERTO" ;;
    cloudflare) [ -f "$ESTADO/tunel.pid" ] && kill -0 "$(cat "$ESTADO/tunel.pid")" 2>/dev/null ;;
    *) return 1 ;;
  esac
}

ip_local() {
  local x=""
  x="$(ip route get 1.1.1.1 2>/dev/null | awk '{for (i = 1; i < NF; i++) if ($i == "src") print $(i + 1)}' | head -1)" || true
  [ -n "$x" ] || x="$(hostname -I 2>/dev/null | awk '{print $1}')" || true
  printf '%s' "$x"
}

resumen() {
  local ip url admin
  ip="$(ip_local)"
  url="$(cat "$ESTADO/tunel.url" 2>/dev/null || true)"
  admin="$(grep '^ADMIN_PASSWORD=' "$PC/.env" | cut -d= -f2-)"
  cat <<MSG

==================================================================================
QSG PMO corre en esta PC ($(hostname)), carpeta «$CARPETA».

  En esta PC:            http://localhost:$PUERTO        (tablero: /despacho)
  En la red local:       http://${ip:-<IP-de-la-PC>}:$PUERTO   (celular en la misma Wi-Fi, sin GPS)
  Dirección https:       ${url:-(sin túnel: bash qsg-servidor.sh tunel)}$( [ "$(cat "$ESTADO/tunel.tipo" 2>/dev/null)" = tailscale ] && echo "   (fija)" || { [ -n "$url" ] && echo "   (cambia al reiniciar)"; } )

App Android (un solo APK para administrador y contratistas): $APK_URL
  Al abrirla, escriba la dirección https de arriba (con ella funcionan el GPS y la cámara).
  El administrador entra a su tablero y el contratista a sus órdenes, según su usuario.
  Si la dirección cambia, al abrir la app toque «Cambiar servidor» mientras dice «Conectando».

Usuarios:
  Administrador:  Administrator / $admin   (en instalacion/pc/.env)
MSG
  if [ -f "$ESTADO/cuenta.txt" ]; then echo "  Su cuenta:      $(cat "$ESTADO/cuenta.txt")"; fi
  if demo_activa && bench execute frappe.db.get_value --args '["User", "despacho@qsg.pr", "enabled"]' 2>/dev/null | grep -qx 1; then
    cat <<MSG
  Demostración:   despacho@qsg.pr / Demo-QSG-2026!   tecnico@qsg.pr / Campo2026!
  Ojo: con la dirección https cualquiera que la conozca puede probar estos usuarios.
  Para operación real apáguelos con: bash qsg-servidor.sh asegurar
MSG
  fi
  cat <<MSG

Tras reiniciar la PC:  bash "$CARPETA/instalacion/linux/qsg-servidor.sh" iniciar
==================================================================================
MSG
}

# ---------------------------------------------------------------------------- órdenes
orden="${1:-instalar}"
[ $# -gt 0 ] && shift
case "$orden" in
  instalar)
    demo=1 con_tunel=1 correo="${QSG_CORREO:-}"
    for a in "$@"; do
      case "$a" in
        --sin-demo) demo=0 ;;
        --sin-tunel) con_tunel=0 ;;
        *@*) correo="$a" ;;
        *) falla "opción desconocida: $a" ;;
      esac
    done
    requisitos
    otra="$("${DOCKER[@]}" ps -a --filter label=com.docker.compose.project=qsg-pmo \
      --format '{{.Label "com.docker.compose.project.working_dir"}}' 2>/dev/null | head -1)"
    otra="${otra%/instalacion/pc}"
    if [ -n "$otra" ] && [ "$otra" != "$CARPETA" ]; then
      falla "QSG PMO ya está instalado en «$otra». No reinstale: use
  QSG_CARPETA=\"$otra\" bash \"$otra/instalacion/linux/qsg-servidor.sh\" iniciar
(o revise con: bash qsg-revisar.sh)"
    fi
    obtener_codigo
    mkdir -p "$ESTADO"
    levantar_servidor "$demo"
    if [ -n "$correo" ]; then cuenta "$correo"; fi
    abrir_firewall
    if [ "$con_tunel" = "1" ]; then tunel; fi
    resumen
    ;;
  iniciar)
    usar_docker
    mkdir -p "$ESTADO"
    dc up -d
    esperar_web
    bench execute qsg_pmo.inteligencia.demo_vivo.al_reanudar >/dev/null 2>&1 || true
    tunel
    resumen
    ;;
  tunel) usar_docker; tunel; resumen ;;
  revisar)
    if [ -f "$CARPETA/instalacion/linux/qsg-revisar.sh" ]; then bash "$CARPETA/instalacion/linux/qsg-revisar.sh" "$CARPETA"
    else bash <(curl -fsSL "https://raw.githubusercontent.com/ingcpmo/PMO/$RAMA/instalacion/linux/qsg-revisar.sh") "$CARPETA"; fi
    ;;
  estado)
    usar_docker
    dc ps --format 'table {{.Service}}\t{{.Status}}'
    if tunel_activo; then
      echo "Dirección https ($(cat "$ESTADO/tunel.tipo")): $(cat "$ESTADO/tunel.url" 2>/dev/null)"
    else
      echo "Dirección https: apagada (bash qsg-servidor.sh tunel)"
      rm -f "$ESTADO/tunel.url" "$ESTADO/tunel.tipo"
    fi
    resumen
    ;;
  cuenta) usar_docker; mkdir -p "$ESTADO"; cuenta "${1:-}" ;;
  actualizar)
    usar_docker
    obtener_codigo
    dc build
    dc up -d
    esperar_web
    bench migrate
    echo "QSG PMO actualizado."
    ;;
  detener)
    usar_docker
    if [ "$(cat "$ESTADO/tunel.tipo" 2>/dev/null)" = tailscale ]; then
      sudo tailscale funnel --https=443 off >/dev/null 2>&1 || sudo tailscale funnel reset >/dev/null 2>&1 || true
      rm -f "$ESTADO/tunel.url" "$ESTADO/tunel.tipo"
    fi
    detener_tunel
    dc stop
    echo "QSG PMO detenido."
    ;;
  asegurar)
    # Operación real: desactiva los usuarios y cuadrillas de demostración (contraseñas públicas)
    usar_docker
    salida="$(bench execute qsg_pmo.inteligencia.perfiles.desactivar_demo --kwargs '{"cuadrillas": 1}' 2>&1)" \
      || { printf '%s\n' "$salida" | tail -5 >&2; falla "no se pudo asegurar."; }
    echo "Usuarios de demostración desactivados: $(printf '%s\n' "$salida" | sed -n 's/^USUARIOS: //p')"
    echo "Cuadrillas de demostración desactivadas: $(printf '%s\n' "$salida" | sed -n 's/^CUADRILLAS: //p')"
    echo "Sus contratistas reales se dan de alta en el tablero: pestaña «Equipo»."
    ;;
  -h | --help | ayuda) sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//' ;;
  *) falla "orden desconocida: $orden (use: revisar, instalar, iniciar, tunel, estado, cuenta, asegurar, actualizar, detener)" ;;
esac
