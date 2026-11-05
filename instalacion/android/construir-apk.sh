#!/usr/bin/env bash
# Construye la app Android "QSG Campo" (APK) apuntando a su servidor de QSG PMO.
#   ./construir-apk.sh http://192.168.1.50:8080
# Requisitos: Node 22+, JDK 21 y Android SDK (Android Studio los instala).
# Si no quiere instalar nada, use la opción en la nube (GitHub Actions) del README.
set -euo pipefail
cd "$(dirname "$0")"
SERVIDOR="${1:-${QSG_SERVIDOR:-}}"
if [ -z "$SERVIDOR" ]; then
  read -r -p "Dirección de QSG PMO (ej. http://192.168.1.50:8080): " SERVIDOR
fi
command -v node >/dev/null || { echo "Falta Node.js 22 o superior: https://nodejs.org"; exit 1; }
command -v java >/dev/null || { echo "Falta Java 21 (viene con Android Studio)."; exit 1; }
if [ -z "${ANDROID_HOME:-}${ANDROID_SDK_ROOT:-}" ]; then
  for d in "$HOME/Library/Android/sdk" "$HOME/Android/Sdk"; do [ -d "$d" ] && export ANDROID_HOME="$d"; done
fi
[ -n "${ANDROID_HOME:-}${ANDROID_SDK_ROOT:-}" ] || { echo "Falta el Android SDK. Instale Android Studio y ábralo una vez."; exit 1; }

npm install --no-audit --no-fund
node preparar.mjs "$SERVIDOR"
[ -d android ] || npx cap add android
npx cap sync android
node preparar.mjs --android
(cd android && chmod +x gradlew && ./gradlew --no-daemon assembleDebug)
mkdir -p salida
cp android/app/build/outputs/apk/debug/app-debug.apk salida/QSG-Campo.apk
echo
echo "Listo: $(pwd)/salida/QSG-Campo.apk"
echo "Cópielo al celular (cable, Drive o WhatsApp) y ábralo para instalar."
