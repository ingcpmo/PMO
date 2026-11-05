# QSG PMO en GitHub Codespaces

Este Codespace instala QSG PMO completo (ERPNext v16 + la app) con datos de demostración. El primer
arranque tarda **10 a 15 minutos**: siga el avance en la terminal *Creating codespace*. Cuando la app
ya responde, la terminal muestra «QSG PMO está listo» y el navegador la abre solo. Si no se abre:
pestaña **Ports** → puerto **8080 (QSG PMO)** → clic en el globo.

## Usuarios de la demostración

| Para ver | Dirección | Usuario | Contraseña |
|---|---|---|---|
| Tablero de despacho | `/despacho` | despacho@qsg.pr | Demo-QSG-2026! |
| App del técnico | `/campo` | tecnico@qsg.pr | Campo2026! |
| Gerencia | `/app/qsg-pmo` | gerente@qsg.pr | Demo-QSG-2026! |
| Supervisor (solo su contratista) | `/despacho` | supervisor@fibraboricua.pr | Demo-QSG-2026! |
| Bodega | `/app/qsg-pmo` | bodega@qsg.pr | Demo-QSG-2026! |
| Administrador | `/app` | Administrator | en `instalacion/pc/.env` |

## Simular un día de trabajo

1. Entre a `/despacho` como despacho@qsg.pr.
2. Pulse **▶ Simular jornada**: cada 6 segundos las cuadrillas salen, avanzan por GPS, llegan y cierran órdenes (alguna sale fallida por cliente ausente).
3. Al tercer paso entra una **avería urgente sin asignar**: pestaña **Sin asignar** → **Mejor cuadrilla** → **Asignar**. La cuadrilla elegida va a atenderla.
4. **Reiniciar jornada** vuelve a empezar el día con las 8 órdenes de la demostración.

Mientras tanto, abra `/campo` como tecnico@qsg.pr (cuadrilla CUA-FTTH-01) en otra ventana o en el celular para ver cómo cambian sus órdenes.

## Verla en el celular (Android o iPhone)

El puerto es **privado**: solo usted lo abre, con su sesión de GitHub. Para el celular:

- Inicie sesión en GitHub en el navegador del celular y abra la misma dirección, o
- en la pestaña **Ports**, clic derecho en 8080 → **Port Visibility → Public** (cualquiera con la dirección podrá ver la página de inicio de sesión; vuelva a *Private* al terminar).

En Chrome de Android: menú ⋮ → **Agregar a la pantalla principal** sobre `/campo`, y queda como app.

## Cuidar las horas gratis

La cuenta personal de GitHub incluye 120 horas-núcleo al mes; esta máquina usa 4 núcleos (unas 30 horas de uso). Detenga el Codespace al terminar (menú **Codespaces → Stop current codespace**) y bórrelo cuando ya no lo necesite.
