# -*- coding: utf-8 -*-
"""El tablero H-08 en datos: todo número del proyecto vive en este paquete.

Cada tema tiene su archivo y acá se reexportan todos los nombres, así el resto
del programa importa siempre de h08.config:

    aeronave.py   identidad y límites físicos del H-19A (AERONAVE, LIM)
    tablero.py    los 30 instrumentos: escala, tabla cal y canal (TABLERO)
    mecanica.py   barrido de cada aguja, engranajes y el horizonte
    hardware.py   lazo, arranque escalonado, placas PCA9685, servos, luces y motor
    panel.py      geometría y textos de la página web

El tablero se recalibra editando estos archivos, sin tocar la lógica.
"""

from h08.config.aeronave import AERONAVE, LIM
from h08.config.tablero import SERVO, MOTOR, LED, TABLERO, TABLERO_POR_ID
from h08.config.mecanica import (BARRIDO, CENTRO_ESCALA, ENGRANAJES, MODULO_ENGRANAJE,
                                 HORIZONTE, reduccion, invertido, factor_servo)
from h08.config.hardware import (LAZO, ARRANQUE, I2C_BUS, PLACAS, SERVO_CFG,
                                 LUCES_ACTIVAS_EN_BAJO, MOTOR_CFG, MOTORES)
from h08.config.panel import (PANEL_LIENZO, PANEL_ZONAS, PANEL, PANEL_VIRTUAL, ANUNCIADOR,
                              PANEL_CONMUTADORES, PANEL_PLACAS)

__all__ = [
    "AERONAVE", "LIM",
    "SERVO", "MOTOR", "LED", "TABLERO", "TABLERO_POR_ID",
    "BARRIDO", "CENTRO_ESCALA", "ENGRANAJES", "MODULO_ENGRANAJE", "HORIZONTE",
    "reduccion", "invertido", "factor_servo",
    "LAZO", "ARRANQUE", "I2C_BUS", "PLACAS", "SERVO_CFG", "LUCES_ACTIVAS_EN_BAJO",
    "MOTOR_CFG", "MOTORES",
    "PANEL_LIENZO", "PANEL_ZONAS", "PANEL", "PANEL_VIRTUAL", "ANUNCIADOR",
    "PANEL_CONMUTADORES", "PANEL_PLACAS",
]


def _volcar_panel():
    """Copia en cada instrumento su lugar, su esfera y su texto de la página."""
    for it in list(TABLERO) + PANEL_VIRTUAL:
        p = PANEL.get(it["id"])
        if p:
            it["desc"] = p["desc"]
            it["zona"] = p["zona"]
            it["dial"] = p["dial"]
            it["pos"] = p["pos"]
            it["tam"] = p["tam"]
    for a in ANUNCIADOR:
        t = TABLERO_POR_ID.get(a["id"])
        if t:
            t["desc"] = a["desc"]
            t["leyenda"] = a["leyenda"]
            t["dial"] = "luz"


_volcar_panel()
