# -*- coding: utf-8 -*-
"""Dónde están los archivos (h08/rutas.py) y la mudanza de raspberry_pi5/ a datos/.

    python3 -m unittest pruebas.test_rutas -v

Todo lo que se muda son archivos de mentira en carpetas temporales: los datos
reales del tablero no se tocan.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

from h08 import rutas
from pruebas.comun import ENV, RAIZ, Prueba, escribir, leer, mismas, rutas_con


class LasRutas(Prueba):

    def test_rutas_por_defecto(self):
        """Sin variables, cada archivo está donde lo dice CONTEXTO_PROYECTO.md."""
        datos = os.path.join(RAIZ, "datos")
        esperadas = {
            "RAIZ": RAIZ,
            "VERSION": os.path.join(RAIZ, "VERSION.txt"),
            "DATOS": datos,
            "CLAVE": os.path.join(datos, "secreto_admin.json"),
            "CALIBRACION": os.path.join(datos, "calibracion_servos.json"),
            "MOTORES": os.path.join(datos, "posicion_motores.json"),
            "INFORMES": os.path.join(datos, "informes"),
            "VIEJA": os.path.join(RAIZ, "raspberry_pi5"),
            "ESTATICOS": os.path.join(RAIZ, "h08", "web", "static"),
            "PUNTO_DE_ACCESO": os.path.join(RAIZ, "deploy", "punto_de_acceso.sh"),
        }
        reales = rutas_con()
        for nombre, ruta in esperadas.items():
            self.comprobar("rutas.%s = %s" % (nombre, os.path.relpath(ruta, RAIZ)),
                           nombre in reales and mismas(reales[nombre], ruta),
                           reales.get(nombre, reales))
        self.comprobar("la página y el script de la red están donde dice rutas.py",
                       os.path.isfile(os.path.join(rutas.ESTATICOS, "tablero.html"))
                       and os.path.isfile(rutas.PUNTO_DE_ACCESO))

    def test_variables_de_entorno(self):
        """H08_DATOS aísla los datos y apaga la mudanza; H08_INFORMES mueve sólo los informes."""
        otra = tempfile.mkdtemp(prefix="h08_datos_")
        con = rutas_con(H08_DATOS=otra)
        self.comprobar("H08_DATOS mueve la clave, la calibración, el motor y los informes",
                       all(mismas(os.path.dirname(con[k]), otra)
                           for k in ("CLAVE", "CALIBRACION", "MOTORES", "INFORMES")), con)
        self.comprobar("con H08_DATOS no hay mudanza desde raspberry_pi5/",
                       con.get("VIEJA", 1) is None, con)
        inf = tempfile.mkdtemp(prefix="h08_inf_")
        self.comprobar("H08_INFORMES cambia sólo la carpeta de informes",
                       mismas(rutas_con(H08_INFORMES=inf)["INFORMES"], inf))

    def test_nadie_arma_rutas_por_su_cuenta(self):
        """Sólo rutas.py nombra los archivos de datos, y nadie toca sys.path."""
        propios = re.compile(r"""["'](secreto_admin|calibracion_servos|posicion_motores)\.json["']"""
                             r"""|["']VERSION\.txt["']|["']informes["']|sys\.path\.insert""")
        culpables = []
        for base, dirs, fs in os.walk(os.path.join(RAIZ, "h08")):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for f in fs:
                ruta = os.path.join(base, f)
                if f.endswith(".py") and not mismas(ruta, rutas.__file__):
                    if propios.search(leer(ruta)):
                        culpables.append(os.path.relpath(ruta, RAIZ))
        self.comprobar("sólo rutas.py nombra los archivos de datos (y nadie toca sys.path)",
                       not culpables, culpables)


