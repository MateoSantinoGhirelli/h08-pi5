# -*- coding: utf-8 -*-
"""Revisión de conexiones y de la instalación; no mueve nada.

    python3 -m h08 diagnostico              revisa todo
    python3 -m h08 diagnostico --cableado   la tabla de cables Raspberry -> placa
    python3 -m h08 diagnostico --guardar    además deja un informe en datos/informes/

Revisa en orden sistema, alimentación, I2C y placas, motor, servicio, pantalla, wifi
propia y archivos, y para cada cosa que falla dice el comando que la arregla. Se
puede correr con el servicio andando.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import urllib.request

from h08 import rutas
from h08.config import PLACAS, MOTORES, I2C_BUS, SERVO_CFG
from h08.herramientas import banco

AUTOSTART = os.path.expanduser("~/.config/autostart/tablero-kiosco.desktop")
PUERTO = 8000

CABLEADO = """
  CABLEADO RASPBERRY PI 5 -> PLACA MADRE (J1)
  --------------------------------------------------------------------------
   Función          GPIO     Pata del conector de 40 de la Raspberry
   3,3 V (lógica)    -        1
   SDA  (I2C)        GPIO2    3
   SCL  (I2C)        GPIO3    5
   GND               -        6, 9, 14, 20, 25, 30, 34, 39
   Motor IN1         GPIO12   32
   Motor IN2         GPIO16   36
   Motor IN3         GPIO20   38
   Motor IN4         GPIO21   40
   (libre: motor 0)  GPIO6/13/19/26   31/33/35/37
  --------------------------------------------------------------------------
  OJO, PLACA ESPEJADA: el cobre de la placa salió en espejo, así que en J1 las
  columnas par e impar quedaron cambiadas y el cable plano NO sirve. Se
  cablea pata por pata con Dupont hembra-hembra siguiendo esta tabla por
  FUNCIÓN (SDA con SDA, IN1 con IN1...), mirando la serigrafía de la placa
  que tienen en la mano. El programa no cambia: las funciones son las mismas.

  PCA9685
   PCA0  0x40  sin puentes        servos de vuelo y motor (canales 0-15)
   PCA1  0x41  puente A0 soldado  MAP, transmisión, eléctricos (0-5), luces (8-13)
   V+ de los dos módulos: 5 V de la fuente de servos (LM2596), NUNCA de la Pi.
   GND de la fuente y GND de la Pi: unidos.
  Luces: ánodo a +5 V (J8), cátodo por 220 ohm (R2..R7) al canal (J7).
