#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prueba_pi5.py - lo agregado para la Raspberry, probado sin la Raspberry
=======================================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

    python3 pruebas/prueba_pi5.py

  LUCES      cada falla enciende SU luz; en crucero normal sólo IGNITION;
             la prueba de lámparas llega al estado que lee la página; sin
             energía se apagan todas aunque la alarma siga
  CARÁTULAS  la página tiene la carátula de cada instrumento que se dibuja,
             sin el fondo blanco ni las líneas de corte de imprenta
  SERVIDOR   /caratulas/ no deja salir de su carpeta, /qr_wifi.svg con la red
             de deploy/punto_de_acceso.sh, el catálogo trae barrido y centro,
             y el mando sin clave no se cae
  RUTAS      h08/rutas.py da las mismas rutas que usaba la versión anterior y
             ningún otro módulo arma rutas de datos por su cuenta
  COMANDO    python3 -m h08 --help lista los subcomandos y cada uno contesta
  PRUEBAS    las pruebas guiadas de la Pi corren en modo --simulado --auto
  SCRIPTS    los .sh no tienen errores de sintaxis; instalar.sh limpia la
             versión vieja y escribe el servicio con python3 -m h08
"""

import http.client
import json
import os
import re
import subprocess
import sys
import tempfile
import threading

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)          # hasta pasar a unittest (fase 4)

from h08 import rutas  # noqa: E402
from h08.__main__ import SUBCOMANDOS  # noqa: E402
from h08.config import TABLERO, PANEL_VIRTUAL, LED  # noqa: E402
from h08.hardware.simulado import ActuadoresSimulados  # noqa: E402
from h08.simulacion.simulador import Simulador  # noqa: E402

DEPLOY = os.path.join(RAIZ, "deploy")
ENV = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")

fallos = []


def cierto(nombre, v, detalle=""):
    print("  %s %s%s" % ("ok  " if v else "MAL ", nombre, "" if v else "   " + str(detalle)))
    if not v:
        fallos.append(nombre)


# ===========================================================================
def correr(sim, seg, dt=0.05):
    for _ in range(int(seg / dt)):
        sim.paso(dt)
        sim.mapa.escribir()


def luces_encendidas(sim):
    e = sim.estado()["instrumentos"]
    return set(it["id"] for it in TABLERO if it["actuador"] == LED and e[it["id"]]["ang"] >= 0.5)


def probar_luces():
    print("\n LUCES DE ALERTA")
    for falla, luz, seg in (("GEN_FAIL", "LT_GEN", 10), ("XMSN_PRESS_LOSS", "LT_XMSN_PRESS", 40),
                            ("LOW_ROTOR_RPM", "LT_LOW_ROTOR", 80),
                            ("FUEL_STARVATION", "LT_FUEL_FWD", 10)):
        sim = Simulador(ActuadoresSimulados(), semilla=1)
        sim.modo_falla(falla)
        vista = False
        for _ in range(int(seg / 1.0)):
            correr(sim, 1.0)
            if luz in luces_encendidas(sim):
                vista = True
                break
        cierto("%s enciende %s antes de %d s" % (falla, luz, seg), vista)

    sim = Simulador(ActuadoresSimulados(), semilla=1)
    sim.modo_falla("PITOT_BLOCK")           # crucero; la falla no toca luces
    correr(sim, 20)
    cierto("crucero: sólo IGNITION encendida", luces_encendidas(sim) == {"LT_STARTER"},
           luces_encendidas(sim))

    sim.prueba_luces(True)
    correr(sim, 0.2)
    cierto("prueba de lámparas: la página ve las seis", len(luces_encendidas(sim)) == 6)
    act = sim.mapa.actuadores
    cierto("prueba de lámparas: las seis salidas encendidas",
           all(act.valores.get("%s:%d" % tuple(it["canal"])) == 1
               for it in TABLERO if it["actuador"] == LED))
    sim.prueba_luces(False)
    correr(sim, 0.2)
    cierto("fin de la prueba: vuelve a sólo IGNITION", luces_encendidas(sim) == {"LT_STARTER"})

    sim = Simulador(ActuadoresSimulados(), semilla=1)
    sim.modo_falla("ELEC_TOTAL")
    correr(sim, 120)
    cierto("sin energía eléctrica: todas apagadas", luces_encendidas(sim) == set(),
           luces_encendidas(sim))


# ===========================================================================
def probar_caratulas():
    print("\n CARÁTULAS DE LA PÁGINA")
    carpeta = os.path.join(rutas.ESTATICOS, "caratulas")
    try:
        with open(os.path.join(carpeta, "indice.json"), encoding="utf-8") as f:
            ind = json.load(f)
    except (OSError, ValueError):
        ind = {}
    cierto("existe h08/web/static/caratulas/indice.json", bool(ind))
    con_dibujo = [it["id"] for it in list(TABLERO) + list(PANEL_VIRTUAL)
                  if it.get("pos") and it.get("dial") != "horizonte"]
    faltan = [i for i in con_dibujo if i not in ind]
    cierto("hay carátula para los %d instrumentos que se dibujan" % len(con_dibujo),
           not faltan, faltan)
    sucias = []
    for ident, c in ind.items():
        ruta = os.path.join(carpeta, c["archivo"])
        try:
            t = open(ruta, encoding="utf-8").read()
        except OSError:
            sucias.append(c["archivo"] + " (no está)")
            continue
        if 'fill="#FFFFFF"' in t or "stroke-dasharray" in t or 'width="' in t.split(">")[0]:
            sucias.append(c["archivo"])
        if not (0 < c["R"] < c["L"] / 2.0):
            sucias.append(c["archivo"] + " (medidas)")
    cierto("sin fondo blanco, sin líneas de corte, medidas coherentes", not sucias, sucias)


# ===========================================================================
class Cliente:
    def __init__(self, puerto):
        self.puerto = puerto

    def pedir(self, metodo, ruta):
        c = http.client.HTTPConnection("localhost", self.puerto, timeout=5)
        c.request(metodo, ruta, body=b"" if metodo == "POST" else None)
        r = c.getresponse()
        b = r.read()
        c.close()
        return r.status, b, r.getheader("Content-Type") or ""


def probar_servidor():
    print("\n SERVIDOR")
    from h08.web import servidor as servidor_web
    from h08.simulacion.hilo import HiloSimulacion
    nucleo = HiloSimulacion(ActuadoresSimulados(), semilla=1)
    nucleo.start()
    puerto = servidor_web.puerto_libre(8150)
    srv = servidor_web.crear(nucleo, puerto, rutas.ESTATICOS, acceso=None)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    c = Cliente(puerto)
    try:
        s, b, t = c.pedir("GET", "/caratulas/airspeed.svg")
        cierto("/caratulas/airspeed.svg se sirve como SVG", s == 200 and "svg" in t and b"<svg" in b)
        for malo in ("/caratulas/../secreto_admin.json", "/caratulas/..%2fsecreto_admin.svg",
                     "/caratulas/AIRSPEED.svg", "/caratulas/indice.json", "/caratulas/"):
            s, _, _ = c.pedir("GET", malo)
            cierto("rechaza %s" % malo, s == 404, s)
        s, b, t = c.pedir("GET", "/qr_wifi.svg")
        cierto("/qr_wifi.svg", s == 200 and b"<svg" in b)
        with open(rutas.PUNTO_DE_ACCESO, encoding="utf-8") as f:
            script = f.read()
        en_script = dict((campo, re.search(r'^%s="([^"]*)"' % var, script, re.M).group(1))
                         for campo, var in (("red", "RED"), ("clave", "CLAVE"), ("ip", "IP")))
        ap = servidor_web.datos_punto_de_acceso()
        cierto("la red, la clave y la IP del QR salen de deploy/punto_de_acceso.sh",
               ap == en_script and ap["clave"] != "", (ap, en_script))
        s, b, _ = c.pedir("GET", "/api/catalogo")
        cat = json.loads(b.decode("utf-8"))
        ins = {i["id"]: i for i in cat["instrumentos"]}
        cierto("el catálogo trae las carátulas", "AIRSPEED" in cat.get("caratulas", {}))
        cierto("el catálogo trae barrido y centro (VSI con el cero a las 9)",
               ins["AIRSPEED"]["barrido"] == 300 and ins["VSI"]["centro"] == 180.0
               and ins["COMPASS"]["barrido"] == "CONT")
        cierto("el catálogo trae la red wifi", cat.get("wifi", {}).get("red") == "Tablero-H08")
        s, b, _ = c.pedir("POST", "/api/mando/tomar")
        cierto("sin clave (--banco): tomar el mando no rompe el servidor",
               s == 200 and json.loads(b.decode("utf-8"))["ok"])
        s, b, _ = c.pedir("GET", "/?kiosco=1")
        cierto("la página del kiosco se sirve", s == 200 and b"kiosco" in b)
    finally:
        srv.shutdown()
        srv.server_close()
        nucleo.detener()
        nucleo.join(5)


# ===========================================================================
def h08(args, env=ENV, timeout=60):
    """Corre python3 -m h08 ARGS desde la raíz, como en la Pi."""
    return subprocess.run([sys.executable, "-m", "h08"] + list(args), capture_output=True,
                          text=True, encoding="utf-8", errors="replace", timeout=timeout,
                          env=env, cwd=RAIZ)


def probar_rutas():
    print("\n RUTAS (h08/rutas.py)")
    # Lo que armaba cada archivo de la versión anterior: tablero_pi5.py y banco.py
    # con su propia carpeta, raspberry_pi5/, e interactivo.py con H08_INFORMES.
    vieja = os.path.join(RAIZ, "raspberry_pi5")
    esperadas = {
        "RAIZ": RAIZ,
        "VERSION": os.path.join(RAIZ, "VERSION.txt"),
        "DATOS": vieja,
        "CLAVE": os.path.join(vieja, "secreto_admin.json"),
        "CALIBRACION": os.path.join(vieja, "calibracion_servos.json"),
        "MOTORES": os.path.join(vieja, "posicion_motores.json"),
        "ESTATICOS": os.path.join(RAIZ, "h08", "web", "static"),
        "PUNTO_DE_ACCESO": os.path.join(RAIZ, "deploy", "punto_de_acceso.sh"),
    }
    for nombre, ruta in esperadas.items():
        cierto("rutas.%s = %s" % (nombre, os.path.relpath(ruta, RAIZ)),
               os.path.normcase(getattr(rutas, nombre)) == os.path.normcase(ruta),
               getattr(rutas, nombre))
    cierto("la página y el script de la red están donde dice rutas.py",
           os.path.isfile(os.path.join(rutas.ESTATICOS, "tablero.html"))
           and os.path.isfile(rutas.PUNTO_DE_ACCESO))

    leer = ["-c", "from h08 import rutas; print(rutas.INFORMES)"]
    sin = dict(ENV)
    sin.pop("H08_INFORMES", None)
    r = subprocess.run([sys.executable] + leer, capture_output=True, text=True, env=sin, cwd=RAIZ)
    cierto("rutas.INFORMES = raspberry_pi5/informes",
           os.path.normcase(r.stdout.strip()) == os.path.normcase(os.path.join(vieja, "informes")),
           r.stdout + r.stderr)
    otra = tempfile.mkdtemp(prefix="h08_inf_")
    r = subprocess.run([sys.executable] + leer, capture_output=True, text=True,
                       env=dict(sin, H08_INFORMES=otra), cwd=RAIZ)
    cierto("H08_INFORMES cambia la carpeta de informes", r.stdout.strip() == otra,
           r.stdout + r.stderr)

    # Que nadie vuelva a armar las rutas de los datos por su cuenta.
    propios = re.compile(r"""["'](secreto_admin|calibracion_servos|posicion_motores)\.json["']"""
                         r"""|["']VERSION\.txt["']|["']informes["']|sys\.path\.insert""")
    culpables = []
    for base, dirs, fs in os.walk(os.path.join(RAIZ, "h08")):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in fs:
            ruta = os.path.join(base, f)
            if f.endswith(".py") and os.path.normcase(ruta) != os.path.normcase(rutas.__file__):
                if propios.search(open(ruta, encoding="utf-8").read()):
                    culpables.append(os.path.relpath(ruta, RAIZ))
    cierto("sólo rutas.py nombra los archivos de datos (y nadie toca sys.path)",
           not culpables, culpables)


