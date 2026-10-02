# -*- coding: utf-8 -*-
"""
actuadores_base.py - interfaz de la capa de salida (hardware)
==============================================================

El núcleo de simulación no sabe qué hay debajo: sólo conoce estos métodos.
Por eso el mismo código corre en una computadora sin hardware
(actuadores_simulados.py) y en la Raspberry Pi 5 moviendo los servos de
verdad (actuadores_pca9685.py). Cambiar de placa de salida es escribir otra
clase que implemente esta interfaz, sin tocar el modelo de vuelo.

Los destinos son tuplas (placa, canal): ("PCA0", 7), ("PCA1", 8) o
("MOTOR", 1) para el motor paso a paso de la brújula.
"""


class ActuadoresBase:

    # -- salidas ------------------------------------------------------------
    def escribir_servo(self, destino, angulo_deg):
        """angulo_deg en [0, 180]: el recorrido del servo."""
        raise NotImplementedError

    def escribir_motor(self, destino, angulo_deg):
        """angulo_deg en grados de aguja, sin tope.

        El 28BYJ-48 da vueltas enteras en los dos sentidos: 370 grados es lo
        mismo que 10. Quien recibe la orden elige el camino más corto.
        """
        raise NotImplementedError

    def escribir_led(self, destino, encendido):
        raise NotImplementedError

    # -- ciclo --------------------------------------------------------------
    def refrescar(self):
        """Vuelca los datos pendientes al hardware. Puede no hacer nada."""
        pass

    def cerrar(self):
        pass

    # -- información --------------------------------------------------------
    def descripcion(self):
        return self.__class__.__name__
