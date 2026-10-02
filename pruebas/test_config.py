# -*- coding: utf-8 -*-
"""h08/config dividido por tema: cada nombre en un solo archivo y el panel volcado en el tablero.

    python3 -m unittest pruebas.test_config -v
"""
import ast
import importlib
import os
import unittest

import h08.config as C
from pruebas.comun import RAIZ, Prueba, leer

TEMAS = ("aeronave", "tablero", "mecanica", "hardware", "panel")


class LaConfiguracion(Prueba):

    def setUp(self):
        self.modulos = dict((t, importlib.import_module("h08.config." + t)) for t in TEMAS)

    def test_cada_nombre_en_un_solo_lugar(self):
        """Cada nombre vive en UN archivo de tema y h08.config da ese mismo objeto."""
        duenos = dict((n, [t for t, m in self.modulos.items() if n in vars(m)])
                      for n in C.__all__)
        repetidos = dict((n, d) for n, d in duenos.items() if len(d) != 1)
        self.comprobar("cada nombre de h08.config está en un solo archivo de tema",
                       not repetidos, repetidos)
        distintos = [n for n, d in duenos.items()
                     if len(d) == 1 and getattr(C, n) is not getattr(self.modulos[d[0]], n)]
        self.comprobar("h08.config reexporta el mismo objeto, no una copia", not distintos,
                       distintos)

    def test_lo_que_se_importa_existe(self):
        """Todo lo que el programa y las pruebas importan de h08.config está en __all__."""
        pedidos = set()
        for carpeta in ("h08", "pruebas"):
            for base, dirs, fs in os.walk(os.path.join(RAIZ, carpeta)):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for f in fs:
                    if not f.endswith(".py"):
                        continue
                    arbol = ast.parse(leer(os.path.join(base, f)))
                    for nodo in ast.walk(arbol):
                        if isinstance(nodo, ast.ImportFrom) and nodo.module == "h08.config":
                            pedidos.update(a.name for a in nodo.names)
        faltan = sorted(n for n in pedidos if n not in C.__all__)
        self.comprobar("los %d nombres que se importan de h08.config están en __all__"
                       % len(pedidos), not faltan, faltan)

    def test_config_no_depende_del_programa(self):
        """config/ sólo importa de config/ y de la biblioteca estándar."""
        ajenos = []
        for t in TEMAS:
            arbol = ast.parse(leer(self.modulos[t].__file__))
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.ImportFrom) and nodo.module \
                        and nodo.module.startswith("h08") \
                        and not nodo.module.startswith("h08.config"):
                    ajenos.append("%s: %s" % (t, nodo.module))
        self.comprobar("config/ sólo importa de config/ y de la biblioteca estándar",
                       not ajenos, ajenos)

    def test_el_panel_quedo_volcado(self):
        """Cada instrumento dibujable y cada luz traen sus datos de la página."""
        sin_panel = [it["id"] for it in list(C.TABLERO) + C.PANEL_VIRTUAL
                     if it["id"] in C.PANEL
                     and not all(k in it for k in ("pos", "tam", "dial", "desc"))]
        sin_luz = [a["id"] for a in C.ANUNCIADOR
                   if C.TABLERO_POR_ID[a["id"]].get("dial") != "luz"
                   or C.TABLERO_POR_ID[a["id"]].get("leyenda") != a["leyenda"]]
        self.comprobar("cada instrumento dibujable trae pos, tamaño, esfera y descripción",
                       not sin_panel, sin_panel)
        self.comprobar("cada luz trae su leyenda del anunciador", not sin_luz, sin_luz)


if __name__ == "__main__":
    unittest.main()
