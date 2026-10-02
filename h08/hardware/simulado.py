# -*- coding: utf-8 -*-
"""
h08/hardware/simulado.py - salida sin hardware
==============================================

No mueve nada: guarda el último valor escrito en cada canal y cuenta las
escrituras. Sirve para:

  1. Correr el tablero completo en una computadora común, sin placas.
  2. Verificar la calibración: se puede leer el ángulo de cada aguja antes
     de conectar un solo servo.
  3. Probar el programa: las pruebas automáticas comparan estos valores.
"""

from h08.hardware.base import ActuadoresBase


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
            print("SERVO %s -> %.1f grados" % (self._clave(destino), angulo_deg))

    def escribir_motor(self, destino, angulo_deg):
        self.valores[self._clave(destino)] = round(angulo_deg, 2)
        self.n_motor += 1

    def escribir_led(self, destino, encendido):
        self.valores[self._clave(destino)] = 1 if encendido else 0
        self.n_led += 1
        if self.verboso:
            print("LUZ   %s -> %s" % (self._clave(destino),
                                      "encendida" if encendido else "apagada"))

    def refrescar(self):
        self.n_refresco += 1
        return 0

    def descripcion(self):
        return "simulada, sin hardware"
