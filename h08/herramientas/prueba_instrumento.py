# -*- coding: utf-8 -*-
"""
python3 -m h08 instrumento - probar los instrumentos de a uno, contra su carátula
================================================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

Con el servicio detenido (sudo systemctl stop tablero-h08):

    python3 -m h08 instrumento                  menú: elegir un instrumento
    python3 -m h08 instrumento AIRSPEED         ése solo
    python3 -m h08 instrumento --todos          todos, uno detrás del otro
    python3 -m h08 instrumento --todos --desde MAP
                                                seguir desde uno
    python3 -m h08 instrumento --listar         qué hay y dónde está conectado
    python3 -m h08 instrumento --simulado --todos --auto
                                                cómo es, sin hardware

Qué hace con cada uno:
  * SERVO: lo lleva por los números grandes de SU carátula (los valores de
    su tabla de calibración), con la misma cuenta que usa el tablero en
    marcha, y pregunta en cada uno "¿la aguja marca X?".
  * BRÚJULA (paso a paso): N, E, S, O y vuelta a N.
  * LUZ: la enciende 2 segundos y pregunta si se vio.

Al final guarda un informe en informes/instrumentos_FECHA.txt y, para cada
cosa que salió mal, dice con qué se arregla.
"""

import argparse
import sys

from h08.config import SERVO, MOTOR, LED
from h08.herramientas import interactivo as I

SECCION = "INSTRUMENTOS"


def listar():
    print("\n  %-15s %-8s %-6s %s" % ("INSTRUMENTO", "CANAL", "TIPO", "MECÁNICA"))
    for it in I.lista_instrumentos():
        print("  %-15s %-8s %-6s %s" % (it["id"], "%s:%d" % tuple(it["canal"]),
                                        it["actuador"], I.mecanica(it)))
    print("\n  Sin canal (sólo en la página): TACH_ROT, SLIP, ALTIMETER_100\n")


def elegir():
    lista = I.lista_instrumentos()
    print("")
    for i, it in enumerate(lista, 1):
        print("  %2d. %-15s %s:%d" % (i, it["id"], it["canal"][0], it["canal"][1]))
    try:
        r = input("\n  Número o nombre (Enter = todos): ").strip()
    except EOFError:
        return None
    if not r:
        return lista
    if r.isdigit() and 1 <= int(r) <= len(lista):
        return [lista[int(r) - 1]]
    it = I.buscar(r)
    if it is None:
        print("  No existe '%s'." % r)
        sys.exit(1)
    return [it]


