#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
calibrar_servo.py - el pulso exacto de 0° y de 180° de cada servo
=================================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

POR QUÉ
---------------------------------------------------------------------------
El programa convierte grados en ancho de pulso con valores nominales:
500 us = 0° y 2500 us = 180°. Cada servo real es distinto (sobre todo los
SG90 y los clones del MG90S): con los valores nominales uno llega a 170°,
otro a 195°, otro zumba contra su tope. La aguja no cae en las marcas.

La calibración mide, con un transportador impreso, qué pulso deja el brazo
del servo exactamente en 0° y en 180°. La calibración del instrumento (qué
ángulo corresponde a cada valor de la esfera) no se toca: sólo cambia cómo se
convierte ese ángulo en pulso.

EL TRANSPORTADOR
---------------------------------------------------------------------------
Se imprime al 100 % (Transportador_servo.pdf), se pega sobre cartón y se
apoya el servo con el eje sobre la cruz, mirándolo desde el lado del eje:
0° queda a la IZQUIERDA y 180° a la DERECHA, por arriba. Así se calibran
todos los servos, lleven engranajes o no: el programa sabe cuáles invierten
el sentido (configuracion.invertido) y lo corrige solo.

USO (con el servicio detenido: sudo systemctl stop tablero-h08)
---------------------------------------------------------------------------
    python3 calibrar_servo.py PCA0 3 --asistente   calibración guiada
    python3 calibrar_servo.py PCA0 --todos         los 16 canales, uno por uno
    python3 calibrar_servo.py PCA0 3 --probar      0 -> 180 -> 0 con lo guardado
    python3 calibrar_servo.py --listar             lo que hay guardado
    python3 calibrar_servo.py PCA0 3 --olvidar     vuelve al valor nominal
    python3 calibrar_servo.py PCA0 3 --pulso 1500  deja ese pulso fijo
    python3 calibrar_servo.py PCA0 3 --explorar abajo   busca el tope (Ctrl+C)

