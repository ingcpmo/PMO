#!/usr/bin/env bash
# Crea (o renueva) su cuenta propia en la demostración de QSG PMO, con su correo:
#   bash .devcontainer/crear-cuenta.sh su-correo@ejemplo.com
# La cuenta es de gerencia: entra al tablero (/despacho), al escritorio y a la app de campo
# (/campo, también desde el APK de Android). Cada vez que se ejecuta genera una contraseña nueva.
set -euo pipefail
cd "$(dirname "$0")/../instalacion/pc"

CORREO="${1:-${QSG_CORREO:-}}"
if [ -z "$CORREO" ]; then
  read -r -p "Su correo: " CORREO
fi
CORREO="$(printf '%s' "$CORREO" | tr -d '[:space:]')"
if ! [[ "$CORREO" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$ ]]; then
  echo "El correo «${CORREO}» no es válido." >&2
  exit 1
fi

SALIDA="$(docker compose exec -T backend bench --site frontend execute \
  qsg_pmo.inteligencia.demo_vivo.crear_cuenta_terminal --args "[\"${CORREO}\"]" 2>&1)" || {
  printf '%s\n' "$SALIDA" | tail -5 >&2
  echo "No se pudo crear la cuenta. ¿Terminó el arranque de QSG PMO?" >&2
  exit 1
}
linea() { printf '%s\n' "$SALIDA" | sed -n "s/^$1: //p" | tail -1; }
ERROR="$(linea ERROR)"
if [ -n "$ERROR" ]; then
  echo "No se creó la cuenta: ${ERROR}" >&2
  exit 1
fi
CORREO="$(linea USUARIO)"
CLAVE="$(linea CLAVE)"
[ -n "$CLAVE" ] || { printf '%s\n' "$SALIDA" | tail -5 >&2; exit 1; }

cat <<MSG

Su cuenta en QSG PMO:
  Usuario:     ${CORREO}
  Contraseña:  ${CLAVE}

Sirve en el tablero (/despacho), en el escritorio y en la app de campo (/campo o el APK de Android).
Para cambiar la contraseña, vuelva a ejecutar: bash .devcontainer/crear-cuenta.sh ${CORREO}
MSG
