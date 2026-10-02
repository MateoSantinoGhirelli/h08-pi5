# -*- coding: utf-8 -*-
"""La página del tablero, con http.server: la Pi no necesita internet ni paquetes.

Sirve el tablero en vivo (/), la botonera del profesor (/mando), los QR de la
dirección y de la red wifi, el cartel A4 para imprimir, las carátulas y el estado en
JSON (/api/...). La página consulta cada 200 ms: la suavidad de las agujas la da el
modelo, no el transporte.

Toda orden se rechaza con 403 si no viene de un admin y con 409 si ese admin no
tiene el mando. La verificación está acá y no en la página: esconder los botones no
protege nada, lo que protege es rechazar el pedido (docs/acceso.md).
"""
import json
import os
import re
import socket
import subprocess

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from h08 import rutas
from h08.web import qr

# Las únicas órdenes sueltas que acepta /api/accion/ (los modos van por
# /api/modo/). Cualquier otra cosa se rechaza con 400.
ACCIONES = ("pausa", "velocidad", "prueba_luces", "piloto_reactivo", "ciclar",
            "activar_falla", "quitar_falla")
# Las órdenes viajan en la dirección y las páginas no mandan cuerpo. El tope importa
# porque el cuerpo se lee antes de saber quién pide: sin él, un Content-Length
# inventado hace que Python reserve esa memoria de una vez (1,5 GB con un pedido).
CUERPO_MAX = 4096
_SCRIPT_AP = rutas.PUNTO_DE_ACCESO


def datos_punto_de_acceso():
    """Nombre, clave e IP de la red wifi propia, leídos de deploy/punto_de_acceso.sh.

    Se leen del script en vez de repetirlos acá: así el cartel impreso no puede
    quedar desactualizado si se cambia la clave de la red.
    """
    datos = {"red": "Tablero-H08", "clave": "", "ip": "10.55.0.1"}
    try:
        with open(_SCRIPT_AP, encoding="utf-8") as f:
            texto = f.read()
    except OSError:
        return datos
    for campo, var in (("red", "RED"), ("clave", "CLAVE"), ("ip", "IP")):
        m = re.search(r'^%s="([^"]*)"' % var, texto, re.M)
        if m:
            datos[campo] = m.group(1)
    return datos


def puerto_libre(preferido, intentos=20):
    """El primer puerto disponible desde el preferido hacia arriba."""
    for p in range(preferido, preferido + intentos):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("", p))
            return p
        except OSError:
            continue
        finally:
            s.close()
    return None


