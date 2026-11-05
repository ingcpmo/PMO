# Imagen de QSG PMO: ERPNext v16 oficial + la app qsg_pmo de este repositorio.
# Se construye desde la raíz del repositorio (lo hace docker-compose.yml).
ARG ERPNEXT_VERSION=v16.53.0
FROM frappe/erpnext:${ERPNEXT_VERSION}

USER frappe
WORKDIR /home/frappe/frappe-bench

COPY --chown=frappe:root . apps/qsg_pmo

# La app es Python puro y no tiene archivos que compilar ni dependencias extra:
# se registra en el entorno de Python con un .pth (equivale a "pip install -e", sin internet)
# y su carpeta public/ se publica como /assets/qsg_pmo.
RUN SITE=$(./env/bin/python -c "import sysconfig; print(sysconfig.get_paths()['purelib'])") \
    && echo /home/frappe/frappe-bench/apps/qsg_pmo > "$SITE/qsg_pmo.pth" \
    && ./env/bin/python -c "import qsg_pmo; print('qsg_pmo', qsg_pmo.__version__)" \
    && ln -sfn /home/frappe/frappe-bench/apps/qsg_pmo/qsg_pmo/public assets/qsg_pmo \
    && (grep -qx qsg_pmo sites/apps.txt || echo qsg_pmo >> sites/apps.txt)
