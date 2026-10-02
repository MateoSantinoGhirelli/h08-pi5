# -*- coding: utf-8 -*-
"""
python3 -m h08 luces-motor - las seis luces de alerta y el motor de la brújula
=============================================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

Con el servicio detenido (sudo systemctl stop tablero-h08):

    python3 -m h08 luces-motor               luces y motor
    python3 -m h08 luces-motor --luces       sólo las luces
    python3 -m h08 luces-motor --motor       sólo el motor
    python3 -m h08 luces-motor --simulado --auto   cómo es, sin hardware

LUCES (PCA1, canales 8 a 13)
  El ánodo de cada LED va a +5 V (J8) y el cátodo vuelve por su resistencia
  de 220 ohm (R2..R7) a una salida del PCA9685 (J7): la luz ENCIENDE con la
  salida en BAJO. El programa ya lo sabe (LUCES_ACTIVAS_EN_BAJO).
    1. prueba de lámparas: las seis juntas;
    2. de a una, con su leyenda y su color: así se ve si hay dos cruzadas;
    3. todas apagadas: se mira si queda alguna "fantasma" (apenas encendida).

MOTOR DE LA BRÚJULA (28BYJ-48 + plaquita ULN2003, GPIO 12-16-20-21)
    1. bobinas de a una: los LED A, B, C, D de la plaquita en ese orden;
    2. N, E, S, O y vuelta a N;
    3. camino corto: de 350° a 10° tiene que ir 20° hacia adelante;
    4. tres vueltas y vuelve: tiene que quedar exactamente donde estaba;
    5. quieto, suelta las bobinas: los LED de la plaquita se apagan.

Guarda el informe en informes/luces_motor_FECHA.txt.
"""

import argparse
import sys

from h08.config import TABLERO, ANUNCIADOR, LED, MOTOR
from h08.herramientas import interactivo as I

S_LUZ = "LUCES DE ALERTA"
S_MOT = "MOTOR DE LA BRÚJULA"

FANTASMA = """
  LUZ FANTASMA: con la salida del PCA9685 "apagada" (en ALTO, 3,3 V) al LED le
  quedan 5 - 3,3 = 1,7 V. Un LED rojo o ámbar ya conduce un poquito con eso
  (una décima de miliampere) y en la oscuridad se ve tenue. No es el programa:
  el PCA9685 no puede subir su salida a 5 V.
  Arreglo, en la placa: un diodo 1N4148 en serie con cada LED (el ánodo del
  diodo hacia +5 V). Le saca 0,6 V: con 1,1 V ningún LED enciende, y
  encendido pierde apenas un poco de brillo."""


def luces(act, P, inf):
    lista = [it for it in TABLERO if it["actuador"] == LED and it.get("canal")]
    anun = {a["id"]: a for a in ANUNCIADOR}
    if "PCA1" not in act.placas:
        inf.anotar(S_LUZ, "todas", "SALTEADO", "PCA1 (0x41) no responde")
        print("  PCA1 no responde: las luces están en esa placa.")
        return True

    def todas(encendidas):
        for it in lista:
            act.escribir_led(it["canal"], encendidas)
        act.refrescar()

    # 1. prueba de lámparas
    print("\n  1. PRUEBA DE LÁMPARAS: las seis encendidas")
    todas(True)
    I.dormir(3.0)
    r = P.si_no("¿Están encendidas las SEIS luces?")
    if r == "q":
        todas(False)
        return False
    if r == "s":
        inf.bien(S_LUZ, "prueba de lámparas (las seis)")
    else:
        inf.mal(S_LUZ, "prueba de lámparas", P.nota("¿Cuál no enciende?"))
    todas(False)

    # 2. de a una
    print("\n  2. DE A UNA (si se enciende otra, hay cables cruzados)")
    for it in lista:
        a = anun.get(it["id"], {})
        while True:
            act.escribir_led(it["canal"], True)
            act.refrescar()
            I.dormir(1.5)
            r = P.si_no("¿Se encendió SOLO «%s» (%s)?  [%s:%d]"
                        % (a.get("leyenda", it["id"]), a.get("color", "?"),
                           it["canal"][0], it["canal"][1]), repetir=True)
            act.escribir_led(it["canal"], False)
            act.refrescar()
            if r != "r":
                break
        if r == "q":
            return False
        if r == "s":
            inf.bien(S_LUZ, it["id"])
        else:
            inf.mal(S_LUZ, it["id"], P.nota("¿Qué se vio? (ninguna / otra luz / tenue)"))

    # 3. apagadas: luz fantasma
    print("\n  3. TODAS APAGADAS durante 5 s. Mirar de cerca, mejor con poca luz.")
    todas(False)
    I.dormir(5.0)
    r = P.si_no("¿Están las seis BIEN apagadas, sin ninguna tenue?")
    if r == "q":
        return False
    if r == "s":
        inf.bien(S_LUZ, "apagadas del todo (sin luz fantasma)")
    else:
        inf.mal(S_LUZ, "luz fantasma con todo apagado", P.nota("¿Cuál queda tenue?"))
        print(FANTASMA)
    return True