def ip_de_red():
    """La IP de esta máquina en la red local, para entrar desde el celular.

    Si hay ruta hacia afuera, la IP de la interfaz por la que se saldría (se consulta
    la tabla de rutas, no se manda ningún paquete). Si no la hay, porque la Pi es el
    punto de acceso, las de sus interfaces, con prioridad para la del punto de acceso.
    Se calcula en cada pedido: al encender, el servicio puede arrancar antes que la red.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    finally:
        s.close()

    try:
        salida = subprocess.run(["hostname", "-I"], capture_output=True,
                                text=True, timeout=2).stdout.split()
    except (OSError, subprocess.SubprocessError):
        salida = []
    ips = [x for x in salida if x.count(".") == 3 and not x.startswith("127.")]
    ip_ap = datos_punto_de_acceso()["ip"]
    if ip_ap in ips:
        return ip_ap
    return ips[0] if ips else None


def direccion(puerto):
    """La dirección que se le da a la gente, con la IP de red si la hay."""
    ip = ip_de_red()
    return "http://%s:%d/" % (ip or "localhost", puerto)


# Las dos páginas que se arman en el momento, porque llevan el QR de la dirección
_PAGINA_QR = """<!doctype html><html lang="es"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tablero H-08 &middot; entrar desde el celular</title>
<style>
 html,body{margin:0;height:100%%;background:#111;color:#eee;
   font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
 .caja{min-height:100%%;display:flex;flex-direction:column;
   align-items:center;justify-content:center;gap:1.4rem;padding:2rem;
   box-sizing:border-box;text-align:center}
 h1{font-size:1.5rem;font-weight:600;margin:0;letter-spacing:.02em}
 .qr{background:#fff;padding:18px;border-radius:14px;line-height:0}
 .url{font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
   font-size:clamp(1.1rem,4vw,2rem);color:#7ec8ff;word-break:break-all}
 p{margin:0;color:#9aa4ae;max-width:34rem;line-height:1.5}
 a{color:#7ec8ff;text-decoration:none;border-bottom:1px solid #35505f;
   padding-bottom:2px}
</style></head><body><div class="caja">
<h1>Tablero did&aacute;ctico H-08</h1>
<div class="qr">%(svg)s</div>
<div class="url">%(url)s</div>
<p>Apunt&aacute; la c&aacute;mara del celular al c&oacute;digo. Ten&eacute;s que estar
en la misma red que %(donde)s.</p>
<p><a href="/">Ir al tablero</a> &nbsp;&middot;&nbsp; <a href="/cartel">Cartel para imprimir</a></p>
</div></body></html>"""

_PAGINA_CARTEL = """<!doctype html><html lang="es"><head><meta charset="utf-8">
<title>Cartel &middot; Tablero H-08</title>
<style>
 @page{size:A4;margin:16mm}
 body{font-family:Arial,Helvetica,sans-serif;color:#111;margin:0}
 .hoja{max-width:178mm;margin:0 auto;text-align:center}
 h1{font-size:30pt;margin:6mm 0 1mm;color:#1F3864}
 .sub{font-size:12pt;color:#555;margin:0 0 3mm}
 .lema{font-size:13pt;color:#2E75B6;font-weight:bold;margin:0 0 7mm}
 .paso{display:inline-block;width:80mm;vertical-align:top;margin:0 3mm}
 .paso h2{font-size:15pt;margin:0 0 3mm}
 .qr{width:62mm;margin:0 auto 3mm}
 .qr svg{width:100%%;height:auto}
 .dato{font-size:14pt;font-weight:bold}
 .dato2{font-size:11pt;color:#555}
 .pie{margin-top:9mm;font-size:10pt;color:#666;line-height:1.6}
 .no-imprimir{margin:6mm 0;font-size:11pt}
 @media print{.no-imprimir{display:none}}
</style></head><body><div class="hoja">
<p class="no-imprimir">Para imprimir: Ctrl+P (en el celular, Compartir &rarr; Imprimir).</p>
<h1>TABLERO DEL H-08</h1>
<p class="sub">Sikorsky S-55 / H-19A &middot; EEST N&deg; 7 &middot; Taller Regional Quilmes</p>
<p class="lema">Miralo funcionar desde tu celular</p>
<div class="paso"><h2>1. Conectate a la red</h2>
 <div class="qr">%(qr_wifi)s</div>
 <div class="dato">%(red)s</div><div class="dato2">clave: %(clave)s</div></div>
<div class="paso"><h2>2. Abr&iacute; la p&aacute;gina</h2>
 <div class="qr">%(qr_url)s</div>
 <div class="dato">%(url)s</div><div class="dato2">s&oacute;lo para mirar</div></div>
<p class="pie">La red del tablero no tiene internet: es normal.<br>
Si el celular se desconecta solo, volv&eacute; a conectarte y us&aacute; el segundo c&oacute;digo.</p>
</div></body></html>"""


class Manejador(BaseHTTPRequestHandler):
    """Atiende los pedidos. ThreadingHTTPServer usa un hilo por pedido, así
    que muchos celulares pueden mirar a la vez; la simulación corre en su
    propio hilo y ningún pedido la frena."""

    protocol_version = "HTTP/1.1"
    # Un celular que se va de la red sin cerrar la conexión dejaba su hilo esperando
    # para siempre. La página pide cada 200 ms: una conexión en uso nunca llega a 60 s.
    timeout = 60
    nucleo = None                 # el HiloSimulacion (lo completa crear())
    estaticos = None              # carpeta con las páginas .html
    puerto = 8000
    donde = "esta computadora"
    acceso = None                 # acceso.Acceso, o None para no pedir clave

    # nombre de la cookie de sesión: corto y sin decir de qué es
    COOKIE = "h08"

    def _url_publica(self):
        return direccion(self.puerto)

    def _responder(self, cuerpo, tipo="application/json; charset=utf-8", codigo=200,
                   cache=None):
        if isinstance(cuerpo, str):
            cuerpo = cuerpo.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.send_header("Cache-Control", cache or "no-store")
        try:
            self.end_headers()
            self.wfile.write(cuerpo)
        except ConnectionError:
            # el celular se fue antes de la respuesta (en Windows es ConnectionAborted)
            self.close_connection = True

    def _json(self, dato):
        self._responder(json.dumps(dato))

    def _sid(self):
        """El identificador de sesión que trae el navegador, si trae alguno."""
        crudo = self.headers.get("Cookie") or ""
        for parte in crudo.split(";"):
            k, _, v = parte.strip().partition("=")
            if k == self.COOKIE:
                return v.strip()
        return None

    def _dar_cookie(self, sid, destino="/mando"):
        """Guarda la sesión y saca la clave de la barra de direcciones.

        El QR trae la clave en la URL. Si esa URL quedara en pantalla, la
        clave quedaría en el historial del navegador y a la vista del curso.
        Se canjea por una cookie y se redirige a la dirección limpia.

        HttpOnly: el javascript de la página no puede leerla.
        SameSite=Lax: otra página no puede mandar órdenes con esta sesión.
        """
        self.send_response(302)
        self.send_header("Location", destino)
        self.send_header(
            "Set-Cookie",
            "%s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d"
            % (self.COOKIE, sid, 8 * 3600))
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _borrar_cookie(self):
        self.send_response(302)
        self.send_header("Location", "/")
        self.send_header("Set-Cookie", "%s=; Path=/; Max-Age=0" % self.COOKIE)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _es_admin(self):
        """Sin control de acceso (acceso=None, uso en una computadora propia)
        todos son administradores; con control, sólo quien leyó el QR."""
        if self.acceso is None:
            return True
        return self.acceso.es_admin(self._sid())

    def _prohibido(self, motivo, codigo=403):
        """Una negativa que explica el motivo. El 409 significa "el mando lo
        tiene otro": la página de mando lo usa para ofrecer pedirlo."""
        self._responder(json.dumps({"ok": False, "motivo": motivo}),
                        "application/json; charset=utf-8", codigo)

    def _pagina(self, nombre):
        try:
            with open(os.path.join(self.estaticos, nombre), "rb") as f:
                self._responder(f.read(), "text/html; charset=utf-8")
        except OSError:
            self._responder("No se encontró la página " + nombre,
                            "text/plain; charset=utf-8", 500)

    # Sólo nombres simples: minúsculas, números y guion bajo. Así no hay forma
    # de pedir con /caratulas/ un archivo que esté fuera de esa carpeta.
    _NOMBRE_CARATULA = re.compile(r"^/caratulas/([a-z0-9_]{1,40})\.svg$")

    def _caratula(self, ruta):
        m = self._NOMBRE_CARATULA.match(ruta)
        if not m:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)
            return
        try:
            with open(os.path.join(self.estaticos, "caratulas", m.group(1) + ".svg"),
                      "rb") as f:
                # no-cache: después de actualizar, el kiosco y los celulares
                # piden la carátula nueva y no se quedan con la vieja.
                self._responder(f.read(), "image/svg+xml; charset=utf-8",
                                cache="no-cache")
        except OSError:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)

    def log_message(self, formato, *args):
        # Sin registro por pedido: cada celular hace cinco por segundo y la
        # consola se volvería ilegible.
        pass

    def do_GET(self):
        u = urlparse(self.path)
        ruta = u.path
        consulta = parse_qs(u.query)

        # para mirar: abierto para cualquiera
        if ruta in ("/", "/panel", "/tablero"):
            self._pagina("tablero.html")

        # para mandar: hace falta la clave del QR del profesor
        elif ruta in ("/mando", "/mando/"):
            clave = (consulta.get("k") or [""])[0]
            if clave and self.acceso:
                sid = self.acceso.entrar(clave)
                if sid:
                    self._dar_cookie(sid, "/mando")
                    return
                self._pagina("sin_permiso.html")
                return
            if self._es_admin():
                self._pagina("mando.html")
            else:
                self._pagina("sin_permiso.html")

        elif ruta == "/salir":
            if self.acceso:
                self.acceso.salir(self._sid())
            self._borrar_cookie()

        elif ruta == "/api/sesion":
            self._json(self.acceso.estado(self._sid()) if self.acceso
                       else {"admin": True, "mando": True, "mando_libre": True,
                             "hay_titular": False, "pedido_ajeno": False,
                             "pedido_mio": False, "admins": 0})

        elif ruta in ("/qr", "/qr/"):
            url = self._url_publica()
            self._responder(
                _PAGINA_QR % {"svg": qr.svg(url, 380), "url": url,
                              "donde": self.donde},
                "text/html; charset=utf-8")

        elif ruta == "/qr.svg":
            self._responder(qr.svg(self._url_publica(), 380),
                            "image/svg+xml; charset=utf-8")

        elif ruta == "/qr_wifi.svg":
            # el mismo dato del cartel pegado al tablero: la red de los
            # visitantes, no la de la escuela
            ap = datos_punto_de_acceso()
            wifi = "WIFI:S:%s;T:WPA;P:%s;;" % (ap["red"], ap["clave"])
            self._responder(qr.svg(wifi, 300), "image/svg+xml; charset=utf-8")

        elif ruta.startswith("/caratulas/"):
            self._caratula(ruta)

        elif ruta in ("/cartel", "/cartel/"):
            ap = datos_punto_de_acceso()
            # en el cartel va la dirección del punto de acceso: el que lo lee ya
            # se conectó a esa red con el primer código
            url = "http://%s:%d/" % (ap["ip"], self.puerto)
            wifi = "WIFI:S:%s;T:WPA;P:%s;;" % (ap["red"], ap["clave"])
            self._responder(
                _PAGINA_CARTEL % {"qr_wifi": qr.svg(wifi, 300),
                                  "qr_url": qr.svg(url, 300),
                                  "red": ap["red"], "clave": ap["clave"],
                                  "url": url.rstrip("/")},
                "text/html; charset=utf-8")

        elif ruta == "/api/catalogo":
            ap = datos_punto_de_acceso()
            self._json(dict(self.nucleo.catalogo,
                            url_publica=self._url_publica(),
                            admin=self._es_admin(),
                            caratulas=indice_caratulas(self.estaticos),
                            wifi={"red": ap["red"],
                                  "url": "http://%s:%d/" % (ap["ip"], self.puerto)}))

        elif ruta == "/api/estado":
            self._json(self.nucleo.foto)

        else:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)

    def do_POST(self):
        u = urlparse(self.path)
        ruta = u.path
        consulta = parse_qs(u.query)

        try:
            largo = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            largo = -1
        if not 0 <= largo <= CUERPO_MAX:
            self.close_connection = True
            self._responder("pedido demasiado grande", "text/plain; charset=utf-8", 413)
            return
        if largo:
            self.rfile.read(largo)

        sid = self._sid()

        # el mando: pedirlo, cederlo, tomarlo
        if ruta.startswith("/api/mando/"):
            if not self._es_admin():
                self._prohibido("Hace falta entrar con el QR del profesor.")
                return
            que = ruta.rsplit("/", 1)[-1]
            if self.acceso is None:
                # Sin control de acceso (--sin-clave, --banco) el mando es de todos:
                # no hay turno que pedir ni ceder.
                self._json({"ok": True, "motivo": ""})
                return
            if que == "tomar":
                ok, motivo = self.acceso.tomar_mando(sid)
                self._json({"ok": ok, "motivo": motivo})
            elif que == "pedir":
                self._json({"ok": self.acceso.pedir_mando(sid)})
            elif que == "ceder":
                self._json({"ok": self.acceso.ceder_mando(sid)})
            elif que == "rechazar":
                self._json({"ok": self.acceso.rechazar_pedido(sid)})
            elif que == "nombre":
                self.acceso.nombrar(sid, (consulta.get("valor") or [""])[0])
                self._json({"ok": True})
            else:
                self._responder("no encontrado",
                                "text/plain; charset=utf-8", 404)
            return

        # de acá para abajo, todo es dar órdenes al tablero
        if self.acceso is not None:
            if not self.acceso.es_admin(sid):
                self._prohibido("Esta página es para mirar. Para operar el "
                                "tablero hace falta el QR del profesor.")
                return
            if not self.acceso.puede_mandar(sid):
                self._prohibido("El mando lo tiene otro dispositivo.", 409)
                return

        if ruta.startswith("/api/modo/"):
            modo = ruta.rsplit("/", 1)[-1]
            ident = (consulta.get("id") or [""])[0]
            if modo == "1":
                self.nucleo.ordenar("modo_normal", ident or None)
            elif modo == "2":
                self.nucleo.ordenar("modo_escenario", ident)
            elif modo == "3":
                self.nucleo.ordenar("modo_falla", ident)
            else:
                self.nucleo.ordenar("detener")
            self._json({"ok": True})

        elif ruta.startswith("/api/accion/"):
            accion = ruta.rsplit("/", 1)[-1]
            if accion not in ACCIONES:
                self._responder("acción desconocida", "text/plain; charset=utf-8", 400)
                return
            crudo = (consulta.get("valor") or [""])[0]
            if crudo in ("true", "false"):
                valor = (crudo == "true")
            elif crudo == "":
                valor = None
            else:
                try:
                    valor = float(crudo)
                except ValueError:
                    valor = crudo
            self.nucleo.ordenar(accion, valor)
            self._json({"ok": True})

        else:
            self._responder("no encontrado", "text/plain; charset=utf-8", 404)


_INDICE = {}


def indice_caratulas(estaticos):
    """{instrumento: {archivo, L, R}} de static/caratulas/indice.json, o {}.

    Si la carpeta no está (una instalación vieja), la página dibuja sus
    esferas de antes: el tablero se ve igual, sólo que no idéntico al físico.
    """
    if estaticos not in _INDICE:
        try:
            with open(os.path.join(estaticos, "caratulas", "indice.json"),
                      encoding="utf-8") as f:
                _INDICE[estaticos] = json.load(f)
        except (OSError, ValueError, TypeError):
            _INDICE[estaticos] = {}
    return _INDICE[estaticos]


def crear(nucleo, puerto, estaticos, donde="esta computadora", acceso=None):
    """Deja el servidor listo para atender (no bloquea).

    acceso=None deja el servidor sin control de permisos: cualquiera que abra
    la página puede mandar. Sirve para probar en una computadora propia. En
    la Raspberry, que está en una red con alumnos, siempre se pasa un Acceso.
    """
    Manejador.nucleo = nucleo
    Manejador.estaticos = estaticos
    Manejador.puerto = puerto
    Manejador.donde = donde
    Manejador.acceso = acceso
    s = ThreadingHTTPServer(("0.0.0.0", puerto), Manejador)
    s.daemon_threads = True
    return s


def cartel_de_acceso(puerto, ancho=68):
    """El texto que se imprime en la terminal: dirección y código QR."""
    url = direccion(puerto)
    lineas = ["-" * ancho,
              " ENTRAR DESDE CUALQUIER CELULAR, TABLET O COMPUTADORA",
              "",
              "     %s" % url,
              "",
              " Escaneando este código con la cámara del teléfono:",
              ""]
    lineas.append(qr.texto_consola(url, borde=1))
    lineas += ["",
               " El mismo código, grande, para proyectar:  %sqr" % url,
               " Cartel A4 para imprimir y pegar:          %scartel" % url,
               "-" * ancho]
    return "\n".join(lineas)
