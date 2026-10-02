#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
probar_canal.py - probar servos y luces de a uno
================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

Con el servicio del tablero detenido (sudo systemctl stop tablero-h08):

    python3 probar_canal.py --detectar          ¿responden las dos PCA9685?
    python3 probar_canal.py --listar            qué va en cada canal
    python3 probar_canal.py PCA0 3 --angulo 90  lleva ese servo a 90 grados
    python3 probar_canal.py PCA0 3 --barrer     de 0 a 180 y vuelta, despacio
    python3 probar_canal.py AIRSPEED --recorrer la escala entera del
                                                instrumento, con su calibración
    python3 probar_canal.py AIRSPEED --valor 0  lleva el instrumento a ese valor
                                                de su escala: así se calza la aguja
    python3 probar_canal.py --luces             enciende las seis luces de a una
    python3 probar_canal.py --apagar            luces apagadas y servos sueltos

Un canal se puede nombrar como PLACA CANAL o por el id del instrumento.
Al salir, el servo queda sin pulso (suelto).
"""

import argparse
import time

import banco
from configuracion import TABLERO, PLACAS, LED, SERVO, factor_servo
from utiles import interpolar_tabla


def detectar():
    from actuadores_pca9685 import BusI2C
    try:
        bus = BusI2C()
    except RuntimeError as e:
        print("\n  %s\n" % e)
        return 1
    faltan = 0
    for nombre, direccion in sorted(PLACAS.items()):
        ok = bus.responde(direccion)
        faltan += 0 if ok else 1
        print("  %s  0x%02X  %s" % (nombre, direccion,
                                    "responde" if ok else "NO RESPONDE"))
    bus.cerrar()
    if faltan:
        print("\n  Revisar: VCC 3,3 V y GND del módulo, SDA a GPIO2, SCL a GPIO3,")
        print("  y el puente A0 soldado sólo en la placa 1 (0x41).")
    return 1 if faltan else 0


def listar():
    cal = {}
    try:
        from actuadores_pca9685 import cargar_calibracion
        cal = cargar_calibracion(banco.ARCHIVO_CALIBRACION)
    except Exception:
        pass
    print("\n  %-10s %-15s %-6s %s" % ("CANAL", "INSTRUMENTO", "TIPO", "CALIBRACIÓN"))
    for nombre in sorted(PLACAS):
        for c in range(16):
            it = banco.que_hay_en((nombre, c))
            if it is None:
                print("  %s:%-5d %s" % (nombre, c, "-"))
                continue
            clave = "%s:%d" % (nombre, c)
            pulso = ""
            if it["actuador"] == SERVO:
                pulso = ("0°=%d 180°=%d us" % cal[clave][:2]) if clave in cal \
                    else "nominal"
            print("  %s:%-5d %-15s %-6s %s" % (nombre, c, it["id"],
                                              it["actuador"], pulso))
    print("\n  El paso a paso de la brújula no va por el PCA9685: ver probar_motor.py\n")


def mover_lento(act, destino, desde, hasta, seg):
    pasos = max(2, int(seg * 50))
    for i in range(pasos + 1):
        act.escribir_servo(destino, desde + (hasta - desde) * i / pasos)
        act.refrescar()
        time.sleep(seg / pasos)


def main():
    ap = argparse.ArgumentParser(description="Probar servos y luces del tablero H-08")
    ap.add_argument("canal", nargs="*", help="PCA0 3   o   AIRSPEED")
    ap.add_argument("--detectar", action="store_true")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--angulo", type=float)
    ap.add_argument("--barrer", action="store_true")
    ap.add_argument("--recorrer", action="store_true")
    ap.add_argument("--valor", type=float,
                    help="valor de la escala del instrumento (para calzar la aguja)")
    ap.add_argument("--luces", action="store_true")
    ap.add_argument("--apagar", action="store_true")
    ap.add_argument("--seg", type=float, default=3.0, help="duración de cada tramo")
    a = ap.parse_args()

    if a.detectar:
        return detectar()
    if a.listar:
        listar()
        return 0

    banco.exigir_servicio_detenido()
    act = banco.abrir_placas()
    if act.faltantes:
        print("  ATENCIÓN, no responden: " + ", ".join(act.faltantes))
        if act.placas:
            print("  (en el banco, con un solo módulo, es normal: se sigue con %s)"
                  % ", ".join(sorted(act.placas)))

    try:
        if a.apagar:
            print("  Luces apagadas y servos sin pulso.")
            return 0

        if a.luces:
            luces = [it for it in TABLERO if it["actuador"] == LED and it.get("canal")]
            for it in luces:
                print("  %-15s %s" % (it["id"], banco.nombre_de(it["canal"])))
                act.escribir_led(it["canal"], True)
                act.refrescar()
                time.sleep(1.0)
                act.escribir_led(it["canal"], False)
                act.refrescar()
            return 0

        destino, it = banco.resolver(a.canal)
        if destino is None:
            ap.print_help()
            return 1
        print("  " + banco.nombre_de(destino))
        if it is not None and it["actuador"] == LED:
            print("  Es una luz: encendida 3 s.")
            act.escribir_led(destino, True)
            act.refrescar()
            time.sleep(3.0)
            return 0

        if a.valor is not None and it is not None:
            ang = interpolar_tabla(a.valor, it["cal"]) * factor_servo(it["id"])
            print("  %s en %g %s (servo a %.1f°). Calzar la aguja sobre esa marca."
                  % (it["id"], a.valor, it["unidad"], ang))
            print("  Ctrl+C para soltar.")
            act.escribir_servo(destino, ang)
            act.refrescar()
            while True:
                time.sleep(1.0)

        if a.recorrer:
            if it is None:
                print("  Ese canal no tiene instrumento: usar --barrer.")
                return 1
            lo, hi = it["escala"]
            f = factor_servo(it["id"])
            n = 10
            valores = [lo + (hi - lo) * i / n for i in range(n + 1)]
            for v in valores + valores[-2::-1]:
                ang = interpolar_tabla(v, it["cal"]) * f
                print("    %10.1f %-7s -> servo %6.1f°" % (v, it["unidad"], ang))
                act.escribir_servo(destino, ang)
                act.refrescar()
                time.sleep(a.seg / 4)
            return 0

        if a.barrer:
            print("  0° -> 180° -> 0°  (Ctrl+C para cortar)")
            act.escribir_servo(destino, 0)
            act.refrescar()
            time.sleep(0.8)
            mover_lento(act, destino, 0, 180, a.seg)
            mover_lento(act, destino, 180, 0, a.seg)
            return 0

        ang = 90.0 if a.angulo is None else a.angulo
        us_min, us_max = act.limites_us(destino)
        print("  %.1f°  (pulso de %.0f us). Ctrl+C para soltar."
              % (ang, us_min + (us_max - us_min) * ang / 180.0))
        act.escribir_servo(destino, ang)
        act.refrescar()
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("")
    finally:
        # Un error de I2C no corta la prueba (se reintenta), pero hay que
        # decirlo: sin este aviso el servo no se mueve y no se sabe por qué.
        if act.errores:
            print("  OJO: %d escrituras por I2C fallaron. Última: %s"
                  % (act.errores, act.ultimo_error))
            print("  Revisar SDA/SCL y GND entre la Raspberry y el módulo.")
        act.cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
