# QSG Campo para iPhone

Fase 3, después de las pruebas en PC y Android.

## Hoy: desde Safari (sin instalar nada)

1. En el iPhone abra Safari en `https://<su-servidor>/campo` y entre.
2. Botón **Compartir** → **Agregar a inicio**.

Se abre a pantalla completa con el icono de QSG, cámara y firma. El GPS funciona cuando el servidor tiene **https** (servidor definitivo o un túnel como `cloudflared`).

## Siguiente: app nativa

La carpeta `android/` usa Capacitor, que también genera la app de iPhone con el mismo código. Para construirla hace falta una **Mac con Xcode** y una cuenta de **Apple Developer** (99 USD al año) para instalarla en los teléfonos con TestFlight. Cuando lleguemos a esta fase se agregará `construir-ipa.sh` en esta carpeta.