En lugar de «PCA0 3» se puede escribir el id del instrumento, por ejemplo
AIRSPEED. Lo medido queda en calibracion_servos.json, que el tablero lee al
arrancar. Ese archivo es de ESTE tablero y no se copia a otro.
"""

import argparse
import json
import os
import time

import banco
from configuracion import SERVO_CFG, SERVO, invertido

PASO_CHICO = 10     # us por cada «+» o «-»
PASO_GRANDE = 50    # us por cada «++» o «--»


def cargar():
    try:
        with open(banco.ARCHIVO_CALIBRACION, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def guardar(cal):
    tmp = banco.ARCHIVO_CALIBRACION + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cal, f, indent=1, sort_keys=True)
    os.replace(tmp, banco.ARCHIVO_CALIBRACION)


def listar(cal):
    print("\n  Nominal: 0° = %d us, 180° = %d us" % (SERVO_CFG["pulso_min_us"],
                                                    SERVO_CFG["pulso_max_us"]))
    if not cal:
        print("  Ningún servo calibrado todavía.\n")
        return
    for clave in sorted(cal, key=lambda k: (k.split(":")[0], int(k.split(":")[1]))):
        v = cal[clave]
        placa, canal = clave.split(":")
        if "us_0" in v:
            txt = "0° = %4d us   180° = %4d us" % (v["us_0"], v["us_180"])
            if v.get("tope_a") is not None:
                txt += "   (no pasa de %d / %d us)" % (v["tope_a"], v["tope_b"])
        else:
            txt = "%d a %d us (formato viejo)" % (v["min_us"], v["max_us"])
        print("  %-26s %s" % (banco.nombre_de((placa, int(canal))), txt))
    print("")


# ===========================================================================
# Asistente
# ===========================================================================
def ajustar(act, destino, us, marca):
    """Mueve el brazo con + y - hasta la marca. Devuelve (pulso, ángulo leído)."""
    print("\n  Llevar el brazo a la marca de %d°." % marca)
    print("  +  / -   mueve %d us      ++ / --   mueve %d us" % (PASO_CHICO, PASO_GRANDE))
    print("  un número (por ejemplo 1480) va a ese pulso")
    print("  Enter vacío: el brazo quedó sobre la marca")
    print("  Si el servo ZUMBA y no se mueve, está contra su tope: volver con")
    print("  el signo contrario hasta que deje de zumbar y aceptar ahí.")
    while True:
        us = max(300, min(2700, us))
        act.escribir_pulso(destino, us)
        act.refrescar()
        r = input("    %4d us > " % us).strip()
        if r == "":
            break
        if r in ("+", "-", "++", "--"):
            paso = PASO_GRANDE if len(r) == 2 else PASO_CHICO
            us += paso if r[0] == "+" else -paso
        else:
            try:
                us = int(r)
            except ValueError:
                print("    no entendí: + - ++ -- un número o Enter")
    leido = input("    ¿Sobre qué marca quedó el brazo? [Enter = %d°] > " % marca).strip()
    try:
        angulo = float(leido) if leido else float(marca)
    except ValueError:
        angulo = float(marca)
    return us, angulo


def asistente(act, destino, cal):
    clave = "%s:%d" % destino
    print("\n  ================================================================")
    print("  Calibrando " + banco.nombre_de(destino))
    print("  ================================================================")
    print("  1. Apoyar el servo sobre el transportador, con el eje en la cruz,")
    print("     mirándolo desde el lado del eje.")
    print("  2. El servo va a 1500 us (el medio). Poner el brazo apuntando lo más")
    print("     cerca posible de 90° (arriba). Si queda torcido no importa: la")
    print("     calibración lo corrige; sólo tiene que poder llegar a 0° y a 180°.")
    act.escribir_pulso(destino, 1500)
    act.refrescar()
    input("     Enter cuando el brazo esté puesto > ")

    ant = cal.get(clave, {})
    u1, a1 = ajustar(act, destino, int(ant.get("us_0", 600)), 0)
    u2, a2 = ajustar(act, destino, int(ant.get("us_180", 2400)), 180)
    if abs(a2 - a1) < 90 or abs(u2 - u1) < 500:
        print("\n  Los dos puntos están muy cerca: no se guarda nada. Repetir.")
        return False

    # Recta por los dos puntos medidos; si una marca no se alcanzó, se
    # extrapola y el pulso medido queda como tope.
    def pulso(ang):
        return u1 + (ang - a1) * (u2 - u1) / (a2 - a1)
    us_0, us_180 = round(pulso(0.0)), round(pulso(180.0))

    medio = round(pulso(90.0))
    act.escribir_pulso(destino, medio)
    act.refrescar()
    print("\n  Comprobación: el brazo tiene que estar en 90° (%d us)." % medio)
    v = input("    ¿En qué marca está? [Enter = 90°] > ").strip()
    try:
        error = float(v) - 90.0 if v else 0.0
    except ValueError:
        error = 0.0
    if abs(error) > 4:
        print("    Error de %.0f° en el medio: el servo no es lineal o se movió el"
              " transportador. Se guarda igual; conviene repetir." % error)

    dato = {"us_0": us_0, "us_180": us_180}
    if a1 != 0.0 or a2 != 180.0:
        dato["tope_a"], dato["tope_b"] = u1, u2
    print("\n  0° = %d us   180° = %d us%s" % (
        us_0, us_180, "   (topes %d y %d us)" % (u1, u2) if "tope_a" in dato else ""))
    it = banco.que_hay_en(destino)
    if it is not None and invertido(it["id"]):
        print("  Este canal lleva engranajes: en el instrumento el programa invierte")
        print("  el sentido solo. En el banco, sin engranajes, gira al revés: es correcto.")
    if input("  ¿Guardar? [S/n] > ").strip().lower() in ("", "s", "si", "sí"):
        cal[clave] = dato
        guardar(cal)
        print("  Guardado.")
        return True
    print("  No se guardó.")
    return False


def barrer(act, destino):
    a, b = act.limites_us(destino)
    print("  Barriendo 0° -> 180° -> 0° (%d -> %d us)." % (a, b))
    for i in list(range(0, 181, 2)) + list(range(180, -1, -2)):
        act.escribir_servo(destino, i)
        act.refrescar()
        time.sleep(0.02)


# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description="Calibrar servos con el transportador")
    ap.add_argument("canal", nargs="*", help="PCA0 3   o   AIRSPEED   (o PCA0 con --todos)")
    ap.add_argument("--asistente", action="store_true")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--probar", action="store_true")
    ap.add_argument("--olvidar", action="store_true")
    ap.add_argument("--pulso", type=int)
    ap.add_argument("--explorar", choices=("abajo", "arriba"))
    ap.add_argument("--desde", type=int, default=1500)
    ap.add_argument("--paso", type=int, default=25)
    ap.add_argument("--seg", type=float, default=0.8)
    a = ap.parse_args()

    cal = cargar()
    if a.listar:
        listar(cal)
        return 0

    if a.todos:
        placa = (a.canal[0] if a.canal else "PCA0").upper()
        banco.exigir_servicio_detenido()
        act = banco.abrir_placas()
        try:
            for n in range(16):
                destino = (placa, n)
                it = banco.que_hay_en(destino)
                if it is not None and it["actuador"] != SERVO:
                    continue
                r = input("\n  Canal %s. Enter para calibrar, s para saltar, q para "
                          "terminar > " % banco.nombre_de(destino)).strip().lower()
                if r == "q":
                    break
                if r == "s":
                    continue
                asistente(act, destino, cal)
                act.soltar(destino)
                act.refrescar()
        except (KeyboardInterrupt, EOFError):
            print("")
        finally:
            act.cerrar()
        listar(cargar())
        return 0

    destino, it = banco.resolver(a.canal)
    if destino is None:
        ap.print_help()
        return 1
    if it is not None and it["actuador"] != SERVO:
        print("  %s no es un servo." % banco.nombre_de(destino))
        return 1
    clave = "%s:%d" % destino

    if a.olvidar:
        if cal.pop(clave, None) is not None:
            guardar(cal)
        print("  %s vuelve a los valores nominales." % banco.nombre_de(destino))
        return 0

    banco.exigir_servicio_detenido()
    act = banco.abrir_placas()
    try:
        if a.asistente:
            asistente(act, destino, cal)
            return 0
        if a.probar:
            barrer(act, destino)
            return 0
        if a.explorar:
            paso = -abs(a.paso) if a.explorar == "abajo" else abs(a.paso)
            us = escrito = a.desde
            print("  Mirar el brazo: cuando deje de moverse y zumbe, Ctrl+C.")
            try:
                while 300 <= us <= 2700:
                    act.escribir_pulso(destino, us)
                    act.refrescar()
                    escrito = us
                    print("    %4d us" % us)
                    time.sleep(a.seg)
                    us += paso
            except KeyboardInterrupt:
                pass
            print("\n  Último valor bueno: %d us (un paso antes del que zumbó)."
                  % (escrito - paso))
            return 0
        us = a.pulso or 1500
        print("  %s: pulso de %d us. Ctrl+C para soltar." % (banco.nombre_de(destino), us))
        act.escribir_pulso(destino, us)
        act.refrescar()
        while True:
            time.sleep(1.0)
    except (KeyboardInterrupt, EOFError):
        print("")
    finally:
        act.cerrar()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
