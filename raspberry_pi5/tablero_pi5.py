#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tablero_pi5.py - programa principal del tablero en la Raspberry Pi 5
====================================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

    python3 tablero_pi5.py                 tablero completo: servos, luces,
                                           el paso a paso de la brújula y la
                                           página web
    python3 tablero_pi5.py --simulado      sin hardware: sólo la página web
                                           (anda también en una computadora)
    python3 tablero_pi5.py --sin-motores   sin el paso a paso de la brújula
    python3 tablero_pi5.py --banco         banco de pruebas en protoboard: un
                                           solo PCA9685 con servos, sin motores
                                           y con la botonera abierta
    python3 tablero_pi5.py --qr-admin      muestra el QR del administrador
    python3 tablero_pi5.py --qr-admin --hoja admin.html
                                           y además una hoja para imprimir
    python3 tablero_pi5.py --renovar-clave invalida el QR de administrador

Arranca tres hilos: la simulación a 20 Hz (hilo_simulacion.py), el motor
paso a paso de la brújula (paso_a_paso.py) y el servidor web en el puerto 8000.
Lo arranca solo el servicio tablero-h08 al encender (ver instalar.sh); la
pantalla de la Raspberry lo muestra con kiosco.sh.

Al recibir Ctrl+C o la orden de parada del servicio (SIGTERM o SIGINT) se
apaga en orden: luces apagadas, servos sin pulso, la aguja de la brújula a su
cero y posición guardada.
"""

import argparse
import datetime
import os
import signal
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(AQUI), "nucleo"))
sys.path.insert(0, AQUI)

from configuracion import AERONAVE, TABLERO, MOTOR_CFG       # noqa: E402
from fallas import CATALOGO                                  # noqa: E402
from escenarios import ESCENARIOS                            # noqa: E402
from acceso import Acceso                                    # noqa: E402
from hilo_simulacion import HiloSimulacion                   # noqa: E402
import qr                                                    # noqa: E402
import servidor_web                                          # noqa: E402

ARCHIVO_CLAVE = os.path.join(AQUI, "secreto_admin.json")
ARCHIVO_CALIBRACION = os.path.join(AQUI, "calibracion_servos.json")
ARCHIVO_MOTORES = os.path.join(AQUI, "posicion_motores.json")


def version():
    """La versión instalada, de VERSION.txt (la escribe el paquete)."""
    try:
        with open(os.path.join(os.path.dirname(AQUI), "VERSION.txt"),
                  encoding="utf-8") as f:
            return f.readline().strip()
    except OSError:
        return "versión de desarrollo"


def construir_actuadores(simulado, con_motores):
    """El único lugar del programa donde se decide sobre qué se escribe.

    Si falta el hardware, el tablero no se cae: avisa y sigue con la página
    web sola, que es lo que ve el público.
    """
    from actuadores_simulados import ActuadoresSimulados
    if simulado:
        return ActuadoresSimulados()
    try:
        from actuadores_pca9685 import ActuadoresPCA9685
        actuadores = ActuadoresPCA9685(calibracion=ARCHIVO_CALIBRACION)
    except (RuntimeError, OSError) as e:
        print("\n  NO SE PUDO ABRIR EL BUS I2C: %s" % e)
        print("  El tablero sigue sólo con la página web.\n")
        return ActuadoresSimulados()
    if con_motores:
        try:
            from paso_a_paso import GestorMotores, EscritorGPIO
            motores = GestorMotores(EscritorGPIO(), ARCHIVO_MOTORES)
            motores.start()
            actuadores.motores = motores
        except Exception as e:
            print("\n  SIN MOTORES PASO A PASO: %s\n" % e)
    return actuadores


# ===========================================================================
# QR del administrador
# ===========================================================================
# No se sirve por la web a propósito: una página que muestra la llave es una
# página a la que se le puede pedir la llave. Sale por la terminal de la
# Raspberry o en una hoja impresa.
def url_admin(puerto, clave):
    return servidor_web.direccion(puerto).rstrip("/") + "/mando?k=" + clave


def cartel_admin(puerto, clave, ancho=70):
    url = url_admin(puerto, clave)
    return "\n".join([
        "=" * ancho,
        " QR DEL ADMINISTRADOR  -  no compartir, no proyectar",
        "=" * ancho,
        " Quien lea este código puede operar el tablero.",
        "",
        qr.texto_consola(url, borde=1),
        "",
        " " + url,
        "",
        " Si se filtró:  python3 tablero_pi5.py --renovar-clave",
        "=" * ancho])


HOJA_ADMIN = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>QR del administrador - Tablero H-08</title>
<style>
 @page{size:A4;margin:18mm}
 body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:0}
 .hoja{max-width:170mm;margin:0 auto;text-align:center}
 h1{font-size:19pt;color:#1F3864;margin:0 0 2mm}
 .sub{font-size:10.5pt;color:#555;margin:0 0 8mm}
 .aviso{border:2px solid #a32;color:#a32;border-radius:4mm;padding:4mm 6mm;
   font-size:11pt;margin:0 0 8mm;line-height:1.5}
 .qr{margin:0 auto 5mm;width:320px}
 .url{font-family:monospace;font-size:8.5pt;color:#444;word-break:break-all}
 ul{text-align:left;font-size:10.5pt;line-height:1.7;max-width:130mm;margin:6mm auto}
 .pie{font-size:9pt;color:#777}
</style></head><body><div class="hoja">
<h1>Tablero H-08 &middot; QR del administrador</h1>
<p class="sub">Sikorsky S-55 / H-19A &middot; EEST N&deg; 7 Taller Regional Quilmes</p>
<div class="aviso"><b>Esta hoja no se pega en la pared.</b><br>
Quien lea este c&oacute;digo puede operar el tablero.</div>
<div class="qr">%(svg)s</div>
<p class="url">%(url)s</p>
<ul>
<li>Se lee con la c&aacute;mara del celular; la clave va dentro del c&oacute;digo.</li>
<li>Pueden entrar varios administradores, pero uno solo tiene el mando a la vez.</li>
<li>Si la Raspberry cambia de red, hay que volver a generar esta hoja.</li>
<li>Si el c&oacute;digo se filtra: <b>python3 tablero_pi5.py --renovar-clave</b></li>
</ul>
<p class="pie">Generada el %(fecha)s</p>
</div></body></html>"""


