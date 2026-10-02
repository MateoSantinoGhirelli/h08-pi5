# -*- coding: utf-8 -*-
"""Pruebas automáticas del tablero, sin hardware: python3 -m pruebas.

Al cargarse arma una carpeta de datos temporal (H08_DATOS) antes de que alguna
prueba importe h08.rutas: así ninguna toca la clave, la calibración ni la
posición del motor reales, ni dispara la mudanza desde raspberry_pi5/.
"""
import atexit
import os
import shutil
import sys
import tempfile

if not os.environ.get("H08_DATOS"):
    if "h08.rutas" in sys.modules:
        raise RuntimeError("h08.rutas se importó antes que las pruebas: sus rutas "
                           "apuntarían a los datos reales del tablero")
    _DATOS = tempfile.mkdtemp(prefix="h08_datos_")
    os.environ["H08_DATOS"] = _DATOS
    atexit.register(shutil.rmtree, _DATOS, True)