def motor(gestor, P, inf):
    if gestor is None:
        inf.anotar(S_MOT, "todo", "SALTEADO", "no se pudo abrir el GPIO")
        return True
    it = next(x for x in TABLERO if x["actuador"] == MOTOR and x.get("canal"))
    destino = tuple(it["canal"])
    m = gestor.motores[destino[1]]
    esc = gestor.escritor
    print("\n  Motor %d, GPIO %s (IN1..IN4), sentido %+d, aguja en %.1f°"
          % (destino[1], ",".join(str(p) for p in m.pines), m.sentido, m.grados()))

    # 1. bobinas
    print("\n  1. BOBINAS de a una, 1 s cada una")
    for i, letra in enumerate("ABCD"):
        print("     IN%d -> LED %s" % (i + 1, letra))
        esc(m.pines, 1 << i)
        I.dormir(1.0)
    m.soltar()
    r = P.si_no("¿Se prendieron los LED de la plaquita en orden A, B, C, D?")
    if r == "q":
        return False
    if r == "s":
        inf.bien(S_MOT, "bobinas A-B-C-D")
    else:
        inf.mal(S_MOT, "bobinas A-B-C-D",
                P.nota("¿Qué se vio?") or "cables IN1..IN4 cruzados o sin 5 V en la plaquita")

    def ir(g, limite=15):
        gestor.escribir_motor(destino, g)
        if not gestor.esperar_quietos(limite):
            print("     (no llegó a tiempo)")

    # 2. puntos cardinales
    print("\n  2. PUNTOS CARDINALES")
    malos = []
    for g, letra in ((0, "N"), (90, "E"), (180, "S"), (270, "O"), (0, "N")):
        ir(g)
        r = P.si_no("¿La aguja apunta a la %s?" % letra)
        if r == "q":
            return False
        if r == "n":
            malos.append(letra)
    if malos:
        inf.mal(S_MOT, "N-E-S-O-N", "no apunta a " + ", ".join(malos) +
                ". Si gira al revés: 'sentido' en h08.config.MOTORES")
    else:
        inf.bien(S_MOT, "N-E-S-O-N")

    # 3. camino corto
    print("\n  3. CAMINO CORTO: a 350° y de ahí a 10°")
    ir(350)
    ir(10)
    r = P.si_no("¿De 350 a 10 fue un poquito hacia adelante (20°), sin dar la vuelta?")
    if r == "q":
        return False
    (inf.bien if r == "s" else inf.mal)(S_MOT, "camino más corto (350° -> 10°)")

    # 4. repetibilidad
    print("\n  4. TRES VUELTAS adelante y vuelve (unos 45 s)")
    ir(0)
    P.pausa("Mirá dónde está la aguja y apretá Enter...")
    inicio = m.obj_grados
    m.obj_grados = inicio + 3 * 360.0
    gestor.esperar_quietos(40)
    m.obj_grados = inicio
    gestor.esperar_quietos(40)
    r = P.si_no("¿Quedó EXACTAMENTE donde estaba?")
    if r == "q":
        return False
    if r == "s":
        inf.bien(S_MOT, "3 vueltas y vuelve: no pierde pasos")
    else:
        inf.mal(S_MOT, "3 vueltas y vuelve",
                "pierde pasos: 5 V de la plaquita (caída al moverse), o bajar vel_max_pps")

    # 5. suelta las bobinas
    print("\n  5. QUIETO: en medio segundo suelta las bobinas")
    I.dormir(1.5)
    r = P.si_no("¿Están apagados los 4 LED de la plaquita?")
    if r == "q":
        return False
    (inf.bien if r == "s" else inf.mal)(S_MOT, "bobinas sueltas en reposo")
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m h08 luces-motor",
                                 description="Probar las luces de alerta y el motor")
    ap.add_argument("--luces", action="store_true")
    ap.add_argument("--motor", action="store_true")
    ap.add_argument("--simulado", action="store_true")
    ap.add_argument("--auto", action="store_true")
    a = ap.parse_args(argv)
    hacer_luces = a.luces or not a.motor
    hacer_motor = a.motor or not a.luces
    I.salir_si_no_hay_consola(a.auto)

    P = I.Preguntas(a.auto)
    inf = I.Informe("PRUEBA DE LUCES Y MOTOR - Tablero H-08" +
                    ("  (SIMULADA)" if a.simulado else ""))
    act = I.abrir_placas(a.simulado) if hacer_luces else None
    gestor = I.abrir_motor(a.simulado) if hacer_motor else None
    try:
        seguir = True
        if hacer_luces:
            print("\n" + "=" * 70 + "\n LUCES DE ALERTA\n" + "=" * 70)
            seguir = luces(act, P, inf)
        if hacer_motor and seguir:
            print("\n" + "=" * 70 + "\n MOTOR DE LA BRÚJULA\n" + "=" * 70)
            motor(gestor, P, inf)
    except KeyboardInterrupt:
        print("")
    finally:
        if gestor is not None:
            gestor.cerrar()
        if act is not None:
            act.cerrar()
    print("\n" + inf.texto())
    print("\n  Informe guardado en: %s\n" % inf.guardar("luces_motor"))
    return 1 if inf.malos() else 0


if __name__ == "__main__":
    sys.exit(main())