def hoja_admin(puerto, clave, destino):
    url = url_admin(puerto, clave)
    with open(destino, "w", encoding="utf-8") as f:
        f.write(HOJA_ADMIN % {
            "svg": qr.svg(url, 320), "url": url,
            "fecha": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")})
    try:
        os.chmod(destino, 0o600)
    except OSError:
        pass


def imprimir_banco(actuadores):
    """Qué instrumento hace cada canal de las placas que respondieron."""
    from configuracion import SERVO, LED, invertido
    placas = getattr(actuadores, "placas", {})
    print("\n BANCO DE PRUEBAS: cada servo hace de este instrumento")
    for it in sorted(TABLERO, key=lambda d: (str((d.get("canal") or ("", 0))[0]),
                                             (d.get("canal") or ("", 0))[1])):
        canal = it.get("canal")
        if not canal or canal[0] not in placas or it["actuador"] not in (SERVO, LED):
            continue
        extra = "  <- gira al revés (en el tablero lleva engranajes)" \
            if it["actuador"] == SERVO and invertido(it["id"]) else ""
        print("   %s-%-3d %-14s%s" % (canal[0], canal[1], it["id"], extra))
    print("")


# ===========================================================================
def main():
    ap = argparse.ArgumentParser(description="Tablero didáctico Sikorsky S-55 H-08")
    ap.add_argument("--simulado", action="store_true",
                    help="sin hardware: sólo la página web")
    ap.add_argument("--sin-motores", action="store_true", dest="sin_motores",
                    help="no usar los motores paso a paso")
    ap.add_argument("--banco", action="store_true",
                    help="banco de pruebas: sin motores, sin clave, informa qué "
                         "instrumento hace cada servo")
    ap.add_argument("--puerto", type=int, default=8000)
    ap.add_argument("--semilla", type=int, default=20250819,
                    help="semilla del ruido de las agujas")
    ap.add_argument("--sin-clave", action="store_true", dest="sin_clave",
                    help="cualquiera que abra la página puede operar "
                         "(sólo para probar en una computadora propia)")
    ap.add_argument("--renovar-clave", action="store_true", dest="renovar",
                    help="genera una clave de administrador nueva y sale")
    ap.add_argument("--qr-admin", action="store_true", dest="qr_admin",
                    help="muestra el QR del administrador y sale")
    ap.add_argument("--hoja", metavar="ARCHIVO.html",
                    help="con --qr-admin: además escribe una hoja para imprimir")
    args = ap.parse_args()
    # En una consola de Windows los caracteres del QR no entran en su
    # codificación: se reemplazan en vez de cortar el programa.
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    if args.banco:
        args.sin_motores = True
        args.sin_clave = True
    acceso = Acceso(ARCHIVO_CLAVE)

    if args.renovar:
        print("\n  Clave de administrador NUEVA: el QR anterior ya no sirve.\n")
        print(cartel_admin(args.puerto, acceso.renovar_clave()))
        return 0

    if args.qr_admin:
        print(cartel_admin(args.puerto, acceso.clave))
        if args.hoja:
            hoja_admin(args.puerto, acceso.clave, args.hoja)
            print("\n  Hoja para imprimir: %s" % os.path.abspath(args.hoja))
        return 0

    print("=" * 70)
    print(" TABLERO DIDÁCTICO " + AERONAVE["modelo"] + "   " + version())
    print(" Matrícula %s  -  %s" % (AERONAVE["matricula"], AERONAVE["serie"]))
    print("=" * 70)

    actuadores = construir_actuadores(args.simulado, not args.sin_motores)

    print(" Salida       : " + actuadores.descripcion())
    if args.banco:
        imprimir_banco(actuadores)
    print(" Instrumentos : %d canales" % len(TABLERO))
    print(" Fallas       : %d   Escenarios: %d" % (len(CATALOGO), len(ESCENARIOS)))
    if getattr(actuadores, "motores", None) is not None:
        print(" Paso a paso  : 28BYJ-48, %.2f pasos por vuelta, hasta %d pasos/s"
              % (MOTOR_CFG["pasos_por_vuelta"], MOTOR_CFG["vel_max_pps"]))

    nucleo = HiloSimulacion(actuadores, semilla=args.semilla)
    nucleo.start()

    servidor = servidor_web.crear(nucleo, args.puerto, os.path.join(AQUI, "web"),
                                  donde="la Raspberry",
                                  acceso=None if args.sin_clave else acceso)
    print(servidor_web.cartel_de_acceso(args.puerto, ancho=70))
    if args.sin_clave:
        print("\n  ATENCIÓN: --sin-clave. Cualquiera que abra la página puede operar.")
    else:
        print("\n  Para mirar : la dirección de arriba, sin clave.")
        print("  Para operar: el QR del administrador (python3 tablero_pi5.py --qr-admin)")

    # systemd detiene el servicio con SIGTERM: se lo trata igual que Ctrl+C
    # para que el apagado sea siempre ordenado.
    def _parar(_sig, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, _parar)

    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        print("\nApagando el tablero (luces, servos y motores a cero)...")
        servidor.server_close()
        nucleo.detener()
        nucleo.join(timeout=12.0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
