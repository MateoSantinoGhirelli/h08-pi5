# -*- coding: utf-8 -*-
"""Que el visitante no pueda operar el tablero.

Levanta el servidor de verdad, en un puerto libre, con un núcleo de mentira,
y le pega con pedidos HTTP como los haría un navegador -o como los haría un
alumno curioso desde la barra de direcciones-.

Lo que se comprueba no es que los botones estén escondidos. Es que el
SERVIDOR conteste 403 cuando la orden no viene de un administrador. Esconder
los botones no protege nada: cualquiera abre la consola del navegador.

    python3 -m unittest pruebas.test_servidor -v
"""
import http.client
import json
import os
import shutil
import socket
import tempfile
import threading
import time
import unittest

from h08.web.acceso import Acceso
from h08.web import servidor as servidor_web
from pruebas.comun import Prueba


class NucleoFalso:
    """Lo mínimo que el servidor le pide al núcleo. Anota lo que le ordenan."""

    def __init__(self):
        self.catalogo = {"fases": [], "escenarios": [], "fallas": [],
                         "instrumentos": [], "anunciador": []}
        self.foto = {"modo_nombre": "MODO 1", "t": 1.0, "pausado": False,
                     "fase": "CRUCERO", "fase_texto": "Crucero"}
        self.ordenes = []

    def ordenar(self, que, valor=None):
        self.ordenes.append((que, valor))


class Cliente:
    """Un navegador de mentira: guarda la cookie como la guardaria uno."""

    def __init__(self, puerto):
        self.puerto = puerto
        self.cookie = None

    def _pedir(self, metodo, ruta):
        c = http.client.HTTPConnection("127.0.0.1", self.puerto, timeout=5)
        cab = {}
        if self.cookie:
            cab["Cookie"] = self.cookie
        c.request(metodo, ruta, headers=cab)
        r = c.getresponse()
        cuerpo = r.read().decode("utf-8", "replace")
        sc = r.getheader("Set-Cookie")
        if sc:
            self.cookie = sc.split(";")[0]
        destino = r.getheader("Location")
        c.close()
        return r.status, cuerpo, destino

    def get(self, ruta):
        return self._pedir("GET", ruta)

    def post(self, ruta):
        return self._pedir("POST", ruta)

    def seguir(self, ruta):
        """GET siguiendo un redirect, como hace el navegador con el QR."""
        cod, cuerpo, destino = self.get(ruta)
        if cod in (301, 302) and destino:
            return self.get(destino)
        return cod, cuerpo, destino


class ConServidor(Prueba):
    """Cada prueba arranca su propio servidor, con páginas de mentira."""

    con_clave = True

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.web = os.path.join(self.tmp, "web")
        os.makedirs(self.web)
        # páginas de mentira, para no depender de las de verdad
        for f, t in (("tablero.html", "<html>TABLERO PUBLICO</html>"),
                     ("mando.html", "<html>BOTONERA</html>"),
                     ("sin_permiso.html", "<html>HACE FALTA EL QR</html>")):
            with open(os.path.join(self.web, f), "w", encoding="utf-8") as fh:
                fh.write(t)
        self.acceso = (Acceso(os.path.join(self.tmp, "secreto_admin.json"))
                       if self.con_clave else None)
        self.nucleo = NucleoFalso()
        self.puerto = servidor_web.puerto_libre(8731)
        self.srv = servidor_web.crear(self.nucleo, self.puerto, self.web, acceso=self.acceso)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        time.sleep(0.1)

    def tearDown(self):
        self.srv.shutdown()
        self.srv.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def profesor_con_el_mando(self):
        """El profesor entra con el QR y da una orden: así toma el mando."""
        p = Cliente(self.puerto)
        p.seguir("/mando?k=" + self.acceso.clave)
        p.post("/api/modo/3?id=OIL_PRESS_LOSS")
        return p


