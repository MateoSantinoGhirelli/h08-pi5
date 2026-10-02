# -*- coding: utf-8 -*-
"""Los scripts de la Pi (deploy/): sintaxis de bash, instalar.sh y actualizar.sh.

    python3 -m unittest pruebas.test_deploy -v
"""
import os
import re
import subprocess
import tempfile
import unittest

from pruebas.comun import RAIZ, Prueba, escribir, leer, mismas, rutas_con

DEPLOY = os.path.join(RAIZ, "deploy")
SCRIPTS = sorted(f for f in os.listdir(DEPLOY) if f.endswith(".sh"))


class LaSintaxis(Prueba):

    # En Windows el "bash" que aparece suele ser el de WSL o el de Git, que no
    # entienden las rutas C:\...: la sintaxis se comprueba en Linux o en la Pi.
    @unittest.skipIf(os.name == "nt", "la sintaxis de bash se comprueba en Linux")
    def test_bash_n(self):
        """bash -n no encuentra errores de sintaxis en ningún .sh."""
        for sh in SCRIPTS:
            try:
                r = subprocess.run(["bash", "-n", os.path.join(DEPLOY, sh)],
                                   capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=30)
            except (OSError, subprocess.SubprocessError):
                self.skipTest("sin bash en este sistema")
            self.comprobar("%s sin errores de sintaxis" % sh, r.returncode == 0, r.stderr)


class Instalar(Prueba):

    def setUp(self):
        self.texto = leer(os.path.join(DEPLOY, "instalar.sh"))

    def test_instalar(self):
        """Deja kiosco, inicio solo y red propia; servicio con -m h08; limpia lo viejo."""
        texto = self.texto
        self.comprobar("instalar.sh deja el kiosco, el inicio solo y la red propia",
                       all(k in texto for k in ("kiosco.sh", "do_boot_behaviour B4",
                                                "do_blanking 1",
                                                "punto_de_acceso.sh\" preparar")))
        self.comprobar("instalar.sh escribe el servicio con python3 -m h08 desde la raíz",
                       "ExecStart=/usr/bin/python3 -m h08\n" in texto
                       and "WorkingDirectory=$RAIZ\n" in texto and "tablero_pi5" not in texto)
        self.comprobar("instalar.sh limpia el kiosco y el servicio de la versión vieja",
                       all(k in texto for k in ("sed -i '/kiosco\\.sh/d' \"$LABWC\"",
                                                "rm -f \"$AUTOSTART\"",
                                                "sudo systemctl stop \"$SERVICIO\"")))
        m = re.search(r'^DATOS="\$RAIZ/([^"]+)"', texto, re.M)
        self.comprobar("instalar.sh protege la clave en la misma carpeta que rutas.DATOS",
                       m is not None and mismas(os.path.join(RAIZ, m.group(1)),
                                                rutas_con()["DATOS"]))


class Actualizar(Prueba):

    def test_actualizar(self):
        """No pisa los datos del tablero, borra lo viejo y reconoce el paquete nuevo."""
        act = leer(os.path.join(DEPLOY, "actualizar.sh"))
        self.comprobar("actualizar.sh no pisa la clave, la calibración ni el motor",
                       all(re.search(r"--exclude '%s'" % re.escape(n), act)
                           for n in ("secreto_admin.json", "calibracion_servos.json",
                                     "posicion_motores.json")))
        self.comprobar("actualizar.sh borra lo viejo (--delete) sin tocar datos/ ni raspberry_pi5/",
                       "rsync -a --delete" in act and "--exclude '/datos/'" in act
                       and "--exclude '/raspberry_pi5/'" in act)
        self.comprobar("actualizar.sh reconoce el paquete nuevo por h08/__main__.py",
                       "h08/__main__.py" in act and "tablero_pi5" not in act)
        self.comprobar("actualizar.sh no copia la carpeta instalada sobre sí misma",
                       '[ "$NUEVO" = "$RAIZ" ]' in act and '[ -n "$PRINCIPAL" ]' in act)

    # Los dos casos salen antes del respaldo y de parar el servicio: en la Pi no se
    # toca nada. Se saltea donde actualizar.sh no llega hasta ahí (sin el servicio).
    @unittest.skipIf(os.name == "nt", "actualizar.sh se corre en Linux")
    def test_rechaza_lo_que_no_es_el_paquete(self):
        """Un paquete sin h08/__main__.py, o la carpeta instalada, se rechazan."""
        with tempfile.TemporaryDirectory() as vacio:
            escribir(os.path.join(vacio, "leeme.txt"), "no es el programa")
            for origen, aviso in ((vacio, "no es un paquete de la versión nueva"),
                                  (RAIZ, "es la carpeta que ya está instalada")):
                try:
                    r = subprocess.run(["bash", os.path.join(DEPLOY, "actualizar.sh"), origen],
                                       capture_output=True, text=True, encoding="utf-8",
                                       errors="replace", timeout=60, cwd=RAIZ)
                except (OSError, subprocess.SubprocessError):
                    self.skipTest("sin bash en este sistema")
                if "no está instalado" in r.stdout or "Falta" in r.stdout:
                    self.skipTest("el servicio no está instalado en esta máquina")
                self.comprobar("actualizar.sh rechaza %s" % origen,
                               r.returncode == 1 and aviso in r.stdout, r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