"""


class Revision:
    def __init__(self, eco=True):
        self.filas = []            # (ok, texto, arreglo) ; ok None = sólo dato
        self.eco = eco
        self.seccion = ""

    def titulo(self, t):
        self.seccion = t
        self.filas.append(("T", t, None))
        if self.eco:
            print("\n  " + t)

    def decir(self, ok, texto, arreglo=None):
        self.filas.append((ok, texto, arreglo))
        if self.eco:
            print("   [%s] %s" % ("ok" if ok else "!!", texto))
            if not ok and arreglo:
                print("        -> " + arreglo)

    def dato(self, texto):
        self.filas.append((None, texto, None))
        if self.eco:
            print("        " + texto)

    def problemas(self):
        return [f for f in self.filas if f[0] is False]

    def texto(self):
        L = []
        for ok, t, arr in self.filas:
            if ok == "T":
                L += ["", " " + t]
            elif ok is None:
                L.append("        " + t)
            else:
                L.append("   [%s] %s" % ("ok" if ok else "!!", t))
                if not ok and arr:
                    L.append("        -> " + arr)
        return "\n".join(L)


def correr(cmd, t=10):
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=t).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def leer(ruta):
    try:
        with open(ruta, encoding="utf-8", errors="replace") as f:
            return f.read().strip("\x00\n ")
    except OSError:
        return ""


def grupos():
    try:
        import grp                  # sólo en Linux
    except ImportError:
        return []
    g = []
    for gid in os.getgroups():
        try:
            g.append(grp.getgrgid(gid).gr_name)
        except KeyError:
            pass
    return g


def http_json(ruta, t=3):
    try:
        with urllib.request.urlopen("http://localhost:%d%s" % (PUERTO, ruta), timeout=t) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception:
        return None


def revisar(eco=True):
    R = Revision(eco)
    soy_root = getattr(os, "geteuid", lambda: -1)() == 0
    g = grupos()

    R.titulo("1. SISTEMA")
    modelo = leer("/proc/device-tree/model")
    R.decir("Raspberry Pi 5" in modelo, "Placa: %s" % (modelo or "desconocida"),
            "el programa está pensado para la Raspberry Pi 5")
    so = ""
    for linea in leer("/etc/os-release").splitlines():
        if linea.startswith("PRETTY_NAME="):
            so = linea.split("=", 1)[1].strip('"')
    R.decir(any(n in so.lower() for n in ("bookworm", "trixie")),
            "Sistema: %s" % (so or "desconocido"),
            "usar Raspberry Pi OS Bookworm (64 bits) o posterior, CON escritorio")
    escritorio = [n for n in ("labwc", "wayfire", "lxsession") if correr(["which", n])]
    R.decir(bool(escritorio), "Escritorio instalado (%s)" % (", ".join(escritorio) or "ninguno"),
            "hace falta Raspberry Pi OS con escritorio para la pantalla del tablero")
    R.decir(sys.version_info >= (3, 9), "Python %d.%d" % sys.version_info[:2])
    version = leer(rutas.VERSION).splitlines()
    R.dato("versión instalada: %s" % (version[0] if version else "sin VERSION.txt"))

    R.titulo("2. ALIMENTACIÓN DE LA RASPBERRY")
    t = correr(["vcgencmd", "get_throttled"])
    if t.startswith("throttled="):
        v = int(t.split("=")[1], 16)
        R.decir(not v & 0x1, "Tensión bien ahora",
                "baja tensión: fuente oficial de 27 W (5,1 V 5 A) y su cable")
        R.decir(not v & 0x10000, "Sin baja tensión desde que arrancó",
                "hubo baja tensión: revisar fuente y cable USB-C. Si pasa cuando se "
                "mueven los servos, la masa de la fuente de servos está mal hecha")
        R.decir(not v & 0x4, "Sin recortes por temperatura", "ventilación de la Pi")
    else:
        R.dato("vcgencmd no disponible")
    adc = correr(["vcgencmd", "pmic_read_adc", "EXT5V_V"])
    m = re.search(r"=([0-9.]+)V", adc)
    if m:
        v5 = float(m.group(1))
        R.decir(v5 >= 4.85, "5 V de entrada de la Pi: %.2f V" % v5,
                "por debajo de 4,85 V: fuente o cable flojos")

    R.titulo("3. BUS I2C Y PLACAS PCA9685")
    dev = "/dev/i2c-%d" % I2C_BUS
    hay = os.path.exists(dev)
    R.decir(hay, "I2C habilitado (%s)" % dev, "sudo raspi-config nonint do_i2c 0   y reiniciar")
    cfg = leer("/boot/firmware/config.txt") or leer("/boot/config.txt")
    m = re.search(r"^dtparam=i2c_arm_baudrate=(\d+)", cfg, re.M)
    R.decir(bool(m), "Velocidad del bus: %s" % ("%s Hz" % m.group(1) if m else "100 kHz (de fábrica)"),
            "bash deploy/instalar.sh la deja en 400 kHz (con 100 kHz anda, pero más lento)")
    R.decir(soy_root or "i2c" in g, "Usuario en el grupo i2c",
            "sudo usermod -aG i2c $USER   y volver a iniciar sesión")
    servicio = banco.servicio_andando()
    if hay:
        try:
            from h08.hardware.pca9685 import BusI2C, PCA9685, MODE1, MODE2, PRESCALE
            # el mismo prescaler que escribe el servicio (121 para 50 Hz)
            pre_esperado = PCA9685(None, 0, SERVO_CFG["frecuencia_hz"]).prescale
            bus = BusI2C()
            encontrados = [d for d in range(0x03, 0x78) if bus.responde(d)]
            R.dato("en el bus hay: " + (", ".join("0x%02X" % d for d in encontrados) or "nada"))
            esperadas = set(PLACAS.values())
            for nombre, direccion in sorted(PLACAS.items()):
                ok = direccion in encontrados
                R.decir(ok, "%s responde en 0x%02X" % (nombre, direccion),
                        "revisar VCC 3,3 V, GND, SDA (GPIO2), SCL (GPIO3)%s"
                        % (" y el puente A0 soldado" if direccion == 0x41 else
                           " y que NO tenga puentes soldados"))
                if ok and servicio:
                    try:
                        m1 = bus.leer(direccion, MODE1, 1)[0]
                        m2 = bus.leer(direccion, MODE2, 1)[0]
                        pre = bus.leer(direccion, PRESCALE, 1)[0]
                        R.decir(pre == pre_esperado and (m2 & 0x04) and not (m1 & 0x10),
                                "%s configurada: %d Hz, salida totem-pole, despierta"
                                % (nombre, SERVO_CFG["frecuencia_hz"]),
                                "el servicio no la pudo configurar: ver journalctl -u %s" % banco.SERVICIO)
                    except OSError:
                        pass
            otras = [d for d in encontrados if d not in esperadas and d != 0x70]
            if 0x70 in encontrados:
                R.dato("0x70 es la dirección 'a todas' del PCA9685: es normal")
            if otras:
                R.dato("OJO, hay algo más en el bus: " + ", ".join("0x%02X" % d for d in otras))
            if encontrados and 0x40 not in encontrados and 0x41 in encontrados:
                R.dato("sólo 0x41: ¿la placa 0 tiene soldado el puente A0 por error?")
            bus.cerrar()
        except RuntimeError as e:
            R.decir(False, "Abrir el bus I2C", str(e).splitlines()[-1].strip())

    R.titulo("4. MOTOR PASO A PASO (GPIO)")
    try:
        import gpiozero                                   # noqa: F401
        R.decir(True, "gpiozero instalado")
    except ImportError:
        R.decir(False, "gpiozero instalado", "sudo apt install -y python3-gpiozero python3-lgpio")
    try:
        import lgpio                                      # noqa: F401
        R.decir(True, "lgpio instalado (la Pi 5 lo necesita)")
    except ImportError:
        R.decir(False, "lgpio instalado", "sudo apt install -y python3-lgpio")
    R.decir(soy_root or "gpio" in g, "Usuario en el grupo gpio",
            "sudo usermod -aG gpio $USER   y volver a iniciar sesión")
    for n, mo in sorted(MOTORES.items()):
        R.dato("motor %d (%s): GPIO %s, sentido %+d"
               % (n, mo["id"], ",".join(str(p) for p in mo["pines"]), mo["sentido"]))
    if not servicio:
        try:
            from gpiozero import DigitalOutputDevice
            ocupados = []
            for mo in MOTORES.values():
                for p in mo["pines"]:
                    try:
                        DigitalOutputDevice(p, initial_value=False).close()
                    except Exception:
                        ocupados.append(p)
            R.decir(not ocupados, "Pines del motor libres",
                    "GPIO ocupados %s: otro programa los usa (¿quedó abierto python3 -m h08 motor?)"
                    % ocupados)
        except ImportError:
            pass
    else:
        R.dato("(pines no revisados: los está usando el servicio, que es lo normal)")

    R.titulo("5. SERVICIO DEL TABLERO")
    R.decir(servicio, "Servicio %s andando" % banco.SERVICIO,
            "sudo systemctl start %s   (errores: journalctl -u %s -n 50)"
            % (banco.SERVICIO, banco.SERVICIO))
    R.decir(correr(["systemctl", "is-enabled", banco.SERVICIO]) == "enabled",
            "Arranca solo al encender", "sudo systemctl enable %s" % banco.SERVICIO)
    est = http_json("/api/estado")
    R.decir(est is not None, "La página contesta en http://localhost:%d/" % PUERTO,
            "el servicio no atiende: journalctl -u %s -n 50" % banco.SERVICIO)
    if est:
        hw = est.get("hardware") or {}
        R.dato("modo: %s   tiempo simulado: %.0f s" % (est.get("modo_nombre", "?"), est.get("t", 0)))
        if "errores_i2c" in hw:
            R.decir(not hw.get("faltan"), "Placas presentes desde el arranque",
                    "faltan %s: el servicio sigue sin ellas" % ", ".join(hw.get("faltan", [])))
            R.decir(hw.get("errores_i2c", 0) == 0,
                    "Errores del bus I2C: %d" % hw.get("errores_i2c", 0),
                    "cables SDA/SCL largos o sueltos, o GND sin unir. Último: %s"
                    % hw.get("ultimo_error", ""))
            R.decir(hw.get("reinicios_pca", 0) == 0,
                    "Reinicios de los PCA9685: %d" % hw.get("reinicios_pca", 0),
                    "se reinician por baja tensión: el 3,3 V del módulo o picos de los servos")
        else:
            R.decir(False, "El servicio maneja el hardware",
                    "está en modo simulado o no abrió el I2C: journalctl -u %s -n 50" % banco.SERVICIO)
        R.decir(hw.get("errores_programa", 0) == 0,
                "Errores del programa: %d" % hw.get("errores_programa", 0),
                "journalctl -u %s -n 100" % banco.SERVICIO)

    R.titulo("6. PANTALLA DE LA RASPBERRY (KIOSCO)")
    nav = [n for n in ("chromium", "chromium-browser") if correr(["which", n])]
    R.decir(bool(nav), "Chromium instalado", "sudo apt install -y chromium")
    auto = leer(AUTOSTART) + leer(os.path.expanduser("~/.config/labwc/autostart"))
    R.decir("kiosco.sh" in auto, "El tablero se abre solo al encender",
            "bash deploy/instalar.sh  (o quitado a propósito con --quitar-kiosco)")
    lightdm = leer("/etc/lightdm/lightdm.conf")
    R.decir(bool(re.search(r"^autologin-user=\S+", lightdm, re.M)),
            "El escritorio entra solo, sin contraseña",
            "sudo raspi-config nonint do_boot_behaviour B4")
    kiosco = correr(["pgrep", "-f", "tablero-kiosco"])
    R.dato("kiosco abierto ahora: %s" % ("sí" if kiosco else "no (normal si se entró por SSH)"))

    R.titulo("7. RED WIFI PROPIA")
    if correr(["which", "nmcli"]):
        conex = correr(["nmcli", "-t", "-f", "NAME", "connection", "show"]).splitlines()
        R.decir("tablero-ap" in conex, "Red Tablero-H08 creada",
                "sudo bash deploy/punto_de_acceso.sh preparar  (y reiniciar)")
        if "tablero-ap" in conex:
            ac = correr(["nmcli", "-g", "connection.autoconnect", "connection", "show", "tablero-ap"])
            R.decir(ac == "yes", "Se levanta sola al encender",
                    "sudo bash deploy/punto_de_acceso.sh permanente")
            activa = "tablero-ap" in correr(["nmcli", "-t", "-f", "NAME", "connection",
                                             "show", "--active"]).splitlines()
            R.decir(activa, "Levantada ahora", "sudo bash deploy/punto_de_acceso.sh encender")
            if activa:
                n = correr(["iw", "dev", "wlan0", "station", "dump"]).count("Station ")
                R.dato("celulares conectados: %d" % n)
    else:
        R.decir(False, "NetworkManager (nmcli)", "hace falta Raspberry Pi OS Bookworm o posterior")
    R.dato("direcciones: %s" % (correr(["hostname", "-I"]) or "ninguna"))

    R.titulo("8. ARCHIVOS")
    R.decir(os.access(rutas.DATOS, os.W_OK), "Se puede escribir en la carpeta de datos (%s)" % rutas.DATOS,
            "la clave, la calibración y la posición del motor se guardan ahí; si no existe, "
            "la crea el tablero al arrancar (o python3 -m h08 --qr-admin)")
    pendientes = rutas.datos_viejos()
    R.decir(not pendientes, "Sin datos viejos en raspberry_pi5/",
            "quedaron %s: el tablero los pasa a datos/ al arrancar; si siguen ahí es porque "
            "en datos/ ya había uno con el mismo nombre (elegir cuál va y borrar el otro)"
            % ", ".join(pendientes))
    R.decir(os.path.exists(rutas.CLAVE),
            "Clave de administrador generada", "python3 -m h08 --qr-admin")
    try:
        with open(rutas.CALIBRACION, encoding="utf-8") as f:
            ncal = len(json.load(f))
    except (OSError, ValueError):
        ncal = 0
    R.dato("servos calibrados: %d de 20 (los demás usan 500-2500 us)" % ncal)
    R.dato("posición del motor guardada: %s"
           % ("sí" if os.path.exists(rutas.MOTORES) else "no (arranca en 0°)"))
    ind = os.path.join(rutas.ESTATICOS, "caratulas", "indice.json")
    R.decir(os.path.exists(ind), "Carátulas de la página (h08/web/static/caratulas)",
            "faltan: la página usa sus esferas viejas. Volver a copiar el paquete")
    return R


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m h08 diagnostico",
                                 description="Diagnóstico del tablero H-08")
    ap.add_argument("--cableado", action="store_true")
    ap.add_argument("--guardar", action="store_true")
    a = ap.parse_args(argv)
    if a.cableado:
        print(CABLEADO)
        return 0
    print("\n  DIAGNÓSTICO DEL TABLERO H-08")
    R = revisar()
    malos = R.problemas()
    print("\n  %s\n" % ("Todo en orden." if not malos else "%d cosa(s) para revisar." % len(malos)))
    if a.guardar:
        os.makedirs(rutas.INFORMES, exist_ok=True)
        ruta = os.path.join(rutas.INFORMES, "diagnostico_%s.txt"
                            % datetime.datetime.now().strftime("%Y%m%d_%H%M"))
        with open(ruta, "w", encoding="utf-8") as f:
            f.write("DIAGNÓSTICO DEL TABLERO H-08  %s\n" %
                    datetime.datetime.now().strftime("%d/%m/%Y %H:%M"))
            f.write(R.texto() + "\n")
        print("  Guardado en: %s\n" % ruta)
    return 0 if not malos else 1


if __name__ == "__main__":
    sys.exit(main())
