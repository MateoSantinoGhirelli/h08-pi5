# -*- coding: utf-8 -*-
"""Salidas sin hardware: guardan el último valor de cada canal y cuentan las escrituras.

Con ellas el tablero corre entero en una computadora sin placas, se puede leer el
ángulo de cada aguja antes de conectar un servo y las pruebas comparan valores.
"""

import logging

from h08.hardware.base import ActuadoresBase

log = logging.getLogger(__name__)


class ActuadoresSimulados(ActuadoresBase):

    def __init__(self, verboso=False):
        self.valores = {}
        self.verboso = verboso
        self.n_servo = 0
        self.n_led = 0
        self.n_motor = 0
        self.n_refresco = 0

    def _clave(self, destino):
        return "%s:%d" % (destino[0], destino[1])

    def escribir_servo(self, destino, angulo_deg):
        self.valores[self._clave(destino)] = round(angulo_deg, 2)
        self.n_servo += 1
        if self.verboso:
            log.info("SERVO %s -> %.1f grados", self._clave(destino), angulo_deg)

    def escribir_motor(self, destino, angulo_deg):
        self.valores[self._clave(destino)] = round(angulo_deg, 2)
        self.n_motor += 1

    def escribir_led(self, destino, encendido):
        self.valores[self._clave(destino)] = 1 if encendido else 0
        self.n_led += 1
        if self.verboso:
            log.info("LUZ   %s -> %s", self._clave(destino),
                     "encendida" if encendido else "apagada")

    def refrescar(self):
        self.n_refresco += 1
        return 0

    def descripcion(self):
        return "simulada, sin hardware"
