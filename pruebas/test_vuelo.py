# -*- coding: utf-8 -*-
"""
test_vuelo.py - el simulador completo, sin hardware
===================================================

    python3 -m unittest pruebas.test_vuelo -v

Corre el vuelo normal entero, los 8 escenarios y las 24 fallas del catálogo
sobre salidas simuladas, y revisa que las tablas de calibración de cada
instrumento sean válidas. Es la prueba de integración: valida la lógica antes
de tocar el hardware.
"""

import time
import unittest

from h08.util import interpolar_tabla
from h08.config import TABLERO, TABLERO_POR_ID
from h08.hardware.simulado import ActuadoresSimulados
from h08.simulacion.simulador import Simulador, MODO_DETENIDO
from h08.simulacion.fallas import CATALOGO
from h08.simulacion.escenarios import ESCENARIOS, PERFIL_NORMAL
from pruebas.comun import Prueba, lenta

DT = 1.0 / 20.0


def correr(sim, segundos):
    for _ in range(int(segundos / DT)):
        sim.paso(DT)
        sim.mapa.escribir()
        if sim.modo == MODO_DETENIDO:
            break


@lenta
class ElVuelo(Prueba):

    def test_vuelo_normal_completo(self):
        """El perfil de vuelo normal corre entero, de la aeronave fría al corte."""
        sim = Simulador(ActuadoresSimulados(), semilla=1234)
        sim.ciclar = False
        sim.modo_normal()
        correr(sim, sum(f["dur"] for f in PERFIL_NORMAL) + 10)

    def test_los_escenarios(self):
        """Cada escenario de emergencia corre hasta su final sin errores."""
        for e in ESCENARIOS:
            with self.subTest(e["id"]):
                sim = Simulador(ActuadoresSimulados(), semilla=777)
                sim.modo_escenario(e["id"])
                correr(sim, e["duracion"] + 5)

    def test_las_fallas(self):
        """Cada falla del catálogo corre 90 s sobre el crucero sin errores."""
        for f in CATALOGO:
            with self.subTest(f["id"]):
                sim = Simulador(ActuadoresSimulados(), semilla=42)
                sim.modo_falla(f["id"])
                # 2 s antes, para que el bus de señales se llene y los filtros
                # arranquen desde el valor de crucero
                for _ in range(int(2.0 / DT)):
                    sim.paso(DT)
                for _ in range(int(90.0 / DT)):
                    sim.paso(DT)
                    sim.mapa.escribir()


class LasTablasDeCalibracion(Prueba):

    def test_cada_tabla(self):
        """Ordenada, cubre la escala, no se sale del recorrido y la aguja nunca retrocede."""
        for it in TABLERO:
            cal = it["cal"]
            vmin, vmax = it["escala"]
            with self.subTest(it["id"]):
                self.assertTrue(all(cal[i][0] > cal[i - 1][0] for i in range(1, len(cal))),
                                "tabla desordenada en x")
                self.assertLessEqual(cal[0][0], vmin + 1e-6, "no cubre el mínimo (%.1f)" % vmin)
                self.assertGreaterEqual(cal[-1][0], vmax - 1e-6,
                                        "no cubre el máximo (%.1f)" % vmax)
                # Los motores de giro continuo no tienen tope: la escala llega a
                # 360 y sigue. Los servos SI: su recorrido útil es el barrido de
                # la esfera o 180, lo que sea menor, porque de 180 para arriba
                # trabajan los engranajes de la reducción.
                if it["actuador"] == "MOTOR":
                    tope = 360.0
                elif "LED" in it["actuador"]:
                    tope = 1.0
                else:
                    tope = 180.0
                angulos = [c[1] for c in cal]
                self.assertTrue(min(angulos) >= -0.01 and max(angulos) <= tope + 0.01,
                                "ángulo fuera de 0..%.0f" % tope)
                # monótona: si no, la aguja retrocedería
                saltos = [cal[i][1] - cal[i - 1][1] for i in range(1, len(cal))]
                signos = set(1 if d > 0 else -1 for d in saltos if d != 0)
                self.assertLessEqual(len(signos), 1, "no monótona: la aguja retrocede")

    def test_tacometro_doble(self):
        """Las agujas de motor y rotor se superponen con la relación 10:1."""
        te = TABLERO_POR_ID["TACH_ENG"]["cal"]
        tr = TABLERO_POR_ID["TACH_ROT"]["cal"]
        peor = max(abs(interpolar_tabla(rpm, te) - interpolar_tabla(rpm / 10.0, tr))
                   for rpm in (0, 500, 1000, 1400, 2000, 2200, 2400, 3000, 3500))
        self.assertLessEqual(peor, 0.5, "las agujas no se superponen (diferencia máxima "
                                        "%.2f grados)" % peor)


class ElRendimiento(Prueba):

    def test_entra_en_el_presupuesto(self):
        """Un paso de simulación tarda mucho menos que los 50 ms que tiene a 20 Hz."""
        sim = Simulador(ActuadoresSimulados(), semilla=1)
        sim._preparar_crucero()
        sim.modo = 3
        n = 20000
        t0 = time.perf_counter()
        for _ in range(n):
            sim.paso(DT)
        us = (time.perf_counter() - t0) / n * 1e6
        self.assertLess(us, 50000.0, "%.0f us por paso" % us)


if __name__ == "__main__":
    unittest.main()
