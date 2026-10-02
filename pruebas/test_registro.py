# -*- coding: utf-8 -*-
"""El registro (h08/registro.py) y lo que anotan el servicio, la simulación y las placas.

    python3 -m unittest pruebas.test_registro -v
"""
import io
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

from h08 import registro, rutas
from h08.hardware import pca9685 as P
from h08.hardware.simulado import ActuadoresSimulados
from h08.simulacion.hilo import HiloSimulacion
from h08.web import servidor as servidor_web
from pruebas.comun import ENV, RAIZ, Prueba, escribir


class ConRegistroPropio(Prueba):
    """Deja el logger «h08» como estaba al terminar cada prueba."""

    def setUp(self):
        raiz = logging.getLogger("h08")
        self._antes = (list(raiz.handlers), raiz.level, raiz.propagate)

    def tearDown(self):
        raiz = logging.getLogger("h08")
        raiz.handlers[:], raiz.level, raiz.propagate = self._antes

    def salida(self, para_journald):
        flujo = io.StringIO()
        registro.configurar(flujo=flujo, para_journald=para_journald)
        return flujo


class ElFormato(ConRegistroPropio):

    def test_niveles_en_castellano(self):
        """Cada línea dice su nivel en castellano y el mensaje, sin hora."""
        flujo = self.salida(False)
        log = logging.getLogger("h08.prueba")
        log.info("arrancó")
        log.warning("una placa no responde")
        log.error("algo falló")
        self.comprobar_igual("INFO, AVISO y ERROR, una línea cada uno",
                             flujo.getvalue().splitlines(),
                             ["INFO arrancó", "AVISO una placa no responde", "ERROR algo falló"])

    def test_prioridad_para_journald(self):
        """En el servicio cada renglón empieza con su prioridad, también el detalle de un error."""
        flujo = self.salida(True)
        log = logging.getLogger("h08.prueba")
        log.info("arrancó")
        try:
            raise RuntimeError("de mentira")
        except RuntimeError:
            log.exception("error en el lazo")
        lineas = flujo.getvalue().splitlines()
        self.comprobar_igual("INFO lleva <6>", lineas[0], "<6>INFO arrancó")
        self.comprobar("el error y cada renglón de su detalle llevan <3>",
                       len(lineas) > 2 and all(l.startswith("<3>") for l in lineas[1:]), lineas)
        self.comprobar("el detalle incluye la excepción",
                       any("RuntimeError: de mentira" in l for l in lineas), lineas)

    def test_sabe_si_corre_como_servicio(self):
        """systemd define JOURNAL_STREAM: con eso se sabe que la salida va al journal."""
        with mock.patch.dict(os.environ, {"JOURNAL_STREAM": "8:12345"}):
            self.comprobar("con JOURNAL_STREAM, va al journal", registro.bajo_systemd())
        sin = dict(os.environ)
        sin.pop("JOURNAL_STREAM", None)
        with mock.patch.dict(os.environ, sin, clear=True):
            self.comprobar_falso("sin JOURNAL_STREAM, es una terminal", registro.bajo_systemd())


class ElLazoDeSimulacion(Prueba):

    def test_errores_del_lazo(self):
        """Un error en el lazo queda como ERROR con su detalle, y no inunda el registro."""
        nucleo = HiloSimulacion(ActuadoresSimulados(), semilla=1)

        def roto():
            raise RuntimeError("de mentira")
        nucleo.sim.servicio = roto
        with self.assertLogs("h08.simulacion.hilo", level="ERROR") as visto:
            nucleo.start()
            fin = time.monotonic() + 5
            while nucleo.errores < 5 and time.monotonic() < fin:
                time.sleep(0.05)
            nucleo.detener()
            nucleo.join(5)
        self.comprobar("el lazo siguió andando después de los errores", nucleo.errores >= 5,
                       nucleo.errores)
        self.comprobar_igual("se anotan sólo los tres primeros", len(visto.records), 3)
        self.comprobar("con el número de error y el detalle",
                       "error 1 en el lazo" in visto.records[0].getMessage()
                       and visto.records[0].exc_info is not None)


class BusConProblemas:
    """Un bus I2C de mentira que puede fallar o hacer que una placa se reinicie."""

    def __init__(self, direcciones):
        self.direcciones = set(direcciones)
        self.fallar = 0
        self.reiniciada = set()

    def escribir(self, direccion, registro_, datos=()):
        if self.fallar:
            self.fallar -= 1
            raise OSError(121, "Remote I/O error")
        if registro_ == P.MODE1:
            self.reiniciada.discard(direccion)

    def leer(self, direccion, registro_, n=1):
        # MODE1 dormido y sin autoincremento = la placa se reinició
        return bytes([P.M1_SLEEP if direccion in self.reiniciada else P.M1_AI])

    def responde(self, direccion):
        return direccion in self.direcciones

    def cerrar(self):
        pass