# ---------------------------------------------------------------------------
def probar_servo(act, it, P, inf):
    puntos = I.puntos_de_prueba(it)
    print("  %s  -  %s" % (it["nombre"], I.mecanica(it)))
    print("  Va a recorrer: " + ", ".join(I.fmt_valor(it, v) for v in puntos))
    ang = I.angulo_servo(it, puntos[0])
    # Primer pulso directo al comienzo de la escala: el servo salta ahí una
    # sola vez y después todo es despacio.
    act.escribir_servo(it["canal"], ang)
    act.refrescar()
    I.dormir(0.8)
    fallas = []
    i = 0
    while i < len(puntos):
        v = puntos[i]
        nuevo = I.angulo_servo(it, v)
        ang = I.mover_servo(act, it, ang, nuevo)
        r = P.si_no("¿La aguja marca %s?  (servo a %.1f°)" % (I.fmt_valor(it, v), nuevo),
                    repetir=True)
        if r == "q":
            return False
        if r == "r":
            ang = I.mover_servo(act, it, ang, I.angulo_servo(it, puntos[max(0, i - 1)]))
            continue
        if r == "n":
            fallas.append(I.fmt_valor(it, v))
        i += 1
    # vuelta al medio y soltar: sin pulso no hace fuerza ni zumba
    I.mover_servo(act, it, ang, I.angulo_servo(it, puntos[len(puntos) // 2]))
    act.soltar(it["canal"])
    act.refrescar()
    if fallas:
        inf.mal(SECCION, it["id"], "no marca: " + ", ".join(fallas))
    else:
        inf.bien(SECCION, it["id"], "%d marcas" % len(puntos))
    return True


def probar_motor(gestor, it, P, inf):
    if gestor is None:
        inf.anotar(SECCION, it["id"], "SALTEADO", "no se pudo abrir el GPIO")
        return True
    n = I.motor_de(it)
    m = gestor.motores[n]
    print("  %s  -  motor %d, GPIO %s, aguja en %.1f°"
          % (it["nombre"], n, ",".join(str(p) for p in m.pines), m.grados()))
    fallas = []
    for g, letra in ((0, "N"), (90, "E"), (180, "S"), (270, "O"), (0, "N")):
        gestor.escribir_motor(tuple(it["canal"]), g)
        if not gestor.esperar_quietos(12):
            print("  (no llegó a tiempo: revisar 5 V de la plaquita y el cable)")
        r = P.si_no("¿La aguja apunta a la %s?" % letra)
        if r == "q":
            return False
        if r == "n":
            fallas.append(letra)
    if fallas:
        inf.mal(SECCION, it["id"], "no apunta a: " + ", ".join(fallas))
    else:
        inf.bien(SECCION, it["id"], "N-E-S-O-N")
    return True


def probar_luz(act, it, P, inf):
    print("  %s  -  %s:%d" % (it["nombre"], it["canal"][0], it["canal"][1]))
    while True:
        act.escribir_led(it["canal"], True)
        act.refrescar()
        I.dormir(2.0)
        act.escribir_led(it["canal"], False)
        act.refrescar()
        r = P.si_no("¿Se encendió %s y se apagó?" % it["id"], repetir=True)
        if r == "r":
            continue
        if r == "q":
            return False
        (inf.bien if r == "s" else inf.mal)(SECCION, it["id"])
        return True


ARREGLOS = {
    SERVO: ("Si marca corrido lo mismo en toda la escala: calzar la aguja con\n"
            "        python3 -m h08 canal {id} --valor {medio}\n"
            "      Si llega bien a un extremo y no al otro, o zumba en un tope:\n"
            "        python3 -m h08 calibrar {canal} --asistente\n"
            "      Si no se mueve: python3 -m h08 diagnostico y el cable del canal {canal}."),
    MOTOR: ("Si gira al revés: 'sentido' en MOTORES (h08/config/hardware.py).\n"
            "      Si queda corrida: python3 -m h08 motor 1 --mover -5 y después --cero.\n"
            "      Si tiembla y no gira: python3 -m h08 motor 1 --bobinas (orden A-B-C-D)."),
    LED: ("Si no prende: LED al revés, o el cable de J7/J8. Probar el LED solo con\n"
          "      una resistencia de 220 ohm entre +5 V y GND."),
}


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m h08 instrumento",
                                 description="Probar los instrumentos de a uno")
    ap.add_argument("instrumento", nargs="?")
    ap.add_argument("--todos", action="store_true")
    ap.add_argument("--desde", help="con --todos: empezar por éste")
    ap.add_argument("--listar", action="store_true")
    ap.add_argument("--simulado", action="store_true", help="sin hardware")
    ap.add_argument("--auto", action="store_true", help="contesta sí a todo (demostración)")
    a = ap.parse_args(argv)

    if a.listar:
        listar()
        return 0
    I.salir_si_no_hay_consola(a.auto)

    if a.instrumento:
        it = I.buscar(a.instrumento)
        if it is None:
            print("  No existe '%s' (ver --listar)." % a.instrumento)
            return 1
        lista = [it]
    elif a.todos:
        lista = I.lista_instrumentos()
        if a.desde:
            ids = [x["id"] for x in lista]
            if a.desde.upper() not in ids:
                print("  No existe '%s'." % a.desde)
                return 1
            lista = lista[ids.index(a.desde.upper()):]
    else:
        lista = elegir()
        if not lista:
            return 0

    P = I.Preguntas(a.auto)
    inf = I.Informe("PRUEBA DE INSTRUMENTOS - Tablero H-08" +
                    ("  (SIMULADA)" if a.simulado else ""))
    act = I.abrir_placas(a.simulado)
    gestor = None
    if any(it["actuador"] == MOTOR for it in lista):
        gestor = I.abrir_motor(a.simulado)

    try:
        for k, it in enumerate(lista, 1):
            print("\n" + "-" * 70)
            print(" %d/%d  %s  (%s:%d)" % (k, len(lista), it["id"], it["canal"][0], it["canal"][1]))
            print("-" * 70)
            if it["actuador"] == SERVO:
                if it["canal"][0] not in act.placas:
                    inf.anotar(SECCION, it["id"], "SALTEADO", "%s no responde" % it["canal"][0])
                    continue
                seguir = probar_servo(act, it, P, inf)
            elif it["actuador"] == MOTOR:
                seguir = probar_motor(gestor, it, P, inf)
            else:
                if it["canal"][0] not in act.placas:
                    inf.anotar(SECCION, it["id"], "SALTEADO", "%s no responde" % it["canal"][0])
                    continue
                seguir = probar_luz(act, it, P, inf)
            if not seguir:
                break
    except KeyboardInterrupt:
        print("")
    finally:
        if gestor is not None:
            gestor.cerrar()
        if getattr(act, "errores", 0):
            print("  OJO: %d escrituras por I2C fallaron. Última: %s"
                  % (act.errores, act.ultimo_error))
            inf.mal(SECCION, "bus I2C", "%d errores de escritura" % act.errores)
        act.cerrar()

    print("\n" + inf.texto())
    malos = inf.malos()
    if malos:
        print("\n  CÓMO SE ARREGLA")
        for _, que, _, _ in malos:
            it = I.buscar(que)
            if it is None:
                continue
            pts = I.puntos_de_prueba(it)
            print("\n    %s:\n      %s" % (que, ARREGLOS[it["actuador"]].format(
                id=it["id"], medio=pts[len(pts) // 2],
                canal="%s %d" % tuple(it["canal"]))))
    print("\n  Informe guardado en: %s\n" % inf.guardar("instrumentos"))
    return 1 if malos else 0


if __name__ == "__main__":
    sys.exit(main())
