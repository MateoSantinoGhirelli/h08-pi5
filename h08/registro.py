# -*- coding: utf-8 -*-
"""El registro del tablero: niveles en castellano y, en el servicio, la prioridad para journald.

Cada módulo anota con logging.getLogger(__name__); acá se decide cómo sale.
Con systemd, cada línea empieza con <N> (la prioridad de syslog): journald la
lee y la saca, y así funciona `journalctl -u tablero-h08 -p warning`.
"""
import logging
import os
import sys

NOMBRES = {logging.DEBUG: "DETALLE", logging.INFO: "INFO", logging.WARNING: "AVISO",
           logging.ERROR: "ERROR", logging.CRITICAL: "GRAVE"}
# Prioridades de syslog que entiende journald (man sd-daemon)
PRIORIDAD = {logging.DEBUG: 7, logging.INFO: 6, logging.WARNING: 4, logging.ERROR: 3,
             logging.CRITICAL: 2}


def bajo_systemd():
    """True si la salida va al journal: systemd define JOURNAL_STREAM en el servicio."""
    return bool(os.environ.get("JOURNAL_STREAM"))


class Formato(logging.Formatter):
    """«AVISO mensaje»; sin hora, porque la pone journald (y la terminal no la necesita)."""

    def __init__(self, para_journald=False):
        super().__init__()
        self.para_journald = para_journald

    def format(self, registro):
        texto = "%s %s" % (NOMBRES.get(registro.levelno, registro.levelname),
                           registro.getMessage())
        if registro.exc_info:
            texto += "\n" + self.formatException(registro.exc_info)
        if self.para_journald:
            # cada renglón con su prioridad: si no, el detalle de un error quedaría como INFO
            prefijo = "<%d>" % PRIORIDAD.get(registro.levelno, 6)
            texto = "\n".join(prefijo + linea for linea in texto.split("\n"))
        return texto


def configurar(nivel=logging.INFO, flujo=None, para_journald=None):
    """Deja el registro de h08 saliendo por la terminal o el journal. Se puede llamar de nuevo."""
    raiz = logging.getLogger("h08")
    for h in [h for h in raiz.handlers if getattr(h, "_h08", False)]:
        raiz.removeHandler(h)
    salida = logging.StreamHandler(flujo or sys.stdout)
    salida.setFormatter(Formato(bajo_systemd() if para_journald is None else para_journald))
    salida._h08 = True
    raiz.addHandler(salida)
    raiz.setLevel(nivel)
    raiz.propagate = False
    return raiz