class LasPlacas(Prueba):

    def test_placa_que_no_responde(self):
        """Al arrancar, una placa que no contesta queda como AVISO."""
        with self.assertLogs("h08.hardware.pca9685", level="WARNING") as visto:
            P.ActuadoresPCA9685(placas={"PCA0": 0x40, "PCA1": 0x41}, bus=BusConProblemas([0x40]))
        self.comprobar("avisa qué placa falta y que el tablero sigue",
                       any("PCA1 (0x41) no responde" in r.getMessage() for r in visto.records),
                       [r.getMessage() for r in visto.records])

    def test_placa_que_se_reinicia(self):
        """Si una placa se reinicia (caída de tensión), queda como AVISO."""
        bus = BusConProblemas([0x40])
        act = P.ActuadoresPCA9685(placas={"PCA0": 0x40}, bus=bus)
        bus.reiniciada.add(0x40)
        act._t_vigilancia -= 10
        with self.assertLogs("h08.hardware.pca9685", level="WARNING") as visto:
            act.refrescar()
        self.comprobar("avisa que PCA0 se reinició",
                       any("PCA0 se reinició" in r.getMessage() for r in visto.records))
        self.comprobar_igual("y lo cuenta en la salud", act.salud()["reinicios_pca"], 1)

    def test_errores_del_bus(self):
        """Los errores del bus se anotan como mucho uno cada 10 s; el total sigue en salud()."""
        bus = BusConProblemas([0x40])
        act = P.ActuadoresPCA9685(placas={"PCA0": 0x40}, bus=bus)
        with self.assertLogs("h08.hardware.pca9685", level="WARNING") as visto:
            for _ in range(5):
                bus.fallar = 1
                act.escribir_servo(("PCA0", 1), 90)
                act.refrescar()
            act._t_aviso_bus -= act.CADA_AVISO_BUS_S + 1
            bus.fallar = 1
            act.escribir_servo(("PCA0", 1), 45)
            act.refrescar()
        mensajes = [r.getMessage() for r in visto.records if "bus I2C" in r.getMessage()]
        self.comprobar_igual("seis errores seguidos dejan dos avisos, no seis", len(mensajes), 2)
        self.comprobar("el aviso dice cuántos van", "van 6" in mensajes[-1], mensajes)
        self.comprobar_igual("y la salud los cuenta todos", act.salud()["errores_i2c"], 6)


class LaMudanzaAnotada(Prueba):

    def test_mudanza_en_el_registro(self):
        """Sin avisar, lo que se mueve va como INFO y los conflictos como AVISO."""
        base = tempfile.mkdtemp(prefix="h08_mudanza_")
        try:
            vieja, nueva = os.path.join(base, "raspberry_pi5"), os.path.join(base, "datos")
            escribir(os.path.join(vieja, "posicion_motores.json"), "{}")
            escribir(os.path.join(vieja, "secreto_admin.json"), "vieja")
            escribir(os.path.join(nueva, "secreto_admin.json"), "nueva")
            with self.assertLogs("h08.rutas", level="INFO") as visto:
                rutas.migrar_datos_viejos(vieja, nueva)
            niveles = dict((r.levelname, r.getMessage()) for r in visto.records)
            self.comprobar("lo movido queda como INFO",
                           "movido" in niveles.get("INFO", ""), visto.records)
            self.comprobar("el conflicto queda como AVISO",
                           "sin mover" in niveles.get("WARNING", ""), visto.records)
        finally:
            shutil.rmtree(base, ignore_errors=True)


class ElArranque(Prueba):

    def test_sin_terminal_no_dibuja_el_qr(self):
        """Como servicio (sin terminal) anota el arranque y la dirección, sin el dibujo del QR."""
        puerto = servidor_web.puerto_libre(8620)
        env = dict(ENV, PYTHONUNBUFFERED="1")
        p = subprocess.Popen([sys.executable, "-m", "h08", "--simulado", "--sin-clave",
                              "--puerto", str(puerto)], stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                             errors="replace", env=env, cwd=RAIZ)
        lineas = []

        def leer():
            for l in p.stdout:
                lineas.append(l.rstrip("\n"))
        hilo = threading.Thread(target=leer, daemon=True)
        hilo.start()
        fin = time.monotonic() + 30
        while not any(l.startswith("INFO página en") for l in lineas) and time.monotonic() < fin \
                and p.poll() is None:
            time.sleep(0.1)
        time.sleep(0.3)
        p.terminate()
        p.wait(10)
        hilo.join(5)
        p.stdout.close()
        texto = "\n".join(lineas)
        self.comprobar("anota el arranque como INFO",
                       any(l.startswith("INFO tablero didáctico") for l in lineas), texto[-500:])
        self.comprobar("anota la dirección de la página",
                       any(l.startswith("INFO página en http://") for l in lineas), texto[-500:])
        self.comprobar("--sin-clave queda como AVISO",
                       any(l.startswith("AVISO --sin-clave") for l in lineas), texto[-500:])
        self.comprobar_falso("y no dibuja el QR", "ENTRAR DESDE CUALQUIER CELULAR" in texto,
                             texto[-500:])


if __name__ == "__main__":
    unittest.main()
