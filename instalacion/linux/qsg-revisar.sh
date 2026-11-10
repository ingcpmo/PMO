#!/usr/bin/env bash
# Revisa esta PC ANTES de instalar QSG PMO: qué hay instalado y qué se puede reutilizar.
# Solo mira; no instala, no borra y no cambia nada.
#   bash qsg-revisar.sh                    (revisa y recomienda para "$HOME/PMO QSG")
#   bash qsg-revisar.sh "/ruta/de/destino"  (otra carpeta de destino)
set -uo pipefail
export LC_NUMERIC=C

USUARIO="${SUDO_USER:-${USER:-$(id -un)}}"
CASA="$(getent passwd "$USUARIO" 2>/dev/null | cut -d: -f6)"
CASA="${CASA:-$HOME}"
DESTINO="${1:-${QSG_CARPETA:-$CASA/PMO QSG}}"
PUERTO="${PUERTO:-8080}"

ok() { printf '  [✔] %s\n' "$*"; }
no() { printf '  [✘] %s\n' "$*"; }
ojo() { printf '  [!] %s\n' "$*"; }
titulo() { printf '\n== %s\n' "$*"; }
tiene() { command -v "$1" >/dev/null 2>&1; }

RECOMENDACIONES=()
recomendar() { RECOMENDACIONES+=("$*"); }

echo "Revisión de QSG PMO en $(hostname) — $(date '+%Y-%m-%d %H:%M')"
echo "Usuario: $USUARIO   Carpeta de destino: «$DESTINO»"

# ------------------------------------------------------------------ 1. equipo
titulo "1. Equipo"
if [ -r /etc/os-release ]; then . /etc/os-release; ok "Sistema: ${PRETTY_NAME:-Linux} ($(uname -m))"; fi
MEM=$(LC_ALL=C awk '/MemTotal/ {printf "%.1f", $2/1048576}' /proc/meminfo)
if LC_ALL=C awk "BEGIN{exit !($MEM >= 4)}"; then ok "Memoria: $MEM GB"; else no "Memoria: $MEM GB (ERPNext necesita al menos 4 GB)"; fi
ok "Procesadores: $(nproc)"
mkdir_padre="$DESTINO"; while [ ! -d "$mkdir_padre" ]; do mkdir_padre="$(dirname "$mkdir_padre")"; done
LIBRE=$(df -Pk "$mkdir_padre" | awk 'NR==2 {printf "%d", $4/1048576}')
if [ "$LIBRE" -ge 15 ]; then ok "Disco libre: $LIBRE GB"
elif [ "$LIBRE" -ge 10 ]; then
  ojo "Disco libre: $LIBRE GB. Alcanza (la instalación ocupa unos 8 GB), pero queda justo."
  recomendar "Si necesita espacio: docker builder prune -f && docker image prune -f (solo caché y restos; no toca otros proyectos) y vacíe la papelera."
else
  no "Disco libre: $LIBRE GB. No alcanza: la instalación ocupa unos 8 GB y necesita margen."
  recomendar "Libere al menos 10 GB antes de instalar."
fi

# ------------------------------------------------------------------ 2. herramientas
titulo "2. Herramientas"
for p in git curl; do
  if tiene "$p"; then ok "$p instalado"; else ojo "$p no está (el instalador lo pone)"; fi
