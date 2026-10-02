# -*- coding: utf-8 -*-
"""Que la documentación de la raíz exista, no mienta la versión y viaje en el zip.

    python3 -m unittest pruebas.test_documentacion -v
"""
import os
import re
import unittest

import empaquetar
from h08 import __version__
from pruebas.comun import RAIZ, Prueba, leer


def version_de_pyproject():
    """La version del [project] de pyproject.toml, sin depender de tomllib (es 3.11+)."""
    texto = leer(os.path.join(RAIZ, "pyproject.toml"))
    try:
        import tomllib
        return tomllib.loads(texto)["project"]["version"]
    except ImportError:
        m = re.search(r'(?m)^\s*version\s*=\s*"([^"]+)"', texto)
        return m.group(1) if m else None


class LaDocumentacion(Prueba):

    def test_estan_los_documentos(self):
        """README, CHANGELOG, pyproject y LEEME están en la raíz."""
        for nombre in ("README.md", "CHANGELOG.md", "pyproject.toml", "LEEME.md",
                       "CONTEXTO_PROYECTO.md"):
            self.comprobar("existe %s" % nombre,
                           os.path.isfile(os.path.join(RAIZ, nombre)))

    def test_una_sola_version(self):
        """pyproject.toml y el CHANGELOG no se desincronizan de h08/__init__.py."""
        self.comprobar_igual("pyproject coincide con h08.__version__",
                             version_de_pyproject(), __version__)
        changelog = leer(os.path.join(RAIZ, "CHANGELOG.md"))
        self.comprobar("el CHANGELOG tiene una entrada para la versión actual",
                       ("[%s]" % __version__) in changelog)

    def test_el_zip_lleva_los_documentos(self):
        """empaquetar.py mete README, CHANGELOG y pyproject, y la carpeta docs/."""
        for nombre in ("README.md", "CHANGELOG.md", "pyproject.toml"):
            self.comprobar("el zip lleva %s" % nombre, nombre in empaquetar.SUELTOS)
        self.comprobar("el zip lleva docs/", "docs" in empaquetar.CARPETAS)

    def test_el_readme_nombra_los_comandos(self):
        """El README trae los comandos que usa una persona, sin rutas viejas."""
        readme = leer(os.path.join(RAIZ, "README.md"))
        for comando in ("py -m h08 --simulado", "py -m pruebas", "py empaquetar.py",
                        "bash deploy/instalar.sh"):
            self.comprobar("el README nombra «%s»" % comando, comando in readme)
        for viejo in ("raspberry_pi5/", "nucleo/", "correr_pruebas"):
            self.comprobar_falso("el README no nombra «%s»" % viejo, viejo in readme)


if __name__ == "__main__":
    unittest.main()
