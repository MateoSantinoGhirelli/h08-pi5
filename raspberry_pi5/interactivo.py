# -*- coding: utf-8 -*-
"""
interactivo.py - lo que comparten las pruebas guiadas del tablero
==================================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

Lo usan prueba_instrumento.py, prueba_luces_motor.py y prueba_general.py:

  * preguntar "¿se movió? ¿se encendió?" y anotar la respuesta;
  * guardar un informe con fecha en raspberry_pi5/informes/;
  * abrir las placas y el motor de verdad, o unos de mentira con --simulado
    (para ver cómo es la prueba en una computadora, sin hardware);
  * llevar un instrumento a un valor de su escala con la misma cuenta que usa
    el tablero en marcha (tabla de calibración x factor del barrido).
"""

import datetime
import os
import sys
import tempfile
import time

import banco
from configuracion import (TABLERO, TABLERO_POR_ID, MOTORES, SERVO, MOTOR, LED,
                           BARRIDO, ENGRANAJES, factor_servo, invertido, reduccion)
from utiles import interpolar_tabla

# (H08_INFORMES la usan las pruebas automáticas para no ensuciar la carpeta)
CARPETA_INFORMES = os.environ.get("H08_INFORMES") or os.path.join(banco.AQUI, "informes")

# Con --simulado no hay nada que mirar: las esperas se acortan.
_ESCALA_TIEMPO = [1.0]


def acelerar():
    _ESCALA_TIEMPO[0] = 0.02


def dormir(seg):
    time.sleep(seg * _ESCALA_TIEMPO[0])


# ===========================================================================
# Preguntas
# ===========================================================================
class Preguntas:
    """Hace las preguntas s/n. Con auto=True contesta "s" solo (para la
    prueba simulada o para una demostración sin nadie al lado)."""

    def __init__(self, auto=False):
        self.auto = auto

    def pausa(self, texto="Enter para seguir..."):
        if self.auto:
            print("  " + texto + "  [auto]")
            return
        try:
            input("  " + texto)
        except EOFError:
            pass

    def si_no(self, texto, repetir=False):
        """Devuelve 's', 'n', 'r' (repetir, si se permite) o 'q' (salir)."""
        op = "[Enter=sí / n=no%s / q=terminar]" % (" / r=repetir" if repetir else "")
        if self.auto:
            print("  %s %s  s [auto]" % (texto, op))
            return "s"
        while True:
            try:
                r = input("  %s %s " % (texto, op)).strip().lower()
            except EOFError:
                return "q"
            if r in ("", "s", "si", "sí", "y"):
                return "s"
            if r in ("n", "no"):
                return "n"
            if r == "q":
                return "q"
            if r == "r" and repetir:
                return "r"

    def nota(self, texto="¿Qué pasó? (una línea, Enter para nada)"):
        if self.auto:
            return ""
        try:
            return input("  " + texto + " ").strip()
        except EOFError:
            return ""


# ===========================================================================
# Informe
# ===========================================================================
class Informe:
    def __init__(self, titulo):
        self.titulo = titulo
        self.inicio = datetime.datetime.now()
        self.filas = []          # (sección, qué, "BIEN"/"MAL"/"SALTEADO", nota)

    def anotar(self, seccion, que, resultado, nota=""):
        self.filas.append((seccion, que, resultado, nota))

    def bien(self, seccion, que, nota=""):
        self.anotar(seccion, que, "BIEN", nota)

    def mal(self, seccion, que, nota=""):
        self.anotar(seccion, que, "MAL", nota)

    def malos(self):
        return [f for f in self.filas if f[2] == "MAL"]

    def texto(self):
        L = ["=" * 72,
             " " + self.titulo,
             " " + self.inicio.strftime("%d/%m/%Y %H:%M"),
             "=" * 72]
        seccion = None
        for s, que, res, nota in self.filas:
            if s != seccion:
                L.append("")
                L.append(" " + s)
                seccion = s
            L.append("   [%-8s] %s%s" % (res, que, ("  -  " + nota) if nota else ""))
        n_mal = len(self.malos())
        L += ["", "-" * 72,
              " %d controles, %d bien, %d mal, %d salteados"
              % (len(self.filas), sum(1 for f in self.filas if f[2] == "BIEN"), n_mal,
                 sum(1 for f in self.filas if f[2] == "SALTEADO")),
              " RESULTADO: " + ("TODO BIEN" if n_mal == 0 else "HAY %d PARA REVISAR" % n_mal),
              "=" * 72]
        return "\n".join(L)

    def guardar(self, nombre):
        os.makedirs(CARPETA_INFORMES, exist_ok=True)
        base = os.path.join(CARPETA_INFORMES, "%s_%s"
                            % (nombre, self.inicio.strftime("%Y%m%d_%H%M%S")))
        ruta, n = base + ".txt", 1
        while os.path.exists(ruta):          # dos pruebas en el mismo segundo
            n += 1
            ruta = "%s_%d.txt" % (base, n)
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(self.texto() + "\n")
        return ruta


