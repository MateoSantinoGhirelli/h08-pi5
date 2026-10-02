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
  SERVIDOR   /caratulas/ no deja salir de su carpeta, /qr_wifi.svg, el
             catálogo trae barrido y centro, y el mando sin clave no se cae
  PRUEBAS    las pruebas guiadas de la Pi corren en modo --simulado --auto
  SCRIPTS    los .sh no tienen errores de sintaxis
"""

import http.client
import json
import os
import re
import subprocess
import sys
import tempfile
import threading

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)
PI = os.path.join(RAIZ, "raspberry_pi5")
sys.path.insert(0, os.path.join(RAIZ, "nucleo"))
sys.path.insert(0, PI)

from configuracion import TABLERO, PANEL_VIRTUAL, LED            # noqa: E402
from actuadores_simulados import ActuadoresSimulados              # noqa: E402
from simulador import Simulador                                   # noqa: E402

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
    carpeta = os.path.join(PI, "web", "caratulas")
    try:
        with open(os.path.join(carpeta, "indice.json"), encoding="utf-8") as f:
            ind = json.load(f)
    except (OSError, ValueError):
        ind = {}
    cierto("existe web/caratulas/indice.json", bool(ind))
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
    import servidor_web
    from hilo_simulacion import HiloSimulacion
    nucleo = HiloSimulacion(ActuadoresSimulados(), semilla=1)
    nucleo.start()
    puerto = servidor_web.puerto_libre(8150)
    srv = servidor_web.crear(nucleo, puerto, os.path.join(PI, "web"), acceso=None)
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
def probar_guiadas():
    print("\n PRUEBAS GUIADAS DE LA PI (--simulado --auto)")
    tmp = tempfile.mkdtemp(prefix="h08_informes_")
    env = dict(os.environ, H08_INFORMES=tmp, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    for args in (["prueba_instrumento.py", "AIRSPEED"], ["prueba_instrumento.py", "COMPASS"],
                 ["prueba_instrumento.py", "LT_GEN"], ["prueba_luces_motor.py", "--luces"],
                 ["prueba_general.py", "--solo", "A"]):
        r = subprocess.run([sys.executable, os.path.join(PI, args[0])] + args[1:] +
                           ["--simulado", "--auto"], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=240, env=env, cwd=PI)
        cierto(" ".join(args), r.returncode == 0 and "TODO BIEN" in r.stdout,
               (r.stdout + r.stderr)[-400:])
    cierto("los informes van a su carpeta", len(os.listdir(tmp)) == 5, os.listdir(tmp))
    r = subprocess.run([sys.executable, os.path.join(PI, "diagnostico_pi.py"), "--cableado"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=30, cwd=PI, env=env)
    cierto("diagnostico_pi.py --cableado", r.returncode == 0 and "GPIO12" in r.stdout)


def probar_scripts():
    print("\n SCRIPTS DE LA PI")
    for sh in sorted(f for f in os.listdir(PI) if f.endswith(".sh")):
        # En Windows el "bash" que aparece suele ser el de WSL o el de Git, que
        # no entienden las rutas C:\...: la sintaxis se comprueba en Linux/Pi.
        if os.name == "nt":
            print("  --   %s: la sintaxis de bash se comprueba en Linux, salteado" % sh)
            continue
        try:
            r = subprocess.run(["bash", "-n", os.path.join(PI, sh)], capture_output=True,
                               text=True, encoding="utf-8", errors="replace", timeout=30)
        except (OSError, subprocess.SubprocessError):
            print("  --   %s: sin bash en este sistema, salteado" % sh)
            continue
        cierto("%s sin errores de sintaxis" % sh, r.returncode == 0, r.stderr)
    texto = open(os.path.join(PI, "instalar.sh"), encoding="utf-8").read()
    cierto("instalar.sh deja el kiosco, el inicio solo y la red propia",
           all(k in texto for k in ("kiosco.sh", "do_boot_behaviour B4", "do_blanking 1",
                                    "punto_de_acceso.sh\" preparar")))
    cierto("actualizar.sh no pisa la clave, la calibración ni el motor",
           all(re.search(r"--exclude '%s'" % re.escape(n),
                         open(os.path.join(PI, "actualizar.sh"), encoding="utf-8").read())
               for n in ("secreto_admin.json", "calibracion_servos.json",
                         "posicion_motores.json")))


def main():
    probar_luces()
    probar_caratulas()
    probar_servidor()
    probar_scripts()
    probar_guiadas()
    print("\n" + ("Todas bien." if not fallos else "FALLARON %d: %s" % (len(fallos), ", ".join(fallos))))
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