def probar_comando():
    print("\n COMANDO python3 -m h08")
    r = h08(["--help"])
    cierto("python3 -m h08 --help lista los %d subcomandos" % len(SUBCOMANDOS),
           r.returncode == 0 and all(s in r.stdout for s in SUBCOMANDOS), r.stdout + r.stderr)
    for sub in SUBCOMANDOS:
        r = h08([sub, "--help"])
        cierto("python3 -m h08 %s --help" % sub,
               r.returncode == 0 and ("python3 -m h08 " + sub) in r.stdout,
               (r.stdout + r.stderr)[-300:])


def probar_guiadas():
    print("\n PRUEBAS GUIADAS DE LA PI (--simulado --auto)")
    tmp = tempfile.mkdtemp(prefix="h08_informes_")
    env = dict(ENV, H08_INFORMES=tmp)
    for args in (["instrumento", "AIRSPEED"], ["instrumento", "COMPASS"],
                 ["instrumento", "LT_GEN"], ["luces-motor", "--luces"],
                 ["prueba-general", "--solo", "A"]):
        r = h08(args + ["--simulado", "--auto"], env=env, timeout=240)
        cierto("python3 -m h08 " + " ".join(args),
               r.returncode == 0 and "TODO BIEN" in r.stdout, (r.stdout + r.stderr)[-400:])
    cierto("los informes van a su carpeta", len(os.listdir(tmp)) == 5, os.listdir(tmp))
    r = h08(["diagnostico", "--cableado"], env=env, timeout=30)
    cierto("python3 -m h08 diagnostico --cableado", r.returncode == 0 and "GPIO12" in r.stdout)


