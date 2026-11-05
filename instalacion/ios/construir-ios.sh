#!/usr/bin/env bash
# Construye la app de iPhone "QSG Campo" apuntando a su servidor de QSG PMO.
#   ./construir-ios.sh https://pmo.qsg.pr
# Requisitos: una Mac con Xcode (App Store) y Node 22+. Para instalarla en iPhones de la empresa
# hace falta además una cuenta de Apple Developer (vea el README).
set -euo pipefail
cd "$(dirname "$0")"
SERVIDOR="${1:-${QSG_SERVIDOR:-}}"
if [ -z "$SERVIDOR" ]; then
  read -r -p "Dirección de QSG PMO (ej. https://pmo.qsg.pr): " SERVIDOR
fi
[ "$(uname)" = "Darwin" ] || { echo "La app de iPhone solo se puede construir en una Mac con Xcode."; exit 1; }
command -v node >/dev/null || { echo "Falta Node.js 22 o superior: https://nodejs.org"; exit 1; }
command -v xcodebuild >/dev/null || { echo "Falta Xcode (instálelo desde la App Store y ábralo una vez)."; exit 1; }

npm install --no-audit --no-fund
node preparar.mjs "$SERVIDOR"
[ -d ios ] || npx cap add ios
npx cap sync ios
node preparar.mjs --ios

cd ios/App
if [ -d App.xcworkspace ]; then DESTINO=(-workspace App.xcworkspace); else DESTINO=(-project App.xcodeproj); fi
xcodebuild "${DESTINO[@]}" -scheme App -configuration Release -sdk iphonesimulator \
  -derivedDataPath build-sim CODE_SIGNING_ALLOWED=NO build | tail -5
cd ../..
mkdir -p salida
rm -rf salida/QSG-Campo-simulador.app
cp -R ios/App/build-sim/Build/Products/Release-iphonesimulator/App.app salida/QSG-Campo-simulador.app
echo
echo "Listo para el simulador: $(pwd)/salida/QSG-Campo-simulador.app"
echo "Para instalarla en iPhones: abra ios/App en Xcode, elija su equipo (Signing & Capabilities) y use"
echo "Product → Archive → Distribute App (TestFlight o Ad Hoc)."
