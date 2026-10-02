#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prueba_servidor.py - que el visitante no pueda operar el tablero
=================================================================

Levanta el servidor de verdad, en un puerto libre, con un nucleo de mentira,
y le pega con pedidos HTTP como los haria un navegador -o como los haria un
alumno curioso desde la barra de direcciones-.

Lo que se comprueba no es que los botones esten escondidos. Es que el
SERVIDOR conteste 403 cuando la orden no viene de un administrador. Esconder
los botones no protege nada: cualquiera abre la consola del navegador.

    python3 prueba_servidor.py
"""
import http.client
import json
import os
import sys
import tempfile
import threading
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
for _c in (os.path.join(AQUI, "..", "nucleo"), os.path.join(AQUI, "nucleo")):
    if os.path.isdir(_c):
        sys.path.insert(0, os.path.abspath(_c))
        break

from acceso import Acceso                                    # noqa: E402
import servidor_web                                       # noqa: E402

fallos = []


def igual(nombre, obtenido, esperado):
    ok = obtenido == esperado
    print("  %s %-54s %s" % ("ok  " if ok else "MAL ", nombre,
                             "" if ok else "-> %r (esperaba %r)"
                             % (obtenido, esperado)))
    if not ok:
        fallos.append(nombre)


def cierto(nombre, v):
    igual(nombre, bool(v), True)


# ===========================================================================
class NucleoFalso:
    """Lo minimo que el servidor le pide al nucleo. Anota lo que le ordenan."""

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


# ===========================================================================
def main():
    tmp = tempfile.mkdtemp()
    web = os.path.join(tmp, "web")
    os.makedirs(web)
    # paginas de mentira, para no depender de las de verdad
    for f, t in (("tablero.html", "<html>TABLERO PUBLICO</html>"),
                 ("mando.html", "<html>BOTONERA</html>"),
                 ("sin_permiso.html", "<html>HACE FALTA EL QR</html>")):
        open(os.path.join(web, f), "w", encoding="utf-8").write(t)

    acceso = Acceso(os.path.join(tmp, "secreto_admin.json"))
    nucleo = NucleoFalso()
    puerto = servidor_web.puerto_libre(8731)
    srv = servidor_web.crear(nucleo, puerto, web, acceso=acceso)
    hilo = threading.Thread(target=srv.serve_forever, daemon=True)
    hilo.start()
    time.sleep(0.3)

    print("=" * 76)
    print(" EL SERVIDOR, CON UN VISITANTE Y DOS ADMINISTRADORES")
    print("=" * 76)

    # -- el visitante -------------------------------------------------------
    print("\n  EL VISITANTE (sin clave)")
    v = Cliente(puerto)
    cod, cuerpo, _ = v.get("/")
    igual("puede ver el tablero", cod, 200)
    cierto("y es la pagina publica", "TABLERO PUBLICO" in cuerpo)

    cod, _c, _ = v.get("/api/estado")
    igual("puede leer el estado en vivo", cod, 200)
    cod, cuerpo, _ = v.get("/api/catalogo")
    igual("puede leer el catalogo", cod, 200)
    igual("y el catalogo le dice que no es admin",
          json.loads(cuerpo).get("admin"), False)

    cod, cuerpo, _ = v.get("/mando")
    igual("en /mando le sale que hace falta el QR", cod, 200)
    cierto("y no la botonera", "BOTONERA" not in cuerpo)
    cod, _c, _ = v.get("/tecnico")
    igual("la vista tecnica ya no existe para nadie", cod, 404)

    antes = len(nucleo.ordenes)
    for ruta in ("/api/modo/1", "/api/modo/3?id=OIL_PRESS_LOSS",
                 "/api/accion/pausa?valor=true",
                 "/api/accion/velocidad?valor=4"):
        cod, _c, _ = v.post(ruta)
        igual("POST %s -> prohibido" % ruta[:34], cod, 403)
    igual("y el nucleo no recibio NINGUNA orden", len(nucleo.ordenes), antes)

    cod, _c, _ = v.post("/api/mando/tomar")
    igual("tampoco puede tomar el mando", cod, 403)

    # una clave inventada no sirve
    cod, cuerpo, _ = v.get("/mando?k=" + "x" * 22)
    cierto("con una clave inventada tampoco entra", "BOTONERA" not in cuerpo)

    # -- el profesor --------------------------------------------------------
    print("\n  EL PROFESOR (con el QR)")
    p = Cliente(puerto)
    cod, cuerpo, destino = p.get("/mando?k=" + acceso.clave)
    igual("el QR redirige", cod, 302)
    igual("a la direccion sin la clave", destino, "/mando")
    cierto("y deja cookie", p.cookie and p.cookie.startswith("h08="))
    cierto("la clave no quedo en la URL de destino", "k=" not in (destino or ""))

    cod, cuerpo, _ = p.get("/mando")
    cierto("ahora si ve la botonera", "BOTONERA" in cuerpo)
    cod, _c, _ = p.get("/tecnico")
    igual("y para el profesor tampoco", cod, 404)

    antes = len(nucleo.ordenes)
    cod, _c, _ = p.post("/api/modo/3?id=OIL_PRESS_LOSS")
    igual("puede meter una falla", cod, 200)
    igual("y la orden llego al nucleo", len(nucleo.ordenes), antes + 1)
    igual("con lo que corresponde", nucleo.ordenes[-1],
          ("modo_falla", "OIL_PRESS_LOSS"))

    cod, cuerpo, _ = p.get("/api/sesion")
    e = json.loads(cuerpo)
    cierto("se ve como admin", e["admin"])
    cierto("y con el mando", e["mando"])

    # el tablero muestra el atajo a /mando solo si el catalogo dice que si
    cod, cuerpo, _ = p.get("/api/catalogo")
    cierto("el catalogo le avisa al tablero que es admin",
           json.loads(cuerpo).get("admin"))

    # -- el ayudante --------------------------------------------------------
    print("\n  EL AYUDANTE (tambien con el QR)")
    a = Cliente(puerto)
    a.seguir("/mando?k=" + acceso.clave)
    cod, cuerpo, _ = a.get("/api/sesion")
    e = json.loads(cuerpo)
    cierto("es admin", e["admin"])
    igual("pero no tiene el mando", e["mando"], False)
    cierto("y ve que lo tiene otro", e["hay_titular"])

    antes = len(nucleo.ordenes)
    cod, cuerpo, _ = a.post("/api/accion/pausa?valor=true")
    igual("su orden se rechaza con 409", cod, 409)
    cierto("explicando que el mando lo tiene otro",
           "mando" in json.loads(cuerpo).get("motivo", "").lower())
    igual("y el nucleo no la recibio", len(nucleo.ordenes), antes)

    cod, _c, _ = a.post("/api/mando/pedir")
    igual("puede pedir el mando", cod, 200)
    cod, cuerpo, _ = p.get("/api/sesion")
    cierto("el profesor ve el pedido", json.loads(cuerpo)["pedido_ajeno"])

    cod, _c, _ = p.post("/api/mando/ceder")
    igual("el profesor cede", cod, 200)
    cod, cuerpo, _ = a.get("/api/sesion")
    cierto("y el ayudante queda con el mando", json.loads(cuerpo)["mando"])

    antes = len(nucleo.ordenes)
    cod, _c, _ = a.post("/api/accion/pausa?valor=true")
    igual("ahora si le pasan las ordenes", cod, 200)
    igual("y llegan al nucleo", len(nucleo.ordenes), antes + 1)
    cod, _c, _ = a.post("/api/accion/borrar_todo?valor=true")
    igual("una orden que no existe se rechaza con 400", cod, 400)
    igual("y no llega al nucleo", len(nucleo.ordenes), antes + 1)

    cod, _c, _ = p.post("/api/accion/pausa?valor=false")
    igual("y al profesor ya no", cod, 409)

    # -- salir --------------------------------------------------------------
    print("\n  CERRAR SESION")
    cod, _c, destino = a.get("/salir")
    igual("redirige al tablero", destino, "/")
    a.cookie = None
    cod, _c, _ = a.post("/api/modo/1")
    igual("y ya no puede mandar", cod, 403)

    # -- renovar la clave ---------------------------------------------------
    print("\n  RENOVAR LA CLAVE")
    vieja = acceso.clave
    nueva = acceso.renovar_clave()
    cod, _c, _ = p.post("/api/modo/1")
    igual("la sesion del profesor se corta", cod, 403)
    z = Cliente(puerto)
    cod, cuerpo, _ = z.get("/mando?k=" + vieja)
    cierto("la clave vieja ya no entra", "BOTONERA" not in cuerpo)
    z2 = Cliente(puerto)
    cod, cuerpo, _ = z2.seguir("/mando?k=" + nueva)
    cierto("la nueva si", "BOTONERA" in cuerpo)

    # -- que NUNCA se sirva la clave por la web -----------------------------
    print("\n  LA CLAVE NO SE SIRVE POR LA WEB")
    for ruta in ("/", "/qr", "/api/catalogo", "/api/estado", "/api/sesion",
                 "/mando"):
        cod, cuerpo, _ = z2.get(ruta)
        igual("la clave no aparece en %s" % ruta, nueva in cuerpo, False)

    srv.shutdown()

    # -- el servidor ABIERTO, que es el de la computadora propia ------------
    # Este es el caso que se me escapo: con acceso=None el servidor dejaba
    # mandar pero /mando contestaba "hace falta el QR", o sea que no habia
    # forma de llegar a la pagina desde donde se manda.
    print("\n  EL SERVIDOR ABIERTO (computadora propia, sin clave)")
    n2 = NucleoFalso()
    p2 = servidor_web.puerto_libre(8751)
    srv2 = servidor_web.crear(n2, p2, web, acceso=None)
    threading.Thread(target=srv2.serve_forever, daemon=True).start()
    time.sleep(0.3)
    c = Cliente(p2)
    cod, cuerpo, _ = c.get("/")
    igual("se ve el tablero", cod, 200)
    cod, cuerpo, _ = c.get("/mando")
    cierto("y TAMBIEN la botonera, sin clave", "BOTONERA" in cuerpo)
    cod, cuerpo, _ = c.get("/api/catalogo")
    cierto("el catalogo dice que es admin (aparece el atajo)",
           json.loads(cuerpo).get("admin"))
    antes = len(n2.ordenes)
    cod, _x, _ = c.post("/api/modo/1")
    igual("y las ordenes pasan", cod, 200)
    igual("y llegan al nucleo", len(n2.ordenes), antes + 1)
    srv2.shutdown()

    print("")
    print("=" * 76)
    if fallos:
        print(" FALLARON %d:" % len(fallos))
        for f in fallos:
            print("   %s" % f)
    else:
        print(" Todo bien.")
    print("=" * 76)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