class ElVisitante(ConServidor):

    def test_el_visitante(self):
        """Sin clave se mira todo, pero toda orden se rechaza con 403."""
        v = Cliente(self.puerto)
        cod, cuerpo, _ = v.get("/")
        self.comprobar_igual("puede ver el tablero", cod, 200)
        self.comprobar("y es la página publica", "TABLERO PUBLICO" in cuerpo)

        cod, _c, _ = v.get("/api/estado")
        self.comprobar_igual("puede leer el estado en vivo", cod, 200)
        cod, cuerpo, _ = v.get("/api/catalogo")
        self.comprobar_igual("puede leer el catálogo", cod, 200)
        self.comprobar_igual("y el catálogo le dice que no es admin",
                             json.loads(cuerpo).get("admin"), False)

        cod, cuerpo, _ = v.get("/mando")
        self.comprobar_igual("en /mando le sale que hace falta el QR", cod, 200)
        self.comprobar("y no la botonera", "BOTONERA" not in cuerpo)
        cod, _c, _ = v.get("/tecnico")
        self.comprobar_igual("la vista técnica ya no existe para nadie", cod, 404)

        antes = len(self.nucleo.ordenes)
        for ruta in ("/api/modo/1", "/api/modo/3?id=OIL_PRESS_LOSS",
                     "/api/accion/pausa?valor=true",
                     "/api/accion/velocidad?valor=4"):
            cod, _c, _ = v.post(ruta)
            self.comprobar_igual("POST %s -> prohibido" % ruta[:34], cod, 403)
        self.comprobar_igual("y el núcleo no recibió NINGUNA orden",
                             len(self.nucleo.ordenes), antes)

        cod, _c, _ = v.post("/api/mando/tomar")
        self.comprobar_igual("tampoco puede tomar el mando", cod, 403)

        # una clave inventada no sirve
        cod, cuerpo, _ = v.get("/mando?k=" + "x" * 22)
        self.comprobar("con una clave inventada tampoco entra", "BOTONERA" not in cuerpo)


class ElProfesor(ConServidor):

    def test_el_profesor(self):
        """Con el QR entra, la clave sale de la URL y sus órdenes llegan al núcleo."""
        p = Cliente(self.puerto)
        cod, cuerpo, destino = p.get("/mando?k=" + self.acceso.clave)
        self.comprobar_igual("el QR redirige", cod, 302)
        self.comprobar_igual("a la dirección sin la clave", destino, "/mando")
        self.comprobar("y deja cookie", p.cookie and p.cookie.startswith("h08="))
        self.comprobar("la clave no quedo en la URL de destino", "k=" not in (destino or ""))

        cod, cuerpo, _ = p.get("/mando")
        self.comprobar("ahora si ve la botonera", "BOTONERA" in cuerpo)
        cod, _c, _ = p.get("/tecnico")
        self.comprobar_igual("y para el profesor tampoco", cod, 404)

        antes = len(self.nucleo.ordenes)
        cod, _c, _ = p.post("/api/modo/3?id=OIL_PRESS_LOSS")
        self.comprobar_igual("puede meter una falla", cod, 200)
        self.comprobar_igual("y la orden llego al núcleo", len(self.nucleo.ordenes), antes + 1)
        self.comprobar_igual("con lo que corresponde", self.nucleo.ordenes[-1],
                             ("modo_falla", "OIL_PRESS_LOSS"))

        cod, cuerpo, _ = p.get("/api/sesion")
        e = json.loads(cuerpo)
        self.comprobar("se ve como admin", e["admin"])
        self.comprobar("y con el mando", e["mando"])

        # el tablero muestra el atajo a /mando solo si el catálogo dice que si
        cod, cuerpo, _ = p.get("/api/catalogo")
        self.comprobar("el catálogo le avisa al tablero que es admin",
                       json.loads(cuerpo).get("admin"))


