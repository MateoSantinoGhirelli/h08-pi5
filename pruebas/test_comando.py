# -*- coding: utf-8 -*-
"""El comando python3 -m h08: su ayuda, cada subcomando y las pruebas guiadas en modo simulado.

    python3 -m unittest pruebas.test_comando -v
"""
import os
import socket
import tempfile
import unittest

from h08.__main__ import SUBCOMANDOS
from pruebas.comun import ENV, Prueba, correr_h08, lenta


class ElComando(Prueba):

    def test_ayuda(self):
        """python3 -m h08 --help lista los subcomandos y cada uno tiene su ayuda."""
        r = correr_h08(["--help"])
        self.comprobar("python3 -m h08 --help lista los %d subcomandos" % len(SUBCOMANDOS),
                       r.returncode == 0 and all(s in r.stdout for s in SUBCOMANDOS),
                       r.stdout + r.stderr)
        for sub in SUBCOMANDOS:
            r = correr_h08([sub, "--help"])
            self.comprobar("python3 -m h08 %s --help" % sub,
                           r.returncode == 0 and ("python3 -m h08 " + sub) in r.stdout,
                           (r.stdout + r.stderr)[-300:])

    def test_puerto_ocupado(self):
        """Con el puerto tomado (el servicio en marcha) se va con un aviso, sin abrir las placas."""
        ocupa = socket.socket()
        ocupa.bind(("0.0.0.0", 0))
        ocupa.listen()
        puerto = ocupa.getsockname()[1]
        try:
            env = dict(ENV, H08_DATOS=tempfile.mkdtemp(prefix="h08_datos_"))
            r = correr_h08(["--simulado", "--puerto", str(puerto)], env=env, timeout=30)
        finally:
            ocupa.close()
        salida = r.stdout + r.stderr
        self.comprobar("sale con 1 y dice que el puerto está ocupado",
                       r.returncode == 1 and "está ocupado" in salida, salida[-400:])
        self.comprobar("sin haber abierto las placas", "salida:" not in salida, salida[-400:])

    def test_tabla_de_cableado(self):
        """python3 -m h08 diagnostico --cableado muestra la tabla de cables."""
        r = correr_h08(["diagnostico", "--cableado"], timeout=30)
        self.comprobar("python3 -m h08 diagnostico --cableado",
                       r.returncode == 0 and "GPIO12" in r.stdout)


@lenta
class LasPruebasGuiadas(Prueba):

    def test_pruebas_guiadas_simuladas(self):
        """Las pruebas guiadas de la Pi corren enteras con --simulado --auto."""
        tmp = tempfile.mkdtemp(prefix="h08_informes_")
        env = dict(ENV, H08_INFORMES=tmp)
        for args in (["instrumento", "AIRSPEED"], ["instrumento", "COMPASS"],
                     ["instrumento", "LT_GEN"], ["luces-motor", "--luces"],
                     ["prueba-general", "--solo", "A"]):
            r = correr_h08(args + ["--simulado", "--auto"], env=env, timeout=240)
            self.comprobar("python3 -m h08 " + " ".join(args),
                           r.returncode == 0 and "TODO BIEN" in r.stdout,
                           (r.stdout + r.stderr)[-400:])
        self.comprobar("los informes van a su carpeta", len(os.listdir(tmp)) == 5,
                       os.listdir(tmp))


if __name__ == "__main__":
    unittest.main()
