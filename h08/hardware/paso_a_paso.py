# -*- coding: utf-8 -*-
"""La aguja de la brújula: un 28BYJ-48 de giro continuo, en su propio hilo.

Da vueltas enteras en los dos sentidos, así que no desanda la vuelta para pasar por
el norte. Va en medio paso, con perfil trapezoidal para no perder pasos (y por eso
no necesita sensor de posición), toma siempre el camino más corto, suelta las
bobinas en reposo y guarda dónde quedó la aguja. Por qué cada cosa: docs/hardware.md.
"""

import json
import math
import os
import threading
import time

from h08.config import MOTOR_CFG, MOTORES

SECUENCIA = (0b0001, 0b0011, 0b0010, 0b0110,
             0b0100, 0b1100, 0b1000, 0b1001)


def _envolver180(d):
    """Diferencia angular llevada a [-180, 180)."""
    return (d + 180.0) % 360.0 - 180.0


class MotorContinuo:
    """Un 28BYJ-48. 'escribir(pines, bits)' pone los 4 pines de la plaquita."""

    def __init__(self, escribir, pines, sentido=1, grados_iniciales=0.0,
                 fase_inicial=0):
        self.escribir = escribir
        self.pines = pines
        self.sentido = 1 if sentido >= 0 else -1
        self.ppv = float(MOTOR_CFG["pasos_por_vuelta"])
        self.v_max = float(MOTOR_CFG["vel_max_pps"])
        self.v_min = float(MOTOR_CFG["vel_arranque_pps"])
        self.acel = float(MOTOR_CFG["aceleracion"])
        self.t_soltar = float(MOTOR_CFG["soltar_tras_s"])
        # posición en pasos y objetivo en grados, los dos "desenrollados": pueden
        # pasar de 360 o ser negativos, y de ahí sale el camino corto
        g = grados_iniciales % 360.0
        self.pos = int(round(g * self.ppv / 360.0))
        self.obj_grados = g
        self.estado = int(fase_inicial) % 8     # fase de la secuencia
        self.vel = 0.0          # pasos por segundo, siempre >= 0
        self.dir = 0            # +1, -1 o 0 (quieto)
        self.proximo = 0.0      # instante del paso siguiente
        self.energizado = False
        self.quieto_desde = time.monotonic()

    # Las órdenes las llama otro hilo: son asignaciones simples, sin candado.
    def ir_a_grados(self, grados):
        """Objetivo en la vuelta más cercana al objetivo anterior."""
        actual = self.obj_grados
        self.obj_grados = actual + _envolver180(grados - actual)

    def grados(self):
        """Ángulo de la aguja, 0 a 360."""
        return (self.pos * 360.0 / self.ppv) % 360.0

    def objetivo_pasos(self):
        return int(round(self.obj_grados * self.ppv / 360.0))

    def declarar_cero(self):
        """La posición actual pasa a ser el cero. No mueve nada."""
        self.pos = 0
        self.obj_grados = 0.0

    def servicio(self, ahora):
        """Da el paso que toque; devuelve cuándo volver a llamarlo (None si está suelto).

        El paso siguiente se programa a 1/velocidad del actual: si el hilo se atrasa,
        el motor va más lento, nunca más rápido de lo que puede seguir sin perder pasos.
        """
        falta = self.objetivo_pasos() - self.pos
        if falta == 0 and self.vel <= self.v_min:
            self.vel = 0.0
            self.dir = 0
            if not self.energizado:
                return None
            soltar_en = self.quieto_desde + self.t_soltar
            if ahora >= soltar_en:
                self.soltar()
                return None
            return soltar_en

        if not self.energizado:
            # re-energiza la fase donde quedó y le da 5 ms al rotor para enganchar
            self.escribir(self.pines, SECUENCIA[self.estado])
            self.energizado = True
            self.proximo = ahora + 0.005
            return self.proximo
        if ahora < self.proximo:
            return self.proximo

        # perfil trapezoidal paso a paso: v² cambia 2·a en cada uno
        if falta == 0:
            deseada = -self.dir          # llegó con velocidad: frena pasándose
        else:
            deseada = 1 if falta > 0 else -1
        a2 = 2.0 * self.acel
        if self.dir == 0:
            self.dir = deseada
            self.vel = self.v_min
        elif self.dir != deseada:
            self.vel = math.sqrt(max(self.vel * self.vel - a2, 0.0))
            if self.vel <= self.v_min:
                self.dir = deseada
                self.vel = self.v_min
        elif abs(falta) <= self.vel * self.vel / a2:
            self.vel = max(self.v_min, math.sqrt(max(self.vel * self.vel - a2, 0.0)))
        else:
            self.vel = min(self.v_max, math.sqrt(self.vel * self.vel + a2))

        self.pos += self.dir
        self.estado = (self.estado + self.dir * self.sentido) % 8
        self.escribir(self.pines, SECUENCIA[self.estado])
        self.quieto_desde = ahora
        self.proximo = ahora + 1.0 / self.vel
        return self.proximo

    def en_objetivo(self):
        return self.objetivo_pasos() == self.pos and self.dir == 0

    def estacionar(self):
        """Pide el cero más cercano (sin desandar vueltas enteras)."""
        self.obj_grados = round(self.obj_grados / 360.0) * 360.0

    def soltar(self):
        self.escribir(self.pines, 0)
        self.energizado = False


