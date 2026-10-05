# -*- coding: utf-8 -*-
"""La página de verdad: carátulas, rutas que no dejan salir de su carpeta, QR del wifi y catálogo.

    python3 -m unittest pruebas.test_web -v
"""
import http.client
import json
import os
import re
import threading
import unittest

from h08 import rutas
from h08.config import TABLERO, PANEL_VIRTUAL
from h08.hardware.simulado import ActuadoresSimulados
from h08.simulacion.hilo import HiloSimulacion
from h08.web import servidor as servidor_web
from pruebas.comun import Prueba, leer


class LasCaratulas(Prueba):

    def test_caratulas(self):
        """Hay carátula para cada instrumento que se dibuja, limpia y con medidas coherentes."""
        carpeta = os.path.join(rutas.ESTATICOS, "caratulas")
        try:
            ind = json.loads(leer(os.path.join(carpeta, "indice.json")))
        except (OSError, ValueError):
            ind = {}
        self.comprobar("existe h08/web/static/caratulas/indice.json", bool(ind))
        con_dibujo = [it["id"] for it in list(TABLERO) + list(PANEL_VIRTUAL)
                      if it.get("pos") and it.get("dial") != "horizonte"]
        faltan = [i for i in con_dibujo if i not in ind]
        self.comprobar("hay carátula para los %d instrumentos que se dibujan" % len(con_dibujo),
                       not faltan, faltan)
        sucias = []
        for ident, c in ind.items():
            try:
                t = leer(os.path.join(carpeta, c["archivo"]))
            except OSError:
                sucias.append(c["archivo"] + " (no está)")
                continue
            if 'fill="#FFFFFF"' in t or "stroke-dasharray" in t or 'width="' in t.split(">")[0]:
                sucias.append(c["archivo"])
            if not (0 < c["R"] < c["L"] / 2.0):
                sucias.append(c["archivo"] + " (medidas)")
        self.comprobar("sin fondo blanco, sin líneas de corte, medidas coherentes", not sucias,
                       sucias)


class Cliente:
    def __init__(self, puerto):
        self.puerto = puerto

    def pedir(self, metodo, ruta):
        # 127.0.0.1 y no localhost: en Windows localhost prueba primero IPv6 y
        # tarda unos 2 s por pedido en caer en IPv4, que es donde escucha.
        c = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=5)
        c.request(metodo, ruta, body=b"" if metodo == "POST" else None)
        r = c.getresponse()
        b = r.read()
        c.close()
        return r.status, b, r.getheader("Content-Type") or ""


class ElServidorConLaPaginaDeVerdad(Prueba):
    """El servidor con las páginas y carátulas reales y un núcleo simulado, sin clave."""

    def setUp(self):
        self.nucleo = HiloSimulacion(ActuadoresSimulados(), semilla=1)
        self.nucleo.start()
        puerto = servidor_web.puerto_libre(8150)
        self.srv = servidor_web.crear(self.nucleo, puerto, rutas.ESTATICOS, acceso=None)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.c = Cliente(puerto)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        self.nucleo.detener()
        self.nucleo.join(5)

    def test_caratulas_por_la_web(self):
        """/caratulas/ sirve los SVG y no deja pedir nada fuera de su carpeta."""
        s, b, t = self.c.pedir("GET", "/caratulas/airspeed.svg")
        self.comprobar("/caratulas/airspeed.svg se sirve como SVG",
                       s == 200 and "svg" in t and b"<svg" in b)
        for malo in ("/caratulas/../secreto_admin.json", "/caratulas/..%2fsecreto_admin.svg",
                     "/caratulas/AIRSPEED.svg", "/caratulas/indice.json", "/caratulas/"):
            s, _, _ = self.c.pedir("GET", malo)
            self.comprobar("rechaza %s" % malo, s == 404, s)

    def test_qr_del_wifi(self):
        """El QR del wifi sale de la red, la clave y la IP de deploy/punto_de_acceso.sh."""
        s, b, t = self.c.pedir("GET", "/qr_wifi.svg")
        self.comprobar("/qr_wifi.svg", s == 200 and b"<svg" in b)
        script = leer(rutas.PUNTO_DE_ACCESO)
        en_script = dict((campo, re.search(r'^%s="([^"]*)"' % var, script, re.M).group(1))
                         for campo, var in (("red", "RED"), ("clave", "CLAVE"), ("ip", "IP")))
        ap = servidor_web.datos_punto_de_acceso()
        self.comprobar("la red, la clave y la IP del QR salen de deploy/punto_de_acceso.sh",
                       ap == en_script and ap["clave"] != "", (ap, en_script))

    def test_catalogo_y_kiosco(self):
        """El catálogo trae carátulas, barridos y la red; el kiosco y el mando sin clave funcionan."""
        s, b, _ = self.c.pedir("GET", "/api/catalogo")
        cat = json.loads(b.decode("utf-8"))
        ins = {i["id"]: i for i in cat["instrumentos"]}
        self.comprobar("el catálogo trae las carátulas", "AIRSPEED" in cat.get("caratulas", {}))
        self.comprobar("el catálogo trae barrido y centro (VSI con el cero a las 9)",
                       ins["AIRSPEED"]["barrido"] == 300 and ins["VSI"]["centro"] == 180.0
                       and ins["COMPASS"]["barrido"] == "CONT")
        self.comprobar("el catálogo trae la red wifi",
                       cat.get("wifi", {}).get("red") == "Tablero-H08")
        s, b, _ = self.c.pedir("POST", "/api/mando/tomar")
        self.comprobar("sin clave (--banco): tomar el mando no rompe el servidor",
                       s == 200 and json.loads(b.decode("utf-8"))["ok"])
        s, b, _ = self.c.pedir("GET", "/?kiosco=1")
        self.comprobar("la página del kiosco se sirve", s == 200 and b"kiosco" in b)


if __name__ == "__main__":
    unittest.main()