def probar_scripts():
    print("\n SCRIPTS DE LA PI (deploy/)")
    for sh in sorted(f for f in os.listdir(DEPLOY) if f.endswith(".sh")):
        # En Windows el "bash" que aparece suele ser el de WSL o el de Git, que
        # no entienden las rutas C:\...: la sintaxis se comprueba en Linux/Pi.
        if os.name == "nt":
            print("  --   %s: la sintaxis de bash se comprueba en Linux, salteado" % sh)
            continue
        try:
            r = subprocess.run(["bash", "-n", os.path.join(DEPLOY, sh)], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=30)
        except (OSError, subprocess.SubprocessError):
            print("  --   %s: sin bash en este sistema, salteado" % sh)
            continue
        cierto("%s sin errores de sintaxis" % sh, r.returncode == 0, r.stderr)
    texto = open(os.path.join(DEPLOY, "instalar.sh"), encoding="utf-8").read()
    cierto("instalar.sh deja el kiosco, el inicio solo y la red propia",
           all(k in texto for k in ("kiosco.sh", "do_boot_behaviour B4", "do_blanking 1",
                                    "punto_de_acceso.sh\" preparar")))
    cierto("instalar.sh escribe el servicio con python3 -m h08 desde la raíz",
           "ExecStart=/usr/bin/python3 -m h08\n" in texto
           and "WorkingDirectory=$RAIZ\n" in texto and "tablero_pi5" not in texto)
    cierto("instalar.sh limpia el kiosco y el servicio de la versión vieja",
           all(k in texto for k in ("sed -i '/kiosco\\.sh/d' \"$LABWC\"",
                                    "rm -f \"$AUTOSTART\"",
                                    "sudo systemctl stop \"$SERVICIO\"")))
    m = re.search(r'^DATOS="\$RAIZ/([^"]+)"', texto, re.M)
    cierto("instalar.sh protege la clave en la misma carpeta que rutas.DATOS",
           m is not None and os.path.normcase(os.path.join(RAIZ, m.group(1)))
           == os.path.normcase(rutas.DATOS))
    act = open(os.path.join(DEPLOY, "actualizar.sh"), encoding="utf-8").read()
    cierto("actualizar.sh no pisa la clave, la calibración ni el motor",
           all(re.search(r"--exclude '%s'" % re.escape(n), act)
               for n in ("secreto_admin.json", "calibracion_servos.json",
                         "posicion_motores.json")))
    cierto("actualizar.sh reconoce el paquete nuevo por h08/__main__.py",
           "h08/__main__.py" in act and "tablero_pi5" not in act)


def main():
    probar_luces()
    probar_caratulas()
    probar_servidor()
    probar_rutas()
    probar_comando()
    probar_scripts()
    probar_guiadas()
    print("\n" + ("Todas bien." if not fallos else "FALLARON %d: %s" % (len(fallos), ", ".join(fallos))))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
