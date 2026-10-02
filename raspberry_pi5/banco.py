# -*- coding: utf-8 -*-
"""
banco.py - lo que comparten las herramientas de prueba de la Raspberry
======================================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

Lo usan probar_canal.py, calibrar_servo.py y probar_motor.py:

  * rutas de los archivos que guarda el tablero;
  * aviso si el servicio del tablero está andando (dos programas escribiendo
    las mismas placas a la vez se pisan);
  * traducir lo que escribe el usuario ("PCA0 3" o "AIRSPEED") a un canal.
"""

import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "nucleo"))

from configuracion import TABLERO, TABLERO_POR_ID, PLACAS   # noqa: E402

ARCHIVO_CALIBRACION = os.path.join(AQUI, "calibracion_servos.json")
ARCHIVO_MOTORES = os.path.join(AQUI, "posicion_motores.json")
SERVICIO = "tablero-h08"


def servicio_andando():
    try:
        r = subprocess.run(["systemctl", "is-active", "--quiet", SERVICIO],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=5)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def exigir_servicio_detenido():
    if servicio_andando():
        print("\n  El servicio del tablero está andando y usa las mismas placas.")
        print("  Primero:   sudo systemctl stop %s" % SERVICIO)
        print("  Al final:  sudo systemctl start %s\n" % SERVICIO)
        sys.exit(1)


def abrir_placas():
    """ActuadoresPCA9685 con la calibración de cada servo cargada."""
    from actuadores_pca9685 import ActuadoresPCA9685
    try:
        return ActuadoresPCA9685(calibracion=ARCHIVO_CALIBRACION)
    except RuntimeError as e:
        print("\n  %s\n" % e)
        sys.exit(1)


def que_hay_en(destino):
    """El instrumento conectado a ese canal, o None."""
    for it in TABLERO:
        if tuple(it.get("canal") or ()) == tuple(destino):
            return it
    return None


def resolver(palabras):
    """["PCA0", "3"] o ["AIRSPEED"]  ->  (destino, instrumento o None)."""
    if not palabras:
        return None, None
    if palabras[0].upper() in PLACAS:
        if len(palabras) < 2 or not palabras[1].isdigit() \
                or not 0 <= int(palabras[1]) <= 15:
            sys.exit("  Falta el canal (0 a 15):  %s 3" % palabras[0].upper())
        destino = (palabras[0].upper(), int(palabras[1]))
        return destino, que_hay_en(destino)
    it = TABLERO_POR_ID.get(palabras[0].upper())
    if it is None or not it.get("canal"):
        sys.exit("  No existe '%s'. Ver la lista con --listar" % palabras[0])
    return tuple(it["canal"]), it


def nombre_de(destino):
    it = que_hay_en(destino)
    return "%s:%d%s" % (destino[0], destino[1],
                        "  (%s)" % it["id"] if it else "  (libre)")
