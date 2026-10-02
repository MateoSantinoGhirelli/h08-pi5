# -*- coding: utf-8 -*-
"""Lo que comparten las pruebas: comprobaciones con nombre, la marca de lenta y el comando."""
import json
import os
import subprocess
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Para los procesos hijos (python3 -m h08 ...): UTF-8 siempre, porque en Windows la
# consola usa otra codificación y los acentos y los QR romperían la salida.
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

# python3 -m pruebas --rapido pone H08_RAPIDO y estas se saltean.
lenta = unittest.skipIf(os.environ.get("H08_RAPIDO"), "lenta: se saltea con --rapido")


class Prueba(unittest.TestCase):
    """TestCase con comprobaciones que tienen nombre.

    Cada una es un subTest: si falla, se informa con su nombre y la prueba sigue
    con las demás, como en un control de puesta en marcha.
    """

    def comprobar(self, nombre, condicion, detalle=None):
        with self.subTest(nombre):
            self.assertTrue(condicion, detalle)

    def comprobar_falso(self, nombre, condicion, detalle=None):
        with self.subTest(nombre):
            self.assertFalse(condicion, detalle)

    def comprobar_igual(self, nombre, obtenido, esperado):
        with self.subTest(nombre):
            self.assertEqual(obtenido, esperado)


def correr_h08(args, env=None, timeout=60, cwd=RAIZ):
    """python3 -m h08 ARGS desde la raíz del proyecto, como en la Pi."""
    return subprocess.run([sys.executable, "-m", "h08"] + list(args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout,
                          env=ENV if env is None else env, cwd=cwd)


def rutas_con(**variables):
    """Las rutas que da h08/rutas.py en un proceso nuevo, con esas variables de entorno.

    Sin variables da las rutas reales del tablero: sólo se leen, nunca se escribe ahí.
    """
    env = dict(ENV)
    env.pop("H08_DATOS", None)
    env.pop("H08_INFORMES", None)
    env.update(variables)
    codigo = ("import json; from h08 import rutas; print(json.dumps(dict((k, getattr(rutas, k))"
              " for k in dir(rutas) if k.isupper())))")
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                       env=env, cwd=RAIZ)
    return json.loads(r.stdout) if r.returncode == 0 else {"error": r.stderr}


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def escribir(ruta, texto):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)


def mismas(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))
