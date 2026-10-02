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
import shutil
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


def rutas_con(**variables):
    """Las rutas que da h08/rutas.py en un proceso nuevo, con esas variables de entorno."""
    env = dict(ENV)
    env.pop("H08_DATOS", None)
    env.pop("H08_INFORMES", None)
    env.update(variables)
    codigo = ("import json; from h08 import rutas; print(json.dumps(dict((k, getattr(rutas, k))"
              " for k in dir(rutas) if k.isupper())))")
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                       env=env, cwd=RAIZ)
    return json.loads(r.stdout) if r.returncode == 0 else {"error": r.stderr}


def mismas(a, b):
    return os.path.normcase(os.path.abspath(a)) == os.path.normcase(os.path.abspath(b))


def probar_rutas():
    print("\n RUTAS (h08/rutas.py)")
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
        cierto("rutas.%s = %s" % (nombre, os.path.relpath(ruta, RAIZ)),
               nombre in reales and mismas(reales[nombre], ruta), reales.get(nombre, reales))
    cierto("la página y el script de la red están donde dice rutas.py",
           os.path.isfile(os.path.join(rutas.ESTATICOS, "tablero.html"))
           and os.path.isfile(rutas.PUNTO_DE_ACCESO))

    otra = tempfile.mkdtemp(prefix="h08_datos_")
    con = rutas_con(H08_DATOS=otra)
    cierto("H08_DATOS mueve la clave, la calibración, el motor y los informes",
           all(mismas(os.path.dirname(con[k]), otra)
               for k in ("CLAVE", "CALIBRACION", "MOTORES", "INFORMES")), con)
    cierto("con H08_DATOS no hay mudanza desde raspberry_pi5/", con.get("VIEJA", 1) is None, con)
    inf = tempfile.mkdtemp(prefix="h08_inf_")
    cierto("H08_INFORMES cambia sólo la carpeta de informes",
           mismas(rutas_con(H08_INFORMES=inf)["INFORMES"], inf))

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


def escribir(ruta, texto):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        f.write(texto)


def leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def probar_migracion():
    print("\n MUDANZA DE raspberry_pi5/ A datos/ (archivos de mentira)")
    base = tempfile.mkdtemp(prefix="h08_mudanza_")
    vieja, nueva = os.path.join(base, "raspberry_pi5"), os.path.join(base, "datos")
    for n in rutas.PRIVADOS:
        escribir(os.path.join(vieja, n), "de mentira: " + n)
    escribir(os.path.join(vieja, "informes", "uno.txt"), "informe 1")
    avisos = []
    conflictos = rutas.migrar_datos_viejos(vieja, nueva, avisos.append)
    cierto("pasa los tres archivos y los informes",
           all(leer(os.path.join(nueva, n)) == "de mentira: " + n for n in rutas.PRIVADOS)
           and leer(os.path.join(nueva, "informes", "uno.txt")) == "informe 1", os.listdir(nueva))
    cierto("avisa cada cosa que mueve, sin conflictos", len(avisos) == 4 and not conflictos,
           avisos)
    cierto("borra raspberry_pi5/ porque quedó vacía",
           not os.path.exists(vieja) and rutas.datos_viejos(vieja) == [])
    avisos = []
    cierto("la segunda vez no hace nada",
           rutas.migrar_datos_viejos(vieja, nueva, avisos.append) == [] and not avisos, avisos)

    # Los dos lados con datos: no se pisa nada y decide una persona.
    escribir(os.path.join(vieja, "secreto_admin.json"), "la vieja")
    escribir(os.path.join(vieja, "informes", "uno.txt"), "otro informe 1")
    escribir(os.path.join(vieja, "informes", "dos.txt"), "informe 2")
    avisos = []
    conflictos = rutas.migrar_datos_viejos(vieja, nueva, avisos.append)
    cierto("con la clave en los dos lados, no pisa la de datos/",
           leer(os.path.join(nueva, "secreto_admin.json")) == "de mentira: secreto_admin.json"
           and leer(os.path.join(vieja, "secreto_admin.json")) == "la vieja")
    cierto("informes: pasa los que faltan y deja los repetidos",
           leer(os.path.join(nueva, "informes", "dos.txt")) == "informe 2"
           and leer(os.path.join(nueva, "informes", "uno.txt")) == "informe 1"
           and os.path.exists(os.path.join(vieja, "informes", "uno.txt")))
    cierto("devuelve y avisa los dos conflictos", len(conflictos) == 2
           and sum("sin mover" in a for a in avisos) == 2, (conflictos, avisos))
    cierto("el diagnóstico ve lo que quedó en raspberry_pi5/",
           rutas.datos_viejos(vieja) == ["secreto_admin.json", "informes"],
           rutas.datos_viejos(vieja))

    # De punta a punta: una copia del programa con datos viejos, como una Pi
    # actualizada, arranca con --qr-admin y tiene que usar la clave que estaba.
    copia = os.path.join(base, "H08_Pi5")
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
    cierto("al arrancar, la clave vieja pasa a datos/ y se usa (no se hace otra)",
           r.returncode == 0 and clave in r.stdout and os.path.isfile(movida)
           and json.loads(leer(movida))["clave"] == clave
           and not os.path.exists(os.path.join(copia, "raspberry_pi5")),
           (r.stdout + r.stderr)[-400:])
    nada = os.path.join(base, "no_existe")
    r = subprocess.run([sys.executable, "-m", "h08", "--help"], capture_output=True, text=True,
                       env=dict(sin, H08_DATOS=nada), cwd=copia, timeout=60)
    cierto("python3 -m h08 --help no crea ni mueve datos",
           r.returncode == 0 and not os.path.exists(nada)
           and os.path.isfile(movida))

    # Con H08_DATOS (pruebas, PC de desarrollo) la clave de raspberry_pi5/ no se toca.
    quieta = os.path.join(copia, "raspberry_pi5", "secreto_admin.json")
    escribir(quieta, json.dumps({"clave": "otraClaveDeMentira99"}))
    aparte = os.path.join(base, "aparte")
    r = subprocess.run([sys.executable, "-m", "h08", "--qr-admin"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       env=dict(sin, H08_DATOS=aparte), cwd=copia, timeout=60)
    cierto("con H08_DATOS, la clave de raspberry_pi5/ queda donde está",
           r.returncode == 0 and os.path.isfile(quieta)
           and json.loads(leer(quieta))["clave"] == "otraClaveDeMentira99"
           and os.path.isfile(os.path.join(aparte, "secreto_admin.json"))
           and "otraClaveDeMentira99" not in r.stdout, (r.stdout + r.stderr)[-300:])
    shutil.rmtree(base, ignore_errors=True)


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
           m is not None and mismas(os.path.join(RAIZ, m.group(1)), rutas_con()["DATOS"]))
    act = open(os.path.join(DEPLOY, "actualizar.sh"), encoding="utf-8").read()
    cierto("actualizar.sh no pisa la clave, la calibración ni el motor",
           all(re.search(r"--exclude '%s'" % re.escape(n), act)
               for n in ("secreto_admin.json", "calibracion_servos.json",
                         "posicion_motores.json")))
    cierto("actualizar.sh borra lo viejo (--delete) sin tocar datos/ ni raspberry_pi5/",
           "rsync -a --delete" in act and "--exclude '/datos/'" in act
           and "--exclude '/raspberry_pi5/'" in act)
    cierto("actualizar.sh reconoce el paquete nuevo por h08/__main__.py",
           "h08/__main__.py" in act and "tablero_pi5" not in act)


def main():
    probar_luces()
    probar_caratulas()
    probar_servidor()
    probar_rutas()
    probar_migracion()
    probar_comando()
    probar_scripts()
    probar_guiadas()
    print("\n" + ("Todas bien." if not fallos else "FALLARON %d: %s" % (len(fallos), ", ".join(fallos))))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