class LaMudanza(Prueba):
    """raspberry_pi5/ -> datos/, con archivos de mentira en una carpeta temporal."""

    def setUp(self):
        self.base = tempfile.mkdtemp(prefix="h08_mudanza_")
        self.vieja = os.path.join(self.base, "raspberry_pi5")
        self.nueva = os.path.join(self.base, "datos")

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def test_mudanza(self):
        """Pasa todo sin pisar nada, avisa cada cosa y la segunda vez no hace nada."""
        vieja, nueva = self.vieja, self.nueva
        for n in rutas.PRIVADOS:
            escribir(os.path.join(vieja, n), "de mentira: " + n)
        escribir(os.path.join(vieja, "informes", "uno.txt"), "informe 1")
        avisos = []
        conflictos = rutas.migrar_datos_viejos(vieja, nueva, avisos.append)
        self.comprobar("pasa los tres archivos y los informes",
                       all(leer(os.path.join(nueva, n)) == "de mentira: " + n
                           for n in rutas.PRIVADOS)
                       and leer(os.path.join(nueva, "informes", "uno.txt")) == "informe 1",
                       os.listdir(nueva))
        self.comprobar("avisa cada cosa que mueve, sin conflictos",
                       len(avisos) == 4 and not conflictos, avisos)
        self.comprobar("borra raspberry_pi5/ porque quedó vacía",
                       not os.path.exists(vieja) and rutas.datos_viejos(vieja) == [])
        avisos = []
        self.comprobar("la segunda vez no hace nada",
                       rutas.migrar_datos_viejos(vieja, nueva, avisos.append) == []
                       and not avisos, avisos)

        # Los dos lados con datos: no se pisa nada y decide una persona.
        escribir(os.path.join(vieja, "secreto_admin.json"), "la vieja")
        escribir(os.path.join(vieja, "informes", "uno.txt"), "otro informe 1")
        escribir(os.path.join(vieja, "informes", "dos.txt"), "informe 2")
        avisos = []
        conflictos = rutas.migrar_datos_viejos(vieja, nueva, avisos.append)
        self.comprobar("con la clave en los dos lados, no pisa la de datos/",
                       leer(os.path.join(nueva, "secreto_admin.json"))
                       == "de mentira: secreto_admin.json"
                       and leer(os.path.join(vieja, "secreto_admin.json")) == "la vieja")
        self.comprobar("informes: pasa los que faltan y deja los repetidos",
                       leer(os.path.join(nueva, "informes", "dos.txt")) == "informe 2"
                       and leer(os.path.join(nueva, "informes", "uno.txt")) == "informe 1"
                       and os.path.exists(os.path.join(vieja, "informes", "uno.txt")))
        self.comprobar("devuelve y avisa los dos conflictos", len(conflictos) == 2
                       and sum("sin mover" in a for a in avisos) == 2, (conflictos, avisos))
        self.comprobar("el diagnóstico ve lo que quedó en raspberry_pi5/",
                       rutas.datos_viejos(vieja) == ["secreto_admin.json", "informes"],
                       rutas.datos_viejos(vieja))

    def test_de_punta_a_punta(self):
        """Una copia del programa con datos viejos arranca y usa la clave que estaba."""
        copia = os.path.join(self.base, "H08_Pi5")
        shutil.copytree(os.path.join(RAIZ, "h08"), os.path.join(copia, "h08"),
                        ignore=shutil.ignore_patterns("__pycache__"))
        clave = "claveDeMentira1234567"
        escribir(os.path.join(copia, "raspberry_pi5", "secreto_admin.json"),
                 json.dumps({"clave": clave}))
        sin = dict(ENV)
        sin.pop("H08_DATOS", None)
        r = subprocess.run([sys.executable, "-m", "h08", "--qr-admin"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace", env=sin, cwd=copia,
                           timeout=60)
        movida = os.path.join(copia, "datos", "secreto_admin.json")
        self.comprobar("al arrancar, la clave vieja pasa a datos/ y se usa (no se hace otra)",
                       r.returncode == 0 and clave in r.stdout and os.path.isfile(movida)
                       and json.loads(leer(movida))["clave"] == clave
                       and not os.path.exists(os.path.join(copia, "raspberry_pi5")),
                       (r.stdout + r.stderr)[-400:])
        nada = os.path.join(self.base, "no_existe")
        r = subprocess.run([sys.executable, "-m", "h08", "--help"], capture_output=True,
                           text=True, env=dict(sin, H08_DATOS=nada), cwd=copia, timeout=60)
        self.comprobar("python3 -m h08 --help no crea ni mueve datos",
                       r.returncode == 0 and not os.path.exists(nada)
                       and os.path.isfile(movida))

        # Con H08_DATOS (pruebas, PC de desarrollo) la clave de raspberry_pi5/ no se toca.
        quieta = os.path.join(copia, "raspberry_pi5", "secreto_admin.json")
        escribir(quieta, json.dumps({"clave": "otraClaveDeMentira99"}))
        aparte = os.path.join(self.base, "aparte")
        r = subprocess.run([sys.executable, "-m", "h08", "--qr-admin"], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           env=dict(sin, H08_DATOS=aparte), cwd=copia, timeout=60)
        self.comprobar("con H08_DATOS, la clave de raspberry_pi5/ queda donde está",
                       r.returncode == 0 and os.path.isfile(quieta)
                       and json.loads(leer(quieta))["clave"] == "otraClaveDeMentira99"
                       and os.path.isfile(os.path.join(aparte, "secreto_admin.json"))
                       and "otraClaveDeMentira99" not in r.stdout, (r.stdout + r.stderr)[-300:])


if __name__ == "__main__":
    unittest.main()
