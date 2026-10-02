# -*- coding: utf-8 -*-
"""Interfaz común de las salidas: servos, luces y motores.

Hay dos implementaciones: pca9685 (la Pi) y simulado (PC y pruebas); el núcleo
de simulación sólo conoce estos métodos. Los destinos son tuplas (placa, canal),
p. ej. ("PCA0", 7) o ("MOTOR", 1) para el paso a paso de la brújula.
"""


class ActuadoresBase:

    def escribir_servo(self, destino, angulo_deg):
        """angulo_deg en [0, 180]: el recorrido del servo."""
        raise NotImplementedError

    def escribir_motor(self, destino, angulo_deg):
        """angulo_deg en grados de aguja, sin tope.

        El 28BYJ-48 da vueltas enteras en los dos sentidos: 370 grados es lo
        mismo que 10, y quien recibe la orden elige el camino más corto.
        """
        raise NotImplementedError

    def escribir_led(self, destino, encendido):
        raise NotImplementedError

    def refrescar(self):
        """Vuelca lo pendiente al hardware (puede no hacer nada)."""
        pass

    def cerrar(self):
        pass

    def descripcion(self):
        return self.__class__.__name__
