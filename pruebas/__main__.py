# -*- coding: utf-8 -*-
"""
python3 -m pruebas - todas las pruebas automáticas, sin hardware
================================================================

    python3 -m pruebas              todas (un par de minutos)
    python3 -m pruebas --rapido     sin las lentas: vuelo completo, tablero en
                                    marcha y pruebas guiadas
    python3 -m pruebas --detalle    además, el resultado de cada prueba
    python3 -m unittest -v          lo mismo con el comando estándar de Python

Se corre desde la carpeta del proyecto, igual en la computadora que en la
Raspberry. Termina con «Todas bien.» o con lo que falló y por qué.

    test_vuelo      el simulador: vuelo normal, 8 escenarios, 24 fallas,
                    tablas de calibración y rendimiento
    test_hardware   PCA9685 y motores contra réplicas de mentira
    test_servidor   la página: el visitante mira y no puede operar
    test_acceso     claves, sesiones y turno del mando
    test_qr         los códigos QR se leen (si está instalado OpenCV)
    test_luces      cada falla enciende su luz, prueba de lámparas
    test_web        carátulas, QR del wifi, catálogo y kiosco
    test_rutas      dónde está cada archivo y la mudanza a datos/
    test_config     h08/config por tema, sin nombres repetidos
    test_comando    python3 -m h08 y las pruebas guiadas en modo simulado
    test_deploy     los scripts de la Pi
"""
import argparse
import os
import sys
import time
import unittest

AQUI = os.path.dirname(os.path.abspath(__file__))


class Resultado(unittest.TestResult):
    """Junta lo que pasó en cada prueba para contarlo en castellano."""

    def __init__(self, detalle):
        super().__init__()
        self.detalle = detalle
        self.buffer = True                # lo que imprima el programa sólo se ve si falla

    def stopTest(self, prueba):
        super().stopTest(prueba)
        if self.detalle:
            print("      %s" % _describir(prueba))


def _describir(prueba):
    return prueba.shortDescription() or prueba.id().split(".")[-1]


def _nombre_del_fallo(prueba):
    """La descripción de la prueba y, si es una comprobación con nombre, ese nombre."""
    madre = getattr(prueba, "test_case", None)
    if madre is not None:                 # un subTest: la comprobación que falló
        return "%s  ->  %s" % (_describir(madre), prueba._subDescription().strip("[] ()"))
    return _describir(prueba)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m pruebas",
                                 description="Pruebas automáticas del tablero H-08")
    ap.add_argument("--rapido", action="store_true",
                    help="saltea las pruebas lentas (vuelo completo, en marcha, guiadas)")
    ap.add_argument("--detalle", action="store_true", help="muestra cada prueba")
    a = ap.parse_args(argv)
    if a.rapido:
        os.environ["H08_RAPIDO"] = "1"
    for flujo in (sys.stdout, sys.stderr):
        try:
            flujo.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass

    archivos = sorted(f[:-3] for f in os.listdir(AQUI)
                      if f.startswith("test_") and f.endswith(".py"))
    cargador = unittest.TestLoader()
    fallos, salteadas, total, t_total = [], [], 0, time.monotonic()
    print("=" * 70)
    for nombre in archivos:
        suite = cargador.loadTestsFromName("pruebas." + nombre)
        r = Resultado(a.detalle)
        t0 = time.monotonic()
        suite.run(r)
        total += r.testsRun
        malos = r.failures + r.errors
        fallos += [(nombre, p, traza) for p, traza in malos]
        salteadas += [(nombre, p, motivo) for p, motivo in r.skipped]
        extra = ", %d salteada%s" % (len(r.skipped), "s" if len(r.skipped) > 1 else "") \
            if r.skipped else ""
        print("  %-18s %-6s %2d pruebas%s   (%.0f s)"
              % (nombre, "OK" if not malos else "FALLÓ", r.testsRun, extra,
                 time.monotonic() - t0))
    print("=" * 70)
    for nombre, p, motivo in salteadas:
        print("  salteada: %s · %s (%s)" % (nombre, _describir(p), motivo))
    for nombre, p, traza in fallos:
        print("\n  FALLÓ en %s: %s" % (nombre, _nombre_del_fallo(p)))
        print("    " + traza.strip().replace("\n", "\n    "))
    print("\n %d pruebas en %.0f s" % (total, time.monotonic() - t_total))
    print(" Todas bien." if not fallos else " Fallaron %d." % len(fallos))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