class ElAyudante(ConServidor):

    def test_el_ayudante(self):
        """Un segundo admin no manda hasta que el profesor le cede el mando."""
        p = self.profesor_con_el_mando()
        a = Cliente(self.puerto)
        a.seguir("/mando?k=" + self.acceso.clave)
        cod, cuerpo, _ = a.get("/api/sesion")
        e = json.loads(cuerpo)
        self.comprobar("es admin", e["admin"])
        self.comprobar_igual("pero no tiene el mando", e["mando"], False)
        self.comprobar("y ve que lo tiene otro", e["hay_titular"])

        antes = len(self.nucleo.ordenes)
        cod, cuerpo, _ = a.post("/api/accion/pausa?valor=true")
        self.comprobar_igual("su orden se rechaza con 409", cod, 409)
        self.comprobar("explicando que el mando lo tiene otro",
                       "mando" in json.loads(cuerpo).get("motivo", "").lower())
        self.comprobar_igual("y el núcleo no la recibió", len(self.nucleo.ordenes), antes)

        cod, _c, _ = a.post("/api/mando/pedir")
        self.comprobar_igual("puede pedir el mando", cod, 200)
        cod, cuerpo, _ = p.get("/api/sesion")
        self.comprobar("el profesor ve el pedido", json.loads(cuerpo)["pedido_ajeno"])

        cod, _c, _ = p.post("/api/mando/ceder")
        self.comprobar_igual("el profesor cede", cod, 200)
        cod, cuerpo, _ = a.get("/api/sesion")
        self.comprobar("y el ayudante queda con el mando", json.loads(cuerpo)["mando"])

        antes = len(self.nucleo.ordenes)
        cod, _c, _ = a.post("/api/accion/pausa?valor=true")
        self.comprobar_igual("ahora si le pasan las órdenes", cod, 200)
        self.comprobar_igual("y llegan al núcleo", len(self.nucleo.ordenes), antes + 1)
        cod, _c, _ = a.post("/api/accion/borrar_todo?valor=true")
        self.comprobar_igual("una orden que no existe se rechaza con 400", cod, 400)
        self.comprobar_igual("y no llega al núcleo", len(self.nucleo.ordenes), antes + 1)

        cod, _c, _ = p.post("/api/accion/pausa?valor=false")
        self.comprobar_igual("y al profesor ya no", cod, 409)


class CerrarSesion(ConServidor):

    def test_cerrar_sesion(self):
        """Después de /salir ya no se puede mandar."""
        a = Cliente(self.puerto)
        a.seguir("/mando?k=" + self.acceso.clave)
        cod, _c, destino = a.get("/salir")
        self.comprobar_igual("redirige al tablero", destino, "/")
        a.cookie = None
        cod, _c, _ = a.post("/api/modo/1")
        self.comprobar_igual("y ya no puede mandar", cod, 403)


class RenovarLaClave(ConServidor):

    def test_renovar_la_clave(self):
        """Una clave nueva corta las sesiones abiertas y deja afuera a la vieja."""
        p = self.profesor_con_el_mando()
        vieja = self.acceso.clave
        nueva = self.acceso.renovar_clave()
        cod, _c, _ = p.post("/api/modo/1")
        self.comprobar_igual("la sesión del profesor se corta", cod, 403)
        z = Cliente(self.puerto)
        cod, cuerpo, _ = z.get("/mando?k=" + vieja)
        self.comprobar("la clave vieja ya no entra", "BOTONERA" not in cuerpo)
        z2 = Cliente(self.puerto)
        cod, cuerpo, _ = z2.seguir("/mando?k=" + nueva)
        self.comprobar("la nueva si", "BOTONERA" in cuerpo)


