#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prueba_hardware.py - la capa de hardware, probada sin hardware
==============================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

    python3 pruebas/prueba_hardware.py

PCA9685: se reemplaza el bus I2C por un PCA9685 de mentira que guarda sus
registros como el chip real (autoincremento, bits full ON / full OFF, estado
de encendido). Se comprueba lo que queda escrito EN EL CHIP, no lo que el
programa cree que escribió.

MOTORES: se reemplazan los GPIO por un rotor de mentira que sigue la
secuencia de medio paso y se da cuenta si una fase salta, si se da más de un
paso a la vez o si se pasa de la velocidad máxima.
"""

import json
import os
import sys
import tempfile
import time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)          # hasta pasar a unittest (fase 4)

from h08.hardware import pca9685 as P  # noqa: E402
from h08.hardware import paso_a_paso as M  # noqa: E402
from h08.config import TABLERO, LED, SERVO, MOTOR_CFG, PLACAS  # noqa: E402

fallos = []


def _lentitud_del_reloj():
    """Cuántas veces más lento que en la Pi duerme un hilo en esta máquina.

    En Windows las esperas cortas duran bastante más que en Linux, y un motor
    simulado tarda más en llegar. Las esperas de las pruebas se estiran en esa
    proporción para no confundir "PC lenta" con "motor que no llega".
    """
    n, t0 = 30, time.perf_counter()
    for _ in range(n):
        time.sleep(0.001)
    por_paso = (time.perf_counter() - t0) / n
    return max(1.0, por_paso / 0.0012)


LENTO = _lentitud_del_reloj()
M.GestorMotores.LIMITE_CIERRE_S = 8.0 * LENTO


def cierto(nombre, v, detalle=""):
    print("  %s %s%s" % ("ok  " if v else "MAL ", nombre,
                         "" if v else "   " + str(detalle)))
    if not v:
        fallos.append(nombre)


# ===========================================================================
# Un PCA9685 de mentira
# ===========================================================================
class ChipFalso:
    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        """Estado de encendido según la hoja de datos."""
        self.r = [0] * 256
        self.r[0x00] = 0x11            # MODE1: SLEEP + ALLCALL
        self.r[0x01] = 0x04            # MODE2: OUTDRV
        self.r[0xFE] = 0x1E            # PRESCALE de fábrica (200 Hz)
        for c in range(16):
            self.r[0x06 + 4 * c + 3] = 0x10     # LEDn_OFF_H: full OFF

    def escribir(self, reg, datos):
        ai = self.r[0x00] & 0x20
        for b in datos:
            if reg == 0xFE and not (self.r[0x00] & 0x10):
                pass                   # el prescaler sólo se escribe dormido
            else:
                self.r[reg] = b
            if reg == 0x00 and b & 0x80:
                self.r[0x00] &= 0x7F   # RESTART se borra solo
            if ai:
                reg = (reg + 1) & 0xFF

    def salida(self, c):
        """('alta'|'baja'|'pwm', cuentas en alto)."""
        on_l, on_h, off_l, off_h = self.r[0x06 + 4 * c: 0x0A + 4 * c]
        if off_h & 0x10:
            return ("baja", 0)
        if on_h & 0x10:
            return ("alta", 4096)
        on = on_l | (on_h & 0x0F) << 8
        off = off_l | (off_h & 0x0F) << 8
        return ("pwm", (off - on) % 4096)


class BusFalso:
    def __init__(self, direcciones):
        self.chips = dict((d, ChipFalso()) for d in direcciones)
        self.transacciones = []
        self.fallar = 0                # cuántas escrituras fallan a propósito

    def escribir(self, direccion, registro, datos=()):
        if direccion not in self.chips:
            raise OSError(121, "Remote I/O error")
        if self.fallar:
            self.fallar -= 1
            raise OSError(121, "Remote I/O error")
        self.transacciones.append((direccion, registro, len(datos)))
        self.chips[direccion].escribir(registro, list(datos))

    def leer(self, direccion, registro, n=1):
        if direccion not in self.chips:
            raise OSError(121, "Remote I/O error")
        return bytes(self.chips[direccion].r[registro:registro + n])

    def responde(self, direccion):
        return direccion in self.chips

    def cerrar(self):
        pass


def probar_pca():
    print("\n  PCA9685")
    bus = BusFalso(PLACAS.values())
    tmp = tempfile.mkdtemp()
    cal = os.path.join(tmp, "cal.json")
    with open(cal, "w") as f:
        json.dump({"PCA0:0": {"min_us": 600, "max_us": 2400},          # formato viejo
                   "PCA0:1": {"us_0": 650, "us_180": 2450,             # con transportador
                              "tope_a": 700, "tope_b": 2450},
                   "PCA0:15": {"us_0": 2400, "us_180": 600}}, f)       # servo al revés
    act = P.ActuadoresPCA9685(bus=bus, calibracion=cal)
    c0, c1 = bus.chips[0x40], bus.chips[0x41]

    cierto("prescaler 121 (50 Hz) en las dos placas",
           c0.r[0xFE] == 121 and c1.r[0xFE] == 121, (c0.r[0xFE], c1.r[0xFE]))
    cierto("despiertas, con autoincremento y salida totem-pole",
           c0.r[0] & 0x30 == 0x20 and c0.r[1] == 0x04, hex(c0.r[0]))
    luces = [tuple(it["canal"]) for it in TABLERO if it["actuador"] == LED and it.get("canal")]
    servos = [tuple(it["canal"]) for it in TABLERO if it["actuador"] == SERVO and it.get("canal")]
    ch = {"PCA0": c0, "PCA1": c1}
    cierto("al arrancar: luces apagadas (salida en ALTO, LED a +5 V)",
           all(ch[p].salida(c)[0] == "alta" for p, c in luces))
    cierto("al arrancar: servos sin pulso",
           all(ch[p].salida(c)[0] == "baja" for p, c in servos))

    f = act.placas["PCA0"].frecuencia
    cu = lambda us: round(us * 4096 * f / 1e6)
    for ang, us in ((0, 500), (90, 1500), (180, 2500)):
        act.escribir_servo(("PCA0", 2), ang)          # sin calibrar, con engranajes
        act.refrescar()
        esperado = cu(2000 - us + 1000)               # invertido: 0° -> 2500 us
        cierto("servo nominal con engranajes %3d° -> %d us" % (ang, 3000 - us),
               c0.salida(2) == ("pwm", esperado), c0.salida(2))
    act.escribir_servo(("PCA1", 3), 0)                # AMMETER: directo, sin calibrar
    act.refrescar()
    cierto("servo nominal directo 0° -> 500 us",
           c1.salida(3) == ("pwm", cu(500)), c1.salida(3))
    act.escribir_servo(("PCA0", 0), 180)
    act.refrescar()
    cierto("calibración vieja (min/max) 180° -> 2400 us",
           c0.salida(0) == ("pwm", cu(2400)), c0.salida(0))
    act.escribir_servo(("PCA0", 1), 0)
    act.refrescar()
    cierto("con engranajes 0° del programa -> la marca de 180° (2450 us)",
           c0.salida(1) == ("pwm", cu(2450)), c0.salida(1))
    act.escribir_servo(("PCA0", 1), 180)
    act.refrescar()
    cierto("y 180° no pasa del tope medido (700 us, no 650)",
           c0.salida(1) == ("pwm", cu(700)), c0.salida(1))
    act.escribir_servo(("PCA0", 15), 0)
    act.refrescar()
    cierto("un servo que gira al revés se corrige con la calibración",
           c0.salida(15) == ("pwm", cu(2400)), c0.salida(15))

    p, c = luces[0]
    act.escribir_led((p, c), True)
    act.refrescar()
    cierto("luz encendida = salida en BAJO (el PCA9685 sumidera)",
           ch[p].salida(c)[0] == "baja")
    act.escribir_led((p, c), False)
    act.refrescar()
    cierto("luz apagada = salida en ALTO", ch[p].salida(c)[0] == "alta")

    bus.transacciones = []
    for i in range(16):
        act.escribir_servo(("PCA0", i), 10 + i)
    act.refrescar()
    cierto("16 canales en UNA transacción de 64 bytes",
           bus.transacciones == [(0x40, 0x06, 64)], bus.transacciones)
    bus.transacciones = []
    act.refrescar()
    cierto("sin cambios no se toca el bus", bus.transacciones == [])

    bus.fallar = 1
    act.escribir_servo(("PCA0", 5), 45)
    act.refrescar()
    cierto("un error de bus se cuenta y no corta el programa", act.errores == 1)
    act.refrescar()
    cierto("y el canal se reintenta en el ciclo siguiente",
           c0.salida(5) == ("pwm", cu(2500 - 2000 * 45 / 180)))   # CHT: con engranajes

    c0.reiniciar()                      # una caída de tensión reinicia el chip
    act._t_vigilancia -= 10
    act.refrescar()
    cierto("chip reiniciado: se detecta y se reconfigura",
           c0.r[0xFE] == 121 and c0.r[0] & 0x30 == 0x20
           and act.placas["PCA0"].reinicios == 1)
    cierto("y recupera los ángulos que tenía",
           c0.salida(5)[0] == "pwm" and c0.salida(0)[0] == "pwm")

    act.cerrar()
    cierto("al cerrar: servos sin pulso",
           all(ch[p].salida(c)[0] == "baja" for p, c in servos))
    cierto("al cerrar: luces apagadas",
           all(ch[p].salida(c)[0] == "alta" for p, c in luces))

    # Una placa que no está
    bus2 = BusFalso([0x40])
    act2 = P.ActuadoresPCA9685(bus=bus2)
    act2.escribir_servo(("PCA1", 0), 90)
    act2.refrescar()
    cierto("si falta una placa se informa y el resto anda",
           "PCA1" in act2.descripcion() and act2.errores == 0, act2.descripcion())


def probar_tablero_completo():
    """El simulador entero escribiendo sobre las placas de mentira."""
    print("\n  SIMULADOR SOBRE LAS PLACAS")
    from h08.simulacion.simulador import Simulador
    bus = BusFalso(PLACAS.values())
    act = P.ActuadoresPCA9685(bus=bus)
    sim = Simulador(act, semilla=5)
    sim.modo_normal()
    for _ in range(20 * 60):
        sim.paso(0.05)
        sim.mapa.escribir()
    ch = {"PCA0": bus.chips[0x40], "PCA1": bus.chips[0x41]}
    f = act.placas["PCA0"].frecuencia
    bien = True
    for c in sim.mapa.canales:
        if not c.activo or c.tipo not in (LED, SERVO):
            continue
        p, n = c.destino
        sal = ch[p].salida(n)
        if c.tipo == LED:
            bien &= sal[0] == ("baja" if c.ang_escrito >= 0.5 else "alta")
        else:
            a, b = act.limites_us(c.destino)
            us = a + (b - a) * min(max(c.ang_escrito, 0), 180) / 180.0
            bien &= sal[0] == "pwm" and abs(sal[1] - us * 4096 * f / 1e6) <= 1
    cierto("un minuto de vuelo: cada canal del chip coincide con el mapa", bien)
    sim.prueba_luces(True)
    for _ in range(4):
        sim.paso(0.05)
        sim.mapa.escribir()
    cierto("prueba de lámparas: las seis salidas en BAJO",
           all(ch[c.destino[0]].salida(c.destino[1])[0] == "baja"
               for c in sim.mapa.canales if c.tipo == LED))


# ===========================================================================
# Motores con un rotor de mentira
# ===========================================================================
class RotorFalso:
    """Sigue las fases y cuenta pasos; detecta saltos de fase."""

    def __init__(self):
        self.bits = 0
        self.fase = None
        self.pasos = 0
        self.saltos = 0
        self.tiempos = []
        self.escrituras = []

    def __call__(self, pines, bits, t=None):
        self.escrituras.append(bits)
        self.bits = bits
        if bits == 0:
            return
        f = M.SECUENCIA.index(bits)
        if self.fase is not None and f != self.fase:
            d = (f - self.fase) % 8
            if d == 1:
                self.pasos += 1
            elif d == 7:
                self.pasos -= 1
            else:
                self.saltos += 1
            self.tiempos.append(RELOJ[0])
        self.fase = f


class RotoresFalsos:
    """Un rotor de mentira por motor, elegido por sus pines."""

    def __init__(self):
        self.rotores = {}

    def __call__(self, pines, bits):
        self.rotores.setdefault(pines, RotorFalso())(pines, bits)

    @property
    def pasos(self):
        return sum(abs(r.pasos) for r in self.rotores.values())

    @property
    def saltos(self):
        return sum(r.saltos for r in self.rotores.values())

    @property
    def bits(self):
        return sum(r.bits for r in self.rotores.values())


RELOJ = [0.0]


def correr_motor(m, seg):
    """Llama al motor en los instantes que él pide, con 0,1 ms de atraso."""
    fin = RELOJ[0] + seg
    while RELOJ[0] < fin:
        prox = m.servicio(RELOJ[0])
        RELOJ[0] = min(fin, (prox + 0.0001) if prox else RELOJ[0] + 0.05)


# El gestor se prueba con dos motores aunque el tablero use uno solo: así se
# comprueba que cada uno lleva su posición por separado.
MOTORES_PRUEBA = {0: {"id": "A", "pines": (6, 13, 19, 26), "sentido": +1},
                  1: {"id": "B", "pines": (12, 16, 20, 21), "sentido": -1}}


def probar_motores():
    print("\n  MOTORES PASO A PASO")
    ppv = MOTOR_CFG["pasos_por_vuelta"]
    rotor = RotorFalso()
    m = M.MotorContinuo(rotor, (6, 13, 19, 26), sentido=1)
    RELOJ[0] = 0.0
    m.ir_a_grados(90)
    correr_motor(m, 3.0)
    cierto("90° = %d pasos, sin saltos de fase" % round(ppv / 4),
           rotor.pasos == round(ppv / 4) and rotor.saltos == 0, (rotor.pasos, rotor.saltos))
    difs = [b - a for a, b in zip(rotor.tiempos, rotor.tiempos[1:])]
    cierto("nunca más rápido que %d pasos/s" % MOTOR_CFG["vel_max_pps"],
           min(difs) >= 1.0 / MOTOR_CFG["vel_max_pps"] - 1e-9, min(difs))
    cierto("bobinas sueltas en reposo", rotor.bits == 0)

    m.ir_a_grados(350)
    correr_motor(m, 3.0)
    antes = rotor.pasos
    m.ir_a_grados(10)
    correr_motor(m, 2.0)
    cierto("de 350° a 10° por el camino corto (+20°, no -340°)",
           abs((rotor.pasos - antes) - 20 * ppv / 360) <= 1, rotor.pasos - antes)

    n0 = len(rotor.escrituras)
    m.ir_a_grados(20)
    correr_motor(m, 0.004)
    cierto("antes del primer paso se re-energiza la fase donde quedó",
           rotor.escrituras[n0] == M.SECUENCIA[m.estado]
           and rotor.pasos == antes + round(20 * ppv / 360))
    correr_motor(m, 2.0)

    # Cambio de sentido en plena marcha: frena, se pasa un poco y vuelve.
    m.ir_a_grados(170)
    correr_motor(m, 0.3)
    m.ir_a_grados(20)
    correr_motor(m, 4.0)
    cierto("cambio de sentido en marcha: termina justo en el objetivo",
           abs(m.grados() - 20) < 0.1 and rotor.saltos == 0, m.grados())

    # Diez vueltas y vuelta: la aguja vuelve exactamente al mismo lugar.
    inicio = rotor.pasos
    m.obj_grados += 3600
    correr_motor(m, 60)
    cierto("10 vueltas = %.0f pasos" % (10 * ppv),
           abs((rotor.pasos - inicio) - 10 * ppv) <= 1, rotor.pasos - inicio)

    # Sentido invertido: la misma orden gira las fases al revés.
    r2 = RotorFalso()
    m2 = M.MotorContinuo(r2, (12, 16, 20, 21), sentido=-1)
    m2.ir_a_grados(45)
    correr_motor(m2, 2.0)
    cierto("sentido -1: las fases giran al revés", r2.pasos == -round(ppv / 8), r2.pasos)

    # Gestor completo, con hilo y archivo de posición.
    tmp = tempfile.mkdtemp()
    arch = os.path.join(tmp, "pos.json")
    r3 = RotoresFalsos()
    g = M.GestorMotores(r3, arch, motores=MOTORES_PRUEBA)
    g.start()
    g.escribir_motor(("MOTOR", 0), 100)
    g.escribir_motor(("MOTOR", 1), 200)
    llegaron = g.esperar_quietos(5.0 * LENTO)
    cierto("hilo de motores: los dos llegan a su objetivo", llegaron)
    g.cerrar()
    with open(arch) as f:
        guardado = json.load(f)
    cierto("al cerrar vuelven a cero y se guarda la posición",
           abs(g.motores[0].grados() % 360) < 0.1 and abs(g.motores[1].grados() % 360) < 0.1
           and all(abs(v[0] % 360) < 0.1 or abs(v[0] - 360) < 0.1
                   for v in guardado.values()), guardado)

    with open(arch, "w") as f:
        json.dump({"0": [123.4, 5], "1": [0, 0]}, f)
    g2 = M.GestorMotores(RotorFalso(), arch, motores=MOTORES_PRUEBA)
    cierto("al arrancar lee la posición y la fase guardadas",
           abs(g2.motores[0].grados() - 123.4) < 0.1 and g2.motores[0].estado == 5)
    with open(arch, "w") as f:
        f.write("{roto")
    g3 = M.GestorMotores(RotorFalso(), arch, motores=MOTORES_PRUEBA)
    cierto("archivo dañado: arranca en cero sin romperse",
           g3.motores[0].grados() == 0)


def probar_en_marcha():
    """Los tres hilos juntos, en tiempo real, y el apagado ordenado."""
    print("\n  EN MARCHA (8 segundos en tiempo real)")
    from h08.simulacion.hilo import HiloSimulacion
    bus = BusFalso(PLACAS.values())
    act = P.ActuadoresPCA9685(bus=bus)
    rotor = RotoresFalsos()
    arch = os.path.join(tempfile.mkdtemp(), "pos.json")
    act.motores = M.GestorMotores(rotor, arch)
    act.motores.start()
    nucleo = HiloSimulacion(act, semilla=3)
    nucleo.start()
    nucleo.ordenar("modo_normal", "CRUCERO")
    time.sleep(8.0)
    foto = nucleo.foto
    cierto("la simulación corre y publica la foto", foto.get("t", 0) > 5, foto.get("t"))
    cierto("sin errores de programa ni de bus",
           foto["hardware"]["errores_programa"] == 0
           and foto["hardware"]["errores_i2c"] == 0, foto.get("hardware"))
    cierto("los motores se movieron sin saltar fases", rotor.pasos != 0 and rotor.saltos == 0,
           (rotor.pasos, rotor.saltos))
    nucleo.detener()
    nucleo.join(15)
    ch = {"PCA0": bus.chips[0x40], "PCA1": bus.chips[0x41]}
    cierto("apagado: el hilo terminó", not nucleo.is_alive())
    cierto("apagado: luces apagadas y servos sin pulso",
           all(ch[c.destino[0]].salida(c.destino[1])[0] ==
               ("alta" if c.tipo == LED else "baja")
               for c in nucleo.sim.mapa.canales if c.activo and c.tipo in (LED, SERVO)))
    cierto("apagado: agujas de los motores en cero y bobinas sueltas",
           all(min(m.grados(), 360 - m.grados()) < 0.1
               for m in act.motores.motores.values()) and rotor.bits == 0)


def main():
    probar_pca()
    probar_en_marcha()
    probar_tablero_completo()
    probar_motores()
    print("\n" + "=" * 70)
    print(" Todo bien." if not fallos else " FALLARON %d: %s" % (len(fallos), fallos))
    print("=" * 70)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