# ===========================================================================
# Salidas: de verdad o de mentira
# ===========================================================================
class PlacasDeMentira:
    """Imita ActuadoresPCA9685 sin bus: anota lo último de cada canal."""

    def __init__(self):
        self.placas = {"PCA0": None, "PCA1": None}
        self.faltantes = []
        self.errores = 0
        self.ultimo_error = ""
        self.valores = {}
        self.motores = None

    def limites_us(self, destino):
        a, b = 500, 2500
        it = banco.que_hay_en(destino)
        if it is not None and it["actuador"] == SERVO and invertido(it["id"]):
            a, b = b, a
        return a, b

    def escribir_servo(self, destino, ang):
        self.valores[tuple(destino)] = round(ang, 2)

    def escribir_pulso(self, destino, us):
        self.valores[tuple(destino)] = ("us", us)

    def escribir_led(self, destino, encendida):
        self.valores[tuple(destino)] = bool(encendida)

    def soltar(self, destino):
        self.valores[tuple(destino)] = None

    def refrescar(self):
        return 0

    def cerrar(self):
        pass

    def descripcion(self):
        return "de mentira (--simulado)"


def abrir_placas(simulado):
    if simulado:
        acelerar()
        return PlacasDeMentira()
    banco.exigir_servicio_detenido()
    act = banco.abrir_placas()
    if act.faltantes:
        print("  ATENCIÓN, no responden: " + ", ".join(act.faltantes))
    return act


def abrir_motor(simulado):
    """GestorMotores andando (con su hilo). Con simulado, pines de mentira y
    la posición en un archivo temporal (no toca la guardada)."""
    from paso_a_paso import GestorMotores
    if simulado:
        acelerar()
        archivo = os.path.join(tempfile.gettempdir(), "h08_motor_simulado.json")
        g = GestorMotores(lambda pines, bits: None, archivo)
    else:
        from paso_a_paso import EscritorGPIO
        banco.exigir_servicio_detenido()
        try:
            g = GestorMotores(EscritorGPIO(), banco.ARCHIVO_MOTORES)
        except RuntimeError as e:
            print("  %s" % e)
            return None
    g.start()
    return g


# ===========================================================================
# Instrumentos
# ===========================================================================
def angulo_servo(it, valor):
    """Valor de la escala -> ángulo del servo, igual que mapa_tablero."""
    return interpolar_tabla(valor, it["cal"]) * factor_servo(it["id"])


def mover_servo(act, it, desde, hasta, seg=1.2):
    """Lleva el servo de un ángulo a otro despacio (como la aguja real)."""
    pasos = max(2, int(seg * 40))
    for i in range(pasos + 1):
        act.escribir_servo(it["canal"], desde + (hasta - desde) * i / pasos)
        act.refrescar()
        dormir(seg / pasos)
    return hasta


def puntos_de_prueba(it):
    """Los valores de la tabla de calibración: son justo los que la carátula
    tiene ubicados con precisión (los números grandes de la escala)."""
    vistos, pts = set(), []
    for v, _ in it["cal"]:
        if v not in vistos:
            vistos.add(v)
            pts.append(v)
    # El cabeceo del horizonte tiene una tabla calculada de muchos puntos:
    # alcanza con los extremos, el medio y los cuartos.
    if len(pts) > 7:
        n = len(pts) - 1
        pts = [pts[round(n * k / 4.0)] for k in range(5)]
    return pts


def mecanica(it):
    """Cómo va la aguja: directa, con engranajes o con su mecanismo."""
    b = BARRIDO.get(it["id"])
    if it["actuador"] == MOTOR:
        return "paso a paso, giro continuo"
    if b == "MEC":
        return "mecanismo del horizonte"
    if isinstance(b, (int, float)):
        r = reduccion(it["id"])
        if r > 1.0:
            par = ENGRANAJES.get(min(ENGRANAJES, key=lambda k: abs(k - r)))
            return "barre %g°, engranajes %d/%d (el servo gira al revés)" % (b, par[0], par[1])
        return "barre %g°, aguja directa en el servo" % b
    return ""


def fmt_valor(it, v):
    return "%g %s" % (v, it["unidad"])


def lista_instrumentos():
    """Los que tienen canal, en el orden del tablero: servos, motor, luces."""
    orden = {SERVO: 0, MOTOR: 1, LED: 2}
    return sorted([it for it in TABLERO if it.get("canal")],
                  key=lambda it: (orden.get(it["actuador"], 9),
                                  str(it["canal"][0]), it["canal"][1]))


def buscar(nombre):
    it = TABLERO_POR_ID.get(nombre.upper())
    if it and it.get("canal"):
        return it
    return None


def motor_de(it):
    """Número de motor de un instrumento de paso a paso."""
    return it["canal"][1] if it["actuador"] == MOTOR else None


def salir_si_no_hay_consola(auto):
    if not auto and not sys.stdin.isatty():
        print("  Esta prueba hace preguntas: correrla en una terminal "
              "(o con --auto para que conteste sola).")
        sys.exit(1)


__all__ = ["Preguntas", "Informe", "abrir_placas", "abrir_motor", "angulo_servo",
           "mover_servo", "dormir", "acelerar", "puntos_de_prueba", "mecanica", "fmt_valor",
           "lista_instrumentos", "buscar", "motor_de", "MOTORES",
           "salir_si_no_hay_consola"]
