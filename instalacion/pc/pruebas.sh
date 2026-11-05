#!/usr/bin/env bash
# Ejecuta las pruebas automáticas de QSG PMO en un sitio aparte ("pruebas"),
# para no mezclarlas con sus datos. La primera vez crea ese sitio (2-4 minutos).
cd "$(dirname "$0")"
docker compose exec backend bash -c "if [ ! -d sites/pruebas ]; then bench new-site pruebas --mariadb-user-host-login-scope=% --admin-password=\$MYSQL_ROOT_PASSWORD --db-root-username=root --db-root-password=\$MYSQL_ROOT_PASSWORD --install-app erpnext --install-app qsg_pmo; fi; bench --site pruebas set-config allow_tests true && bench --site pruebas run-tests --app qsg_pmo"
