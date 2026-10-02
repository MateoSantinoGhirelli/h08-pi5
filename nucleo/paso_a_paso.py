# -*- coding: utf-8 -*-
"""
paso_a_paso.py - agujas de giro continuo con motores 28BYJ-48
=============================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

POR QUÉ UN MOTOR PASO A PASO Y NO UN SERVO
---------------------------------------------------------------------------
Dos indicaciones del tablero dan vueltas enteras: la aguja de centenas del
altímetro (una vuelta cada 1000 pies) y la rosa de la brújula giroscópica
(pasa por el norte y sigue). Un servo tiene topes y tendría que desandar la
vuelta entera cada vez. El 28BYJ-48 gira indefinidamente en los dos sentidos
y trae una reducción de 63,68:1, así que mueve una aguja sin esfuerzo.

CÓMO SE CONECTA
---------------------------------------------------------------------------
Cada motor usa la plaquita ULN2003 con la que viene de fábrica, montada junto
al motor. Los cuatro GPIO de la Raspberry llegan por la placa madre y cables
Dupont a IN1..IN4 de la plaquita; el motor se enchufa en su conector blanco.
El ULN2003 es el que maneja la corriente de las bobinas (50 ohm a 5 V: unos
100 mA cada una, 200 mA con dos a la vez): un pin de la Raspberry no da más
de 16 mA y no tiene diodos para la descarga inductiva.

La secuencia de MEDIO PASO energiza una o dos bobinas por vez:

        IN1  IN1+IN2  IN2  IN2+IN3  IN3  IN3+IN4  IN4  IN4+IN1

Avanzar un paso es pasar al estado siguiente; retroceder, al anterior.

CÓMO SE MUEVE
---------------------------------------------------------------------------
Los motores tienen su propio hilo, que duerme hasta el instante del próximo
paso de cualquiera de los dos. La velocidad sigue un perfil trapezoidal:
arranca a vel_arranque_pps, acelera hasta vel_max_pps y frena a tiempo para
detenerse justo en el objetivo. Así no pierde pasos, y un
motor que no pierde pasos no necesita sensor de posición.

  * CAMINO MÁS CORTO: ir de 350 a 10 grados son 20 hacia adelante, no 340
    hacia atrás. El objetivo se lleva en grados "desenrollados".
  * BOBINAS SUELTAS EN REPOSO: quieto más de soltar_tras_s se cortan las
    bobinas. Un 28BYJ-48 energizado consume y se calienta aunque no se mueva;
    la reducción alcanza para que la aguja no se corra sola.
  * POSICIÓN GUARDADA: al apagar en orden, cada aguja vuelve a su cero y se
    guarda la posición en un archivo. Al encender se lee de ahí. Si hubo un
    corte de luz, la última posición guardada con el motor quieto sirve igual.
"""

import json
import math
import os
import threading
import time

from configuracion import MOTOR_CFG, MOTORES

SECUENCIA = (0b0001, 0b0011, 0b0010, 0b0110,
             0b0100, 0b1100, 0b1000, 0b1001)


def _envolver180(d):
    """Diferencia angular llevada a [-180, 180)."""
    return (d + 180.0) % 360.0 - 180.0


# ===========================================================================
# Un motor
# ===========================================================================
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
        # Posición en pasos y objetivo en grados, ambos "desenrollados":
        # pueden pasar de 360 o ser negativos.
        g = grados_iniciales % 360.0
        self.pos = int(round(g * self.ppv / 360.0))
        self.obj_grados = g
        self.estado = int(fase_inicial) % 8     # fase de la secuencia
        self.vel = 0.0          # pasos por segundo, siempre >= 0
        self.dir = 0            # +1, -1 o 0 (quieto)
        self.proximo = 0.0      # instante del paso siguiente
        self.energizado = False
        self.quieto_desde = time.monotonic()

    # -- órdenes (las llama otro hilo; son asignaciones simples) ------------
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

    # -- servicio (lo llama el hilo de motores) ----------------------------
    def servicio(self, ahora):
        """
        Da el paso que corresponda. Devuelve el instante en que quiere que lo
        vuelvan a llamar, o None si está quieto con las bobinas sueltas.

        El paso siguiente se programa a 1/velocidad del actual: si el hilo se
        atrasa, el motor va un poco más lento, nunca más rápido de lo que
        puede seguir sin perder pasos.
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
            # Re-energizar la fase donde quedó y darle 5 ms al rotor.
            self.escribir(self.pines, SECUENCIA[self.estado])
            self.energizado = True
            self.proximo = ahora + 0.005
            return self.proximo
        if ahora < self.proximo:
            return self.proximo

        # Perfil trapezoidal, calculado paso a paso: v² cambia 2·a por paso.
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


# ===========================================================================
# Salida a los GPIO de la Raspberry Pi 5
# ===========================================================================
class EscritorGPIO:
    """
    Pone los 4 pines IN1..IN4 de una plaquita. Usa gpiozero, que en la
    Raspberry Pi 5 trabaja sobre lgpio (RPi.GPIO no funciona con el chip RP1
    de la Pi 5). Sólo escribe los pines que cambian.
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


# ===========================================================================
# Los dos motores del tablero, con su hilo
# ===========================================================================
class GestorMotores(threading.Thread):
    """
    Recibe los ángulos del mapa del tablero (escribir_motor) y mueve los
    motores desde su propio hilo. El destino de cada instrumento es
    ("MOTOR", n), con n la clave de configuracion.MOTORES.
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
        # Todas las entradas de las plaquitas en bajo desde el arranque. Si
        # algún GPIO arranca con su resistencia de pull-up, sin esto dejaría
        # una bobina encendida hasta el primer movimiento de ese motor.
        for m in self.motores.values():
            m.soltar()
        self._parar = threading.Event()
        self._t_guardado = 0.0
        self._guardado = self._posiciones()

    # -- desde el mapa del tablero -----------------------------------------
    def escribir_motor(self, destino, angulo_deg):
        m = self.motores.get(destino[1])
        if m is not None:
            m.ir_a_grados(angulo_deg)

    def descripcion(self):
        return "%d motores paso a paso (GPIO %s)" % (
            len(self.motores),
            " / ".join(",".join(str(p) for p in m.pines)
                       for m in self.motores.values()))

    # -- hilo ---------------------------------------------------------------
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
                    # Entre paso y paso (~1 ms) se usa time.sleep: en Windows
                    # Event.wait no baja de ~15 ms y el motor iría 15 veces más
                    # lento (sólo importa al simular en la PC; en la Pi da igual).
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

    # -- posición persistente ----------------------------------------------
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
