"""Inteligencia operativa de QSG PMO.

Funciones puras (sin base de datos) para que se puedan probar solas y cambiar de proveedor:

* ``territorio``: los 78 municipios de Puerto Rico, terreno, islas y zonas vecinas.
* ``rutas``: tiempo de viaje con terreno, ferry y tiempos reales de OSRM si hay.
* ``optimizacion``: mejora el plan del motor por reglas con búsqueda local.
* ``tracking``: limpia el GPS de las cuadrillas, detecta inactividad, retrasos y velocidad real.
* ``zonas``: rendimiento por zona, afinidad cuadrilla-zona, demanda contra capacidad y la
  mejor cuadrilla para una orden nueva.
* ``materiales``: qué recoger en bodega (neto de lo que ya hay en el camión) y qué devolver.
* ``pendientes``: lo que le falta a cada orden para no dejar trabajo a medias.
* ``clima``: alertas del Servicio Nacional de Meteorología convertidas en zonas afectadas.
* ``ia``: modelo de lenguaje (Claude o uno local con Ollama) con respaldo por reglas.
"""
