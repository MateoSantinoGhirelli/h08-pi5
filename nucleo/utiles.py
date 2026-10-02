# -*- coding: utf-8 -*-
"""
utiles.py - reloj, azar reproducible y matemática común
========================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

Herramientas que usa todo el núcleo: el reloj monotónico, el generador de
números pseudoaleatorios, el filtro de primer orden, el limitador de
velocidad y la interpolación de las tablas de calibración. Ningún otro
módulo las vuelve a implementar.
"""

import time as _t

# ---------------------------------------------------------------------------
# RELOJ MONOTÓNICO EN MILISEGUNDOS
# ---------------------------------------------------------------------------
# Se usa un reloj monotónico y no la hora del sistema: si se corrige la hora
# de la Raspberry Pi mientras el tablero funciona, la simulación no se altera.
# ---------------------------------------------------------------------------
_T0 = _t.monotonic()


def ticks_ms():
    """Milisegundos transcurridos desde que arrancó el programa."""
    return int((_t.monotonic() - _T0) * 1000)


def ticks_diff(a, b):
    """Diferencia entre dos lecturas de ticks_ms(), en milisegundos."""
    return a - b


# ---------------------------------------------------------------------------
# GENERADOR PSEUDOALEATORIO REPRODUCIBLE (congruencial lineal de 32 bits)
# ---------------------------------------------------------------------------
# Con la misma semilla se obtiene siempre el mismo vuelo, con las mismas
# vibraciones de aguja. Así una demostración que salió bien en la prueba sale
# igual delante del curso, y las pruebas automáticas pueden comparar
# resultados exactos.
# ---------------------------------------------------------------------------
class Aleatorio:
    __slots__ = ("_s",)

    def __init__(self, semilla=20250819):
        self._s = semilla & 0xFFFFFFFF

    def sembrar(self, semilla):
        self._s = semilla & 0xFFFFFFFF

    def _siguiente(self):
        # Constantes de Numerical Recipes
        self._s = (1664525 * self._s + 1013904223) & 0xFFFFFFFF
        return self._s

    def uniforme(self):
        """Flotante en [0,0 ; 1,0)."""
        return self._siguiente() / 4294967296.0

    def simetrico(self):
        """Flotante en [-1,0 ; +1,0)."""
        return self.uniforme() * 2.0 - 1.0


RNG = Aleatorio()


# ---------------------------------------------------------------------------
# MATEMÁTICA DE USO GENERAL
# ---------------------------------------------------------------------------
def limitar(x, minimo, maximo):
    """Satura x al intervalo [mínimo, máximo]."""
    if x < minimo:
        return minimo
    if x > maximo:
        return maximo
    return x


def mezclar(a, b, k):
    """Interpolación lineal: k=0 devuelve a, k=1 devuelve b."""
    return a + (b - a) * k


def aproximar(actual, objetivo, dt, tau):
    """
    Filtro pasabajos de primer orden (retardo exponencial).

    Es la base de toda la dinámica del simulador: cada magnitud física
    «persigue» a su objetivo con una constante de tiempo tau, en segundos.

        tau chico  → responde rápido (presión de aceite, régimen del motor)
        tau grande → responde lento  (temperatura de culata, de aceite)

    Se usa la forma discreta x += (obj - x) · dt/(tau+dt), que es estable
    aunque el paso de tiempo se agrande.
    """
    if tau <= 0.0:
        return objetivo
    k = dt / (tau + dt)
    return actual + (objetivo - actual) * k


def rampa(actual, objetivo, dt, velocidad):
    """
    Limitador de velocidad de cambio, en unidades por segundo.

    A diferencia de aproximar(), avanza a velocidad constante. Protege a los
    servos de los saltos bruscos: un servo al que se le ordena cruzar la
    esfera de golpe castiga el engranaje y puede desprender la aguja.
    """
    paso = velocidad * dt
    d = objetivo - actual
    if d > paso:
        return actual + paso
    if d < -paso:
        return actual - paso
    return objetivo


def interpolar_tabla(x, tabla):
    """
    Interpolación lineal a trozos sobre una tabla [(x0,y0), (x1,y1), …].

    Es el corazón de la calibración de los instrumentos. Las esferas
    aeronáuticas no son lineales:
      • el velocímetro comprime el extremo inferior, porque la presión
        dinámica crece con el cuadrado de la velocidad;
      • los aforadores de combustible siguen la forma del tanque;
      • los manómetros de tubo Bourdon tienen su propia no linealidad.

    En vez de modelar cada mecanismo, se mide dónde cae cada marca de la
    esfera y se carga la tabla. Recalibrar un instrumento es corregir su
    tabla en configuracion.py, sin tocar la lógica.

    La tabla debe estar ordenada de menor a mayor en x.
    """
    n = len(tabla)
    if n == 0:
        return 0.0
    if x <= tabla[0][0]:
        return tabla[0][1]
    if x >= tabla[n - 1][0]:
        return tabla[n - 1][1]
    # Búsqueda lineal: las tablas tienen entre 3 y 13 puntos.
    i = 1
    while i < n and tabla[i][0] < x:
        i += 1
    x0, y0 = tabla[i - 1]
    x1, y1 = tabla[i]
    dx = x1 - x0
    if dx == 0.0:
        return y1
    return y0 + (y1 - y0) * (x - x0) / dx
