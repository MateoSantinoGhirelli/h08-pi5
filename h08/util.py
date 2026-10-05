# -*- coding: utf-8 -*-
"""Reloj, azar reproducible, filtros y la interpolación de las tablas de calibración."""

import time as _t

# Monotónico y no la hora del sistema: si se corrige la hora de la Pi con el
# tablero en marcha, la simulación no salta.
_T0 = _t.monotonic()


def ticks_ms():
    """Milisegundos desde que arrancó el programa."""
    return int((_t.monotonic() - _T0) * 1000)


def ticks_diff(a, b):
    return a - b


class Aleatorio:
    """Congruencial lineal de 32 bits, reproducible.

    Con la misma semilla sale el mismo vuelo con las mismas vibraciones de aguja:
    una demostración que anduvo en la prueba sale igual delante del curso, y las
    pruebas automáticas comparan resultados exactos.
    """
    __slots__ = ("_s",)

    def __init__(self, semilla=20250819):
        self._s = semilla & 0xFFFFFFFF

    def sembrar(self, semilla):
        self._s = semilla & 0xFFFFFFFF

    def _siguiente(self):
        # constantes de Numerical Recipes
        self._s = (1664525 * self._s + 1013904223) & 0xFFFFFFFF
        return self._s

    def uniforme(self):
        """Flotante en [0,0 ; 1,0)."""
        return self._siguiente() / 4294967296.0

    def simetrico(self):
        """Flotante en [-1,0 ; +1,0)."""
        return self.uniforme() * 2.0 - 1.0


RNG = Aleatorio()


def limitar(x, minimo, maximo):
    if x < minimo:
        return minimo
    if x > maximo:
        return maximo
    return x


def mezclar(a, b, k):
    """Interpolación lineal: k=0 da a, k=1 da b."""
    return a + (b - a) * k


def aproximar(actual, objetivo, dt, tau):
    """Filtro de primer orden: actual persigue a objetivo con constante de tiempo tau (s).

    Es la base de la dinámica del simulador: tau chico para la presión de aceite o
    el régimen, tau grande para las temperaturas. La forma x += (obj - x)·dt/(tau+dt)
    sigue siendo estable aunque el paso de tiempo se agrande.
    """
    if tau <= 0.0:
        return objetivo
    k = dt / (tau + dt)
    return actual + (objetivo - actual) * k


def rampa(actual, objetivo, dt, velocidad):
    """Avanza hacia objetivo a velocidad constante (unidades por segundo).

    Un servo al que se le ordena cruzar la esfera de golpe castiga el engranaje y
    puede desprender la aguja.
    """
    paso = velocidad * dt
    d = objetivo - actual
    if d > paso:
        return actual + paso
    if d < -paso:
        return actual - paso
    return objetivo


def interpolar_tabla(x, tabla):
    """Interpolación lineal a trozos sobre [(x0, y0), (x1, y1), ...], ordenada en x.

    Las esferas aeronáuticas no son lineales (el velocímetro comprime el extremo
    bajo porque la presión dinámica va con V²; los aforadores siguen la forma del
    tanque): en vez de modelar cada mecanismo, la tabla dice dónde cae cada marca.
    Las carátulas impresas están dibujadas con estas tablas, así que una aguja que
    no cae en su marca se ajusta o se calibra el servo; la tabla no se toca.
    """
    n = len(tabla)
    if n == 0:
        return 0.0
    if x <= tabla[0][0]:
        return tabla[0][1]
    if x >= tabla[n - 1][0]:
        return tabla[n - 1][1]
    # búsqueda lineal: las tablas tienen entre 3 y 13 puntos
    i = 1
    while i < n and tabla[i][0] < x:
        i += 1
    x0, y0 = tabla[i - 1]
    x1, y1 = tabla[i]
    dx = x1 - x0
    if dx == 0.0:
        return y1
    return y0 + (y1 - y0) * (x - x0) / dx
