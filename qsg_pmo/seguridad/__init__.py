# Copyright (c) 2026, QSG and contributors
# For license information, please see license.txt
"""Módulo de seguridad de QSG PMO.

Piezas (todas activas al instalar o migrar):

* ``eventos``: registro inalterable de eventos de seguridad (QSG Evento Seguridad).
* ``limites``: límite de peticiones por usuario y método; al excederse responde 429 y lo registra.
* ``validacion``: limpieza de texto, coordenadas, firma, fotos e IP permitidas para la integración.
* ``archivos``: solo imágenes reales (por contenido, no por extensión) y de tamaño acotado en
  los documentos de QSG.
* ``cabeceras``: cabeceras HTTP de seguridad (CSP en /campo, anti-clickjacking, nosniff, HSTS).
* ``endurecimiento``: bloqueo por intentos fallidos, política de contraseñas, sesiones cortas,
  sin auto-registro, sin trazas de error y doble factor opcional para gerencia.
* ``verificar``: autodiagnóstico del estado de seguridad del sitio.
* ``auditoria``: datos de prueba para la simulación y las pruebas de ataque.
"""
