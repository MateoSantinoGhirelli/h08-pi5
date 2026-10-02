# -*- coding: utf-8 -*-
"""Dónde están los archivos del tablero; el resto del programa no arma rutas propias.

Lo que escribe cada tablero (clave, calibración, posición del motor, informes) va
en datos/, fuera del código: una actualización puede reemplazar h08/ entero.
H08_DATOS cambia esa carpeta (las pruebas usan una temporal) y apaga la mudanza.
"""
import logging
import os
import shutil

log = logging.getLogger(__name__)

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

VERSION = os.path.join(RAIZ, "VERSION.txt")
ESTATICOS = os.path.join(RAIZ, "h08", "web", "static")
PUNTO_DE_ACCESO = os.path.join(RAIZ, "deploy", "punto_de_acceso.sh")

_DATOS_APARTE = os.environ.get("H08_DATOS")
DATOS = _DATOS_APARTE or os.path.join(RAIZ, "datos")
CLAVE = os.path.join(DATOS, "secreto_admin.json")
CALIBRACION = os.path.join(DATOS, "calibracion_servos.json")
MOTORES = os.path.join(DATOS, "posicion_motores.json")
# H08_INFORMES la usan las pruebas automáticas para no ensuciar la carpeta.
INFORMES = os.environ.get("H08_INFORMES") or os.path.join(DATOS, "informes")

# Hasta la versión de octubre de 2026 los datos estaban acá. Con H08_DATOS no hay
# mudanza: esa carpeta está aislada y no puede llevarse los datos reales.
VIEJA = None if _DATOS_APARTE else os.path.join(RAIZ, "raspberry_pi5")
PRIVADOS = ("secreto_admin.json", "calibracion_servos.json", "posicion_motores.json")


def datos_viejos(vieja=VIEJA):
    """Lo que todavía queda en raspberry_pi5/ (vacío si ya se mudó todo)."""
    if not vieja:
        return []
    return [n for n in PRIVADOS + ("informes",) if os.path.exists(os.path.join(vieja, n))]


def migrar_datos_viejos(vieja=VIEJA, nueva=DATOS, avisar=None):
    """Pasa los datos de raspberry_pi5/ a datos/ sin pisar nada; devuelve los conflictos.

    Crea la carpeta nueva si falta. Lo que ya existe en las dos se deja como está y
    se avisa: decide una persona, no el programa. Correrla otra vez no hace nada.
    Cada movimiento queda en el registro (los conflictos, como AVISO); con avisar,
    los mensajes van ahí en cambio (lo usan las pruebas).
    """
    os.makedirs(nueva, exist_ok=True)
    if not vieja or not os.path.isdir(vieja):
        return []
    conflictos = []

    def mover(origen, destino):
        if os.path.exists(destino):
            conflictos.append(origen)
            (avisar or log.warning)("[datos] %s quedó sin mover: ya existe %s"
                                    % (origen, destino))
            return
        shutil.move(origen, destino)
        (avisar or log.info)("[datos] movido %s -> %s" % (origen, destino))

    for nombre in PRIVADOS:
        origen = os.path.join(vieja, nombre)
        if os.path.isfile(origen):
            mover(origen, os.path.join(nueva, nombre))

    informes_viejos = os.path.join(vieja, "informes")
    if os.path.isdir(informes_viejos):
        destino = os.path.join(nueva, "informes")
        if not os.path.exists(destino):
            mover(informes_viejos, destino)
        else:
            for f in sorted(os.listdir(informes_viejos)):
                mover(os.path.join(informes_viejos, f), os.path.join(destino, f))
            _borrar_si_vacia(informes_viejos)

    _borrar_si_vacia(vieja)
    return conflictos


def _borrar_si_vacia(carpeta):
    try:
        os.rmdir(carpeta)
    except OSError:
        pass