done
DOCKER=()
if tiene docker; then
  ok "Docker instalado: $(docker --version 2>/dev/null | sed 's/Docker version //')"
  if docker info >/dev/null 2>&1; then
    DOCKER=(docker); ok "Docker está corriendo y su usuario lo puede usar"
  elif sudo -n docker info >/dev/null 2>&1; then
    DOCKER=(sudo -n docker); ojo "Docker corre, pero su usuario necesita sudo (no está en el grupo docker)"
  elif systemctl is-active --quiet docker 2>/dev/null; then
    ojo "Docker corre, pero no pude consultarlo sin contraseña. Para ver todo: sudo bash $0"
  else
    no "Docker está instalado pero apagado: sudo systemctl start docker"
  fi
  if [ ${#DOCKER[@]} -gt 0 ]; then
    if "${DOCKER[@]}" compose version >/dev/null 2>&1; then ok "Docker Compose: $("${DOCKER[@]}" compose version --short 2>/dev/null)"
    else ojo "Falta Docker Compose (el instalador lo pone)"; fi
    if "${DOCKER[@]}" buildx version >/dev/null 2>&1; then ok "Docker Buildx: $("${DOCKER[@]}" buildx version 2>/dev/null | awk '{print $2}')"
    else
      no "Falta Docker Buildx: sin él la construcción de la imagen no arranca (el instalador lo pone)"
      recomendar "Falta buildx. El instalador lo instala; a mano: sudo apt-get install -y docker-buildx (o docker-buildx-plugin)"
    fi
  fi
  if tiene dpkg-query; then
    PAQ=$(dpkg-query -W -f='${Package} ' docker.io docker-ce 2>/dev/null || true)
    [ -n "$PAQ" ] && ok "Docker viene del paquete: $PAQ"
  fi
else
  ojo "Docker no está instalado (el instalador lo instala)"
fi

# ------------------------------------------------------------------ 2b. internet
titulo "2b. Conexión a internet (descargas)"
for u in https://github.com https://registry-1.docker.io/v2/ https://mirror.gcr.io/v2/ https://download.docker.com; do
  c=$(curl -s -o /dev/null -m 10 -w '%{http_code}' "$u" 2>/dev/null || true)
  if [ -n "$c" ] && [ "$c" != 000 ]; then ok "$u responde"; else no "$u no responde"; fi
done

# ------------------------------------------------------------------ 3. QSG PMO en Docker
titulo "3. QSG PMO en Docker"
CARPETA_DOCKER=""
DATOS=0
if [ ${#DOCKER[@]} -gt 0 ]; then
  CONT=$("${DOCKER[@]}" ps -a --filter "label=com.docker.compose.project=qsg-pmo" --format '{{.Names}}\t{{.Status}}' 2>/dev/null)
  if [ -n "$CONT" ]; then
    CARPETA_DOCKER=$("${DOCKER[@]}" ps -a --filter "label=com.docker.compose.project=qsg-pmo" \
      --format '{{.Label "com.docker.compose.project.working_dir"}}' | head -1)
    ok "Hay contenedores de QSG PMO, instalados desde: «${CARPETA_DOCKER%/instalacion/pc}»"
    printf '%s\n' "$CONT" | sed 's/^/        /'
  else
    no "No hay contenedores de QSG PMO"
  fi
  for v in qsg-pmo_db-data qsg-pmo_sites; do
    if "${DOCKER[@]}" volume inspect "$v" >/dev/null 2>&1; then
      DATOS=1; ok "Volumen $v existe (datos de una instalación anterior)"
    fi
  done
  [ "$DATOS" = 1 ] || no "No hay base de datos de QSG PMO"
  IMG=$("${DOCKER[@]}" images --format '{{.Repository}}:{{.Tag}} ({{.Size}})' 2>/dev/null | grep -E '^(qsg-pmo:local|frappe/erpnext:|mariadb:11\.8|redis:6\.2-alpine|mirror\.gcr\.io/)' || true)
  if [ -n "$IMG" ]; then ok "Imágenes ya descargadas (ahorran tiempo):"; printf '%s\n' "$IMG" | sed 's/^/        /'; fi
  OTROS=$("${DOCKER[@]}" ps -a --format '{{.Names}}\t{{.Image}}\t{{.Label "com.docker.compose.project"}}' 2>/dev/null \
    | grep -Ei 'frappe|erpnext' | grep -v $'\tqsg-pmo$' || true)
  if [ -n "$OTROS" ]; then ojo "Otros contenedores de Frappe/ERPNext (otro proyecto):"; printf '%s\n' "$OTROS" | sed 's/^/        /'; fi
else
  ojo "No se pudo consultar Docker; esta sección queda incompleta"
fi

# ------------------------------------------------------------------ 4. servidor respondiendo
titulo "4. ¿Responde un servidor en el puerto $PUERTO?"
if curl -sf -m 5 "http://localhost:$PUERTO/api/method/ping" 2>/dev/null | grep -q pong; then
  ok "Sí: hay Frappe/ERPNext respondiendo en http://localhost:$PUERTO"
  CODIGO=$(curl -s -o /dev/null -m 5 -w '%{http_code}' "http://localhost:$PUERTO/assets/qsg_pmo/js/despacho.js")
  if [ "$CODIGO" = 200 ]; then ok "Es QSG PMO con la inteligencia operativa (tablero /despacho)"
  else ojo "Responde, pero no tiene el tablero de QSG PMO v0.4 (versión anterior u otra app)"; fi
  SERVIDOR_ARRIBA=1
else
  SERVIDOR_ARRIBA=0
  if (ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep -qE "[:.]$PUERTO\b"; then
    no "El puerto $PUERTO está ocupado por otro programa (use PUERTO=8081 al instalar)"
    recomendar "El puerto $PUERTO está ocupado: instale con  PUERTO=8081 bash qsg-servidor.sh instalar su-correo"
  else
    ok "No hay nada en el puerto $PUERTO (libre para instalar)"
  fi
fi
for p in 3306 6379 8000; do
  if (ss -ltn 2>/dev/null || netstat -ltn 2>/dev/null) | grep -qE "[:.]$p\b"; then
    ojo "Puerto $p en uso por otro programa u otro proyecto. No estorba: QSG PMO no publica ese puerto."
  fi
done

# ------------------------------------------------------------------ 5. copias del código en disco
titulo "5. Copias de QSG PMO en el disco"
mapfile -t COPIAS < <(find "$CASA" "$HOME" /home /opt /srv /var/www -maxdepth 7 \
  \( -name node_modules -o -name .cache -o -name .local -o -name snap -o -name .git -o -name frappe-bench \) -prune \
  -o -type f -path '*/instalacion/pc/docker-compose.yml' -print 2>/dev/null | sed 's|/instalacion/pc/docker-compose.yml$||' | sort -u)
if [ ${#COPIAS[@]} -eq 0 ]; then
  no "No encontré copias del código"
fi
for c in "${COPIAS[@]}"; do
  [ -n "$c" ] || continue
  rama=$(git -C "$c" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "sin git")
  fecha=$(git -C "$c" log -1 --format='%cd' --date=short 2>/dev/null || echo "?")
  linux=$([ -f "$c/instalacion/linux/qsg-servidor.sh" ] && echo "trae el script de Linux" || echo "versión anterior, sin el script de Linux")
  env=$([ -f "$c/instalacion/pc/.env" ] && echo "tiene .env (contraseñas de esa instalación)" || echo "sin .env")
  ok "«$c»"
  echo "        rama $rama, último cambio $fecha; $linux; $env"
  [ -f "$c/.qsg/tunel.url" ] && echo "        último túnel: $(cat "$c/.qsg/tunel.url")"
done
if [ -d "$DESTINO" ]; then
  if [ -z "$(ls -A "$DESTINO" 2>/dev/null)" ]; then ok "La carpeta de destino existe y está vacía"
  elif [ -f "$DESTINO/instalacion/pc/docker-compose.yml" ]; then ok "La carpeta de destino ya tiene el código de QSG PMO (se reutiliza)"
  else ojo "La carpeta de destino ya tiene archivos: $(ls -A "$DESTINO" | head -5 | tr '\n' ' ')"; fi
else
  ok "La carpeta de destino no existe todavía (el instalador la crea)"
fi

# ------------------------------------------------------------------ 6. Frappe fuera de Docker y túnel
titulo "6. Otros"
if tiene bench; then ojo "Hay un «bench» de Frappe instalado fuera de Docker: $(command -v bench). No se usa ni se toca."; fi
BENCHES=$(find "$CASA" /opt /srv -maxdepth 4 -type d -name frappe-bench 2>/dev/null | head -5)
[ -n "$BENCHES" ] && { ojo "Carpetas frappe-bench (instalaciones manuales; no se tocan):"; printf '%s\n' "$BENCHES" | sed 's/^/        /'; }
if pgrep -f "cloudflared.*tunnel" >/dev/null 2>&1; then ok "Hay un túnel cloudflared corriendo"; else no "No hay túnel cloudflared corriendo"; fi

# ------------------------------------------------------------------ 7. recomendación
titulo "7. Qué hacer"
DOCKER_DIR="${CARPETA_DOCKER%/instalacion/pc}"
if [ -n "$DOCKER_DIR" ]; then
  if [ -f "$DOCKER_DIR/instalacion/linux/qsg-servidor.sh" ]; then
    S="QSG_CARPETA=\"$DOCKER_DIR\" bash \"$DOCKER_DIR/instalacion/linux/qsg-servidor.sh\""
  else
    S="QSG_CARPETA=\"$DOCKER_DIR\" bash qsg-servidor.sh"
  fi
  if [ "$SERVIDOR_ARRIBA" = 1 ]; then
    echo "  QSG PMO YA ESTÁ INSTALADO y funcionando desde «$DOCKER_DIR». No hace falta reinstalar."
  else
    echo "  QSG PMO YA ESTÁ INSTALADO en «$DOCKER_DIR», pero apagado. No hace falta reinstalar."
  fi
  echo "    Encenderlo y abrir la dirección https:   $S iniciar"
  echo "    Traer la última versión (conserva datos): $S actualizar"
  echo "    Ver direcciones y usuarios:                $S estado"
  if [ "$DOCKER_DIR" != "$DESTINO" ]; then
    echo "  Está en otra carpeta que «$DESTINO». Úsela tal cual (lo más simple), o muévala:"
    echo "    $S detener && mv \"$DOCKER_DIR\" \"$DESTINO\""
    echo "    y después: QSG_CARPETA=\"$DESTINO\" bash \"$DESTINO/instalacion/linux/qsg-servidor.sh\" iniciar"
  fi
elif [ "$DATOS" = 1 ]; then
  echo "  Hay DATOS de una instalación anterior (base de datos en Docker), sin contenedores."
  ENV_VIEJO=""
  for c in "${COPIAS[@]}"; do [ -f "$c/instalacion/pc/.env" ] && ENV_VIEJO="$c/instalacion/pc/.env" && break; done
  if [ -n "$ENV_VIEJO" ]; then
    echo "  Para reutilizarlos, copie las contraseñas de esa instalación antes de instalar:"
    echo "    mkdir -p \"$DESTINO/instalacion/pc\" && cp \"$ENV_VIEJO\" \"$DESTINO/instalacion/pc/.env\""
    echo "    y luego instale normalmente; conservará la base de datos."
  else
    echo "  No encontré el .env con sus contraseñas. Si no necesita esos datos, bórrelos para empezar limpio:"
    echo "    docker volume rm qsg-pmo_db-data qsg-pmo_sites qsg-pmo_logs qsg-pmo_redis-queue-data"
  fi
elif [ ${#COPIAS[@]} -gt 0 ] && [ -n "${COPIAS[0]}" ]; then
  echo "  Hay código descargado pero nada instalado en Docker (una instalación que no terminó)."
  echo "  Se puede continuar ahí mismo: el instalador reutiliza el código, el .env y las imágenes"
  echo "  ya descargadas. Copias encontradas:"
  for c in "${COPIAS[@]}"; do echo "    «$c»"; done
else
  echo "  La PC está limpia: puede instalar en «$DESTINO» sin conflictos."
fi
for r in "${RECOMENDACIONES[@]}"; do echo "  $r"; done
echo
