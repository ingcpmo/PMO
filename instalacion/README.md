# Instalación de QSG PMO

Cada carpeta instala QSG PMO en un entorno distinto. Haga las pruebas en este orden:

| Orden | Carpeta | Qué instala | Qué ejecutar |
|---|---|---|---|
| 1 | [`pc/`](pc/) | El servidor completo (oficina + app de campo) en una computadora con Windows, Mac o Linux | `pc/instalar.bat` (Windows) o `pc/instalar.sh` (Mac/Linux) |
| 2 | [`android/`](android/) | La app **QSG Campo** para los celulares Android de los técnicos | Acción en la nube *App Android (APK)* o `android/construir-apk.bat` |
| 3 | [`ios/`](ios/) | iPhone: por ahora desde Safari; la app nativa viene después | Ver `ios/README.md` |

El celular necesita un servidor al que conectarse. Para la primera prueba, ese servidor es la PC del paso 1, y el celular debe estar en la misma Wi-Fi.

```
GitHub (código)
   │
   ├── instalacion/pc       → PC con Docker: http://<IP-de-la-PC>:8080
   │                              ├── /app     ventanas de oficina (despacho, reportes)
   │                              └── /campo   app del técnico
   │
   └── instalacion/android  → QSG-Campo.apk  → abre http://<IP-de-la-PC>:8080/campo
                                                con GPS y cámara del teléfono
```