class LaClaveNoSeSirve(ConServidor):

    def test_la_clave_no_se_sirve_por_la_web(self):
        """Ni siquiera un admin recibe la clave en ninguna página ni respuesta."""
        z2 = Cliente(self.puerto)
        z2.seguir("/mando?k=" + self.acceso.clave)
        for ruta in ("/", "/qr", "/api/catalogo", "/api/estado", "/api/sesion",
                     "/mando"):
            cod, cuerpo, _ = z2.get(ruta)
            self.comprobar_igual("la clave no aparece en %s" % ruta,
                                 self.acceso.clave in cuerpo, False)


class ElCuerpoInventado(ConServidor):

    def test_el_cuerpo_inventado(self):
        """Un Content-Length enorme o roto se rechaza con 413 sin leer ni reservar nada."""
        for largo in ("1500000000", "-5", "abc"):
            s = socket.create_connection(("127.0.0.1", self.puerto), timeout=5)
            s.sendall(("POST /api/modo/4 HTTP/1.1\r\nHost: x\r\nContent-Length: %s\r\n\r\n"
                       % largo).encode())
            respuesta = s.recv(200).decode("latin-1")
            s.close()
            self.comprobar("Content-Length %s -> 413 en el momento" % largo,
                           respuesta.startswith("HTTP/1.1 413"), respuesta[:40])
        self.comprobar_igual("y el núcleo no recibió ninguna orden", self.nucleo.ordenes, [])
        p = self.profesor_con_el_mando()
        cod, _c, _ = p.post("/api/accion/pausa?valor=true")
        self.comprobar_igual("las órdenes de la botonera, sin cuerpo, siguen pasando", cod, 200)


class LaConexionAbandonada(ConServidor):

    def test_la_conexion_abandonada(self):
        """Un celular que se fue sin cerrar no se queda con un hilo para siempre."""
        self.comprobar("el servidor tiene tiempo de espera",
                       0 < (servidor_web.Manejador.timeout or 0) <= 120)
        vieja = servidor_web.Manejador.timeout
        servidor_web.Manejador.timeout = 0.5      # el mismo mecanismo, sin esperar 60 s
        try:
            s = socket.create_connection(("127.0.0.1", self.puerto), timeout=5)
            s.sendall(b"GET /api/estado HTTP/1.1\r\nHost: x\r\n\r\n")
            time.sleep(1.5)
            s.settimeout(2)
            # La respuesta puede llegar en dos tramos: se lee todo hasta el cierre.
            cerrada = False
            try:
                while True:
                    if s.recv(4096) == b"":
                        cerrada = True
                        break
            except socket.timeout:
                cerrada = False                   # sigue abierta: el hilo sigue esperando
            except OSError:
                cerrada = True                    # la cerró de golpe (en Windows, reset)
            s.close()
        finally:
            servidor_web.Manejador.timeout = vieja
        self.comprobar("pasado el tiempo, el servidor cierra la conexión", cerrada)


class ElServidorAbierto(ConServidor):
    """El de la computadora propia: con acceso=None el servidor deja mandar, y
    /mando tiene que mostrar la botonera; si no, no habría forma de llegar a la
    página desde donde se manda."""

    con_clave = False

    def test_el_servidor_abierto(self):
        """Sin control de acceso, cualquiera ve la botonera y sus órdenes pasan."""
        c = Cliente(self.puerto)
        cod, cuerpo, _ = c.get("/")
        self.comprobar_igual("se ve el tablero", cod, 200)
        cod, cuerpo, _ = c.get("/mando")
        self.comprobar("y TAMBIÉN la botonera, sin clave", "BOTONERA" in cuerpo)
        cod, cuerpo, _ = c.get("/api/catalogo")
        self.comprobar("el catálogo dice que es admin (aparece el atajo)",
                       json.loads(cuerpo).get("admin"))
        antes = len(self.nucleo.ordenes)
        cod, _x, _ = c.post("/api/modo/1")
        self.comprobar_igual("y las órdenes pasan", cod, 200)
        self.comprobar_igual("y llegan al núcleo", len(self.nucleo.ordenes), antes + 1)


if __name__ == "__main__":
    unittest.main()