class EscritorGPIO:
    """Pone los 4 pines IN1..IN4 de una plaquita; sólo escribe los que cambian.

    Con gpiozero, que en la Pi 5 trabaja sobre lgpio: RPi.GPIO no anda con el RP1.
    """

    def __init__(self):
        try:
            from gpiozero import DigitalOutputDevice
        except ImportError:
            raise RuntimeError("Falta gpiozero:  sudo apt install -y "
                               "python3-gpiozero python3-lgpio")
        self._crear = DigitalOutputDevice
        self.salidas = {}
        self.ultimo = {}

    def __call__(self, pines, bits):
        previo = self.ultimo.get(pines)
        for i, gp in enumerate(pines):
            b = (bits >> i) & 1
            if previo is not None and ((previo >> i) & 1) == b:
                continue
            s = self.salidas.get(gp)
            if s is None:
                s = self._crear(gp, initial_value=False)
                self.salidas[gp] = s
            s.value = b
        self.ultimo[pines] = bits

    def cerrar(self):
        for s in self.salidas.values():
            try:
                s.off()
                s.close()
            except Exception:
                pass
        self.salidas = {}


class GestorMotores(threading.Thread):
    """Recibe los ángulos del mapa del tablero y mueve los motores en su propio hilo.

    El destino de cada instrumento es ("MOTOR", n), con n la clave de MOTORES.
    """

    PERIODO_QUIETO_S = 0.05      # vuelta del hilo con los motores sueltos
    LIMITE_CIERRE_S = 8.0        # tiempo para llevar las agujas a cero al cerrar
    GUARDAR_CADA_S = 30.0

    def __init__(self, escritor, archivo_posicion=None, motores=MOTORES):
        threading.Thread.__init__(self, daemon=True, name="motores")
        self.escritor = escritor
        self.archivo = archivo_posicion
        guardado = self._leer_posiciones()
        self.motores = {}
        for n, m in motores.items():
            grados, fase = guardado.get(str(n), (0.0, 0))
            self.motores[n] = MotorContinuo(escritor, tuple(m["pines"]),
                                            m.get("sentido", 1), grados, fase)
        # Todas las entradas en bajo desde el arranque: si un GPIO levanta con su
        # pull-up, sin esto quedaría una bobina encendida hasta el primer movimiento.
        for m in self.motores.values():
            m.soltar()
        self._parar = threading.Event()
        self._t_guardado = 0.0
        self._guardado = self._posiciones()

    def escribir_motor(self, destino, angulo_deg):
        m = self.motores.get(destino[1])
        if m is not None:
            m.ir_a_grados(angulo_deg)

    def descripcion(self):
        return "%d motores paso a paso (GPIO %s)" % (
            len(self.motores),
            " / ".join(",".join(str(p) for p in m.pines)
                       for m in self.motores.values()))

    def run(self):
        while not self._parar.is_set():
            ahora = time.monotonic()
            proximos = [m.servicio(ahora) for m in self.motores.values()]
            pendientes = [p for p in proximos if p is not None]
            if pendientes:
                espera = min(pendientes) - time.monotonic()
            else:
                espera = self.PERIODO_QUIETO_S
                if ahora - self._t_guardado >= self.GUARDAR_CADA_S:
                    self._t_guardado = ahora
                    self._guardar()
            if espera > 0:
                if pendientes and espera < self.PERIODO_QUIETO_S:
                    # Entre paso y paso (~1 ms), time.sleep y no Event.wait: en Windows
                    # wait no baja de ~15 ms y el motor simulado iría 15 veces más lento.
                    time.sleep(espera)
                else:
                    self._parar.wait(min(espera, self.PERIODO_QUIETO_S))

    def esperar_quietos(self, limite_s=10.0):
        fin = time.monotonic() + limite_s
        while time.monotonic() < fin:
            if all(m.en_objetivo() for m in self.motores.values()):
                return True
            time.sleep(0.02)
        return False

    def detener(self):
        """Para el hilo sin mover las agujas, suelta las bobinas y guarda."""
        self._parar.set()
        if self.is_alive():
            self.join(1.0)
        for m in self.motores.values():
            m.soltar()
        self._guardar(forzar=True)

    def cerrar(self):
        """Lleva las agujas a su cero, guarda la posición y suelta todo."""
        if self.is_alive():
            for m in self.motores.values():
                m.estacionar()
            self.esperar_quietos(self.LIMITE_CIERRE_S)
            self._parar.set()
            self.join(1.0)
        for m in self.motores.values():
            m.soltar()
        self._guardar(forzar=True)
        cerrar = getattr(self.escritor, "cerrar", None)
        if cerrar:
            cerrar()

    def _posiciones(self):
        """{"0": [grados de la aguja, fase de la secuencia], ...}"""
        return dict((str(n), [round(m.grados(), 2), m.estado])
                    for n, m in self.motores.items())

    def _leer_posiciones(self):
        if not self.archivo:
            return {}
        try:
            with open(self.archivo, encoding="utf-8") as f:
                d = json.load(f)
            return dict((k, (float(v[0]), int(v[1]))) for k, v in d.items())
        except (OSError, ValueError, TypeError, AttributeError, IndexError,
                KeyError):
            return {}

    def _guardar(self, forzar=False):
        """Escribe la posición si cambió (o siempre, con forzar)."""
        if not self.archivo:
            return
        actual = self._posiciones()
        if actual == self._guardado and not forzar:
            return
        tmp = self.archivo + ".tmp"
        try:
            # datos/ puede no existir todavía (probar el motor en un banco nuevo)
            os.makedirs(os.path.dirname(os.path.abspath(self.archivo)), exist_ok=True)
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(actual, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.archivo)      # nunca queda un archivo a medias
            self._guardado = actual
        except OSError:
            pass

    def guardar_ahora(self):
        self._guardar(forzar=True)
