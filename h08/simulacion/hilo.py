# -*- coding: utf-8 -*-
"""
h08/simulacion/hilo.py - la simulación en su propio hilo
====================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

En la Raspberry conviven tres trabajos con tiempos distintos:

  * la simulación y las placas PCA9685, a 20 Hz y sin saltos (este hilo);
  * los motores paso a paso, cada milisegundo (su propio hilo, paso_a_paso.py);
  * el servidor web, que atiende pedidos cuando llegan (hilo principal).

El servidor se comunica con este hilo de dos maneras solamente:

  * MANDA órdenes por una cola (queue.Queue ya es segura entre hilos);
  * LEE la última foto del estado, que se reemplaza entera de una vez (una
    asignación de referencia es atómica en Python).

Si una vuelta del lazo falla (un error de bus, un error de programa), el
error se cuenta y se informa, y el lazo sigue: el tablero no se queda
congelado delante del público.
"""

import logging
import queue
import threading
import time

from h08.simulacion.simulador import Simulador
from h08.config import LAZO

log = logging.getLogger(__name__)


class HiloSimulacion(threading.Thread):

    def __init__(self, actuadores, semilla=None):
        threading.Thread.__init__(self, daemon=True, name="simulacion")
        self.sim = Simulador(actuadores, semilla=semilla)
        self.actuadores = actuadores
        self.cola = queue.Queue()
        self.foto = self.sim.estado()
        self.catalogo = self.sim.catalogo_estatico()
        self.errores = 0
        self.ultimo_error = ""
        self._parar = threading.Event()
        self._periodo_foto = 1.0 / LAZO["hz_telemetria"]

    # -- para el servidor web ----------------------------------------------
    def ordenar(self, accion, valor=None):
        self.cola.put((accion, valor))

    def detener(self):
        self._parar.set()

    # -- hilo ----------------------------------------------------------------
    def run(self):
        sim = self.sim
        sim.modo_normal()
        t_foto = time.monotonic()

        while not self._parar.is_set():
            try:
                while True:
                    try:
                        accion, valor = self.cola.get_nowait()
                    except queue.Empty:
                        break
                    self._ejecutar(accion, valor)

                # El simulador calcula cuántos pasos fijos de 50 ms le
                # corresponden al tiempo real transcurrido y escribe las placas.
                sim.servicio()

                ahora = time.monotonic()
                if ahora - t_foto >= self._periodo_foto:
                    t_foto = ahora
                    foto = sim.estado()
                    foto["hardware"] = self._salud()
                    self.foto = foto
            except Exception as e:
                self.errores += 1
                self.ultimo_error = "%s: %s" % (type(e).__name__, e)
                if self.errores <= 3 or self.errores % 100 == 0:
                    log.exception("error %d en el lazo de simulación; el tablero sigue",
                                  self.errores)
                time.sleep(0.2)
            time.sleep(0.005)

        # Apagado en orden: luces apagadas, servos sin pulso, motores a cero.
        try:
            sim.mapa.apagar()
        except Exception:
            pass
        try:
            self.actuadores.cerrar()
        except Exception:
            log.exception("no se pudieron dejar las salidas en reposo al apagar")

    def _salud(self):
        d = {"errores_programa": self.errores, "ultimo_error": self.ultimo_error}
        salud = getattr(self.actuadores, "salud", None)
        if salud:
            d.update(salud())
        return d

    # -- órdenes -------------------------------------------------------------
    def _ejecutar(self, accion, valor):
        sim = self.sim
        if accion == "modo_normal":
            sim.modo_normal(desde_fase=valor)
        elif accion == "modo_escenario":
            sim.modo_escenario(valor)
        elif accion == "modo_falla":
            sim.modo_falla(valor)
        elif accion == "detener":
            sim.detener()
        elif accion == "activar_falla":
            sim.activar_falla(valor)
        elif accion == "quitar_falla":
            sim.quitar_falla(valor)
        elif accion == "pausa":
            sim.pausado = bool(valor)
        elif accion == "velocidad":
            try:
                sim.velocidad = max(0.25, min(float(valor), 8.0))
            except (TypeError, ValueError):
                pass
        elif accion == "prueba_luces":
            sim.prueba_luces(bool(valor))
        elif accion == "piloto_reactivo":
            sim.fijar_piloto_reactivo(bool(valor))
        elif accion == "ciclar":
            sim.ciclar = bool(valor)
