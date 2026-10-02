# -*- coding: utf-8 -*-
"""Las luces de alerta: cada falla enciende la suya, la prueba de lámparas y el corte eléctrico.

    python3 -m unittest pruebas.test_luces -v
"""
import unittest

from h08.config import TABLERO, LED
from h08.hardware.simulado import ActuadoresSimulados
from h08.simulacion.simulador import Simulador
from pruebas.comun import Prueba


def correr(sim, seg, dt=0.05):
    for _ in range(int(seg / dt)):
        sim.paso(dt)
        sim.mapa.escribir()


def luces_encendidas(sim):
    e = sim.estado()["instrumentos"]
    return set(it["id"] for it in TABLERO if it["actuador"] == LED and e[it["id"]]["ang"] >= 0.5)


class LasLucesDeAlerta(Prueba):

    def test_cada_falla_enciende_su_luz(self):
        """Generador, transmisión, rotor bajo y combustible encienden su luz a tiempo."""
        for falla, luz, seg in (("GEN_FAIL", "LT_GEN", 10), ("XMSN_PRESS_LOSS", "LT_XMSN_PRESS", 40),
                                ("LOW_ROTOR_RPM", "LT_LOW_ROTOR", 80),
                                ("FUEL_STARVATION", "LT_FUEL_FWD", 10)):
            sim = Simulador(ActuadoresSimulados(), semilla=1)
            sim.modo_falla(falla)
            vista = False
            for _ in range(int(seg / 1.0)):
                correr(sim, 1.0)
                if luz in luces_encendidas(sim):
                    vista = True
                    break
            self.comprobar("%s enciende %s antes de %d s" % (falla, luz, seg), vista)

    def test_crucero_y_prueba_de_lamparas(self):
        """En crucero sólo IGNITION; la prueba de lámparas enciende las seis y vuelve."""
        sim = Simulador(ActuadoresSimulados(), semilla=1)
        sim.modo_falla("PITOT_BLOCK")           # crucero; la falla no toca luces
        correr(sim, 20)
        self.comprobar("crucero: sólo IGNITION encendida", luces_encendidas(sim) == {"LT_STARTER"},
                       luces_encendidas(sim))

        sim.prueba_luces(True)
        correr(sim, 0.2)
        self.comprobar("prueba de lámparas: la página ve las seis", len(luces_encendidas(sim)) == 6)
        act = sim.mapa.actuadores
        self.comprobar("prueba de lámparas: las seis salidas encendidas",
                       all(act.valores.get("%s:%d" % tuple(it["canal"])) == 1
                           for it in TABLERO if it["actuador"] == LED))
        sim.prueba_luces(False)
        correr(sim, 0.2)
        self.comprobar("fin de la prueba: vuelve a sólo IGNITION",
                       luces_encendidas(sim) == {"LT_STARTER"})

    def test_sin_energia_electrica(self):
        """Sin barra eléctrica se apagan todas, aunque la alarma siga."""
        sim = Simulador(ActuadoresSimulados(), semilla=1)
        sim.modo_falla("ELEC_TOTAL")
        correr(sim, 120)
        self.comprobar("sin energía eléctrica: todas apagadas", luces_encendidas(sim) == set(),
                       luces_encendidas(sim))


if __name__ == "__main__":
    unittest.main()
