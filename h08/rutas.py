# -*- coding: utf-8 -*-
"""Dónde están los archivos del tablero; el resto del programa no arma rutas propias.

Los datos de cada tablero (clave, calibración, posición del motor, informes) siguen
en raspberry_pi5/, que es donde los busca la versión anterior.
"""
import os

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VERSION = os.path.join(RAIZ, "VERSION.txt")
ESTATICOS = os.path.join(RAIZ, "h08", "web", "static")
PUNTO_DE_ACCESO = os.path.join(RAIZ, "deploy", "punto_de_acceso.sh")

DATOS = os.path.join(RAIZ, "raspberry_pi5")
CLAVE = os.path.join(DATOS, "secreto_admin.json")
CALIBRACION = os.path.join(DATOS, "calibracion_servos.json")
MOTORES = os.path.join(DATOS, "posicion_motores.json")
# H08_INFORMES la usan las pruebas automáticas para no ensuciar la carpeta.
INFORMES = os.environ.get("H08_INFORMES") or os.path.join(DATOS, "informes")
