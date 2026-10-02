# -*- coding: utf-8 -*-
"""
h08/hardware/pca9685.py - servos y luces sobre dos PCA9685 por I2C
================================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
EEST N° 7 - Taller Regional Quilmes

EL CHIP
---------------------------------------------------------------------------
El PCA9685 genera 16 salidas PWM de 12 bits (4096 cuentas por período) con
una base de tiempo común. La frecuencia se fija con el PRESCALER:

        prescale = round(25 MHz / (4096 · f)) - 1        (121 para 50 Hz)

A 50 Hz el período es de 20 ms y cada cuenta vale 4,88 us. Un servo usa
pulsos de 500 a 2500 us, o sea de 102 a 512 cuentas: unos 410 pasos para
180 grados, 0,44 grados por paso.

Cada canal ocupa cuatro registros seguidos (ON_L, ON_H, OFF_L, OFF_H). Con
el AUTOINCREMENTO de MODE1 activado se escriben varios canales seguidos en
una sola transacción. Dos bits especiales fijan la salida sin PWM:

        bit 4 de ON_H  ->  salida siempre en ALTO  ("full ON")
        bit 4 de OFF_H ->  salida siempre en BAJO  ("full OFF", tiene prioridad)

Se usan para las luces, que son todo o nada, y para soltar los servos (sin
pulso el servo no hace fuerza ni zumba).

EL BUS
---------------------------------------------------------------------------
Se habla con el dispositivo /dev/i2c-1 del kernel usando sólo la biblioteca
estándar (os + fcntl): no hace falta instalar nada. Cada escritura es una
transacción: dirección del registro seguida de los datos.

CUIDADOS
---------------------------------------------------------------------------
  * Luces invertidas: ver LUCES_ACTIVAS_EN_BAJO en h08/config/hardware.py.
  * Si el PCA9685 se reinicia (una caída de tensión fuerte), vuelve dormido,
    sin autoincremento y con todas las salidas en bajo. Cada dos segundos se
    lee MODE1; si el chip se reinició, se lo vuelve a configurar y se le
    reenvían todos los canales.
  * Un error de bus no detiene el tablero: se cuenta, y los canales que no se
    pudieron escribir se reintentan en el ciclo siguiente.
"""

try:
    import fcntl            # sólo existe en Linux (la Raspberry)
except ImportError:         # en Windows se puede correr todo en modo simulado
    fcntl = None
import json
import logging
import os
import time

from h08.util import limitar
from h08.config import (SERVO_CFG, LUCES_ACTIVAS_EN_BAJO, I2C_BUS, PLACAS,
                        TABLERO, LED, invertido)
from h08.hardware.base import ActuadoresBase

log = logging.getLogger(__name__)

# --- Registros y bits del PCA9685 -----------------------------------------
MODE1 = 0x00
MODE2 = 0x01
LED0_ON_L = 0x06
PRESCALE = 0xFE

M1_RESTART = 0x80
M1_AI = 0x20            # autoincremento de dirección de registro
M1_SLEEP = 0x10
M2_OUTDRV = 0x04        # salida totem-pole: obligatoria para los servos

OSCILADOR_HZ = 25000000.0

# Cuatro bytes de canal (ON_L, ON_H, OFF_L, OFF_H) para los estados fijos
SALIDA_ALTA = (0x00, 0x10, 0x00, 0x00)     # full ON
SALIDA_BAJA = (0x00, 0x00, 0x00, 0x10)     # full OFF

I2C_SLAVE = 0x0703      # ioctl de linux/i2c-dev.h: elegir el esclavo


# ===========================================================================
# Bus I2C del kernel
# ===========================================================================
class BusI2C:
    """Acceso a /dev/i2c-N con la biblioteca estándar."""

    def __init__(self, numero=I2C_BUS):
        self.nombre = "/dev/i2c-%d" % numero
        if fcntl is None:
            raise RuntimeError("No hay bus I2C en este sistema (sólo en la Raspberry).")
        try:
            self._fd = os.open(self.nombre, os.O_RDWR)
        except FileNotFoundError:
            raise RuntimeError(
                "No existe %s: el I2C está deshabilitado.\n"
                "  sudo raspi-config nonint do_i2c 0   y reiniciar" % self.nombre)
        except PermissionError:
            raise RuntimeError(
                "Sin permiso sobre %s.\n"
                "  sudo usermod -aG i2c $USER   y volver a iniciar sesión"
                % self.nombre)
        self._actual = None

    def _elegir(self, direccion):
        if direccion != self._actual:
            fcntl.ioctl(self._fd, I2C_SLAVE, direccion)
            self._actual = direccion

    def escribir(self, direccion, registro, datos=()):
        self._elegir(direccion)
        os.write(self._fd, bytes([registro]) + bytes(datos))

    def leer(self, direccion, registro, n=1):
        self._elegir(direccion)
        os.write(self._fd, bytes([registro]))
        return os.read(self._fd, n)

    def responde(self, direccion):
        """True si hay un dispositivo que contesta en esa dirección."""
        try:
            self.leer(direccion, MODE1, 1)
            return True
        except OSError:
            return False

    def cerrar(self):
        try:
            os.close(self._fd)
        except OSError:
            pass


# ===========================================================================
# Una placa PCA9685
# ===========================================================================
class PCA9685:
    """Una placa: 16 canales con memoria sombra de lo escrito."""

    def __init__(self, bus, direccion, frecuencia=50):
        self.bus = bus
        self.dir = direccion
        self.prescale = int(round(OSCILADOR_HZ / (4096.0 * frecuencia))) - 1
        self.frecuencia = OSCILADOR_HZ / (4096.0 * (self.prescale + 1))
        self.reg = [SALIDA_BAJA] * 16      # lo que tiene que haber en el chip
        self.sucio = [True] * 16           # lo que falta mandar
        self.reinicios = 0

    def configurar(self):
        """Frecuencia y modo de salida. El prescaler sólo se escribe dormido."""
        self.bus.escribir(self.dir, MODE1, [M1_AI | M1_SLEEP])
        self.bus.escribir(self.dir, PRESCALE, [self.prescale])
        self.bus.escribir(self.dir, MODE2, [M2_OUTDRV])
        self.bus.escribir(self.dir, MODE1, [M1_AI])
        time.sleep(0.001)                  # el oscilador tarda 500 us
        self.bus.escribir(self.dir, MODE1, [M1_AI | M1_RESTART])
        self.sucio = [True] * 16

    def se_reinicio(self):
        """Lee MODE1: si está dormido o sin autoincremento, se reinició."""
        m1 = self.bus.leer(self.dir, MODE1, 1)[0]
        return (m1 & M1_SLEEP) or not (m1 & M1_AI)

    def poner(self, canal, cuatro_bytes):
        if self.reg[canal] != cuatro_bytes:
            self.reg[canal] = cuatro_bytes
            self.sucio[canal] = True

    def volcar(self):
        """Manda de una vez el tramo que va del primer al último canal sucio."""
        if True not in self.sucio:
            return 0
        a = self.sucio.index(True)
        b = 15 - self.sucio[::-1].index(True)
        datos = []
        for c in range(a, b + 1):
            datos.extend(self.reg[c])
        self.bus.escribir(self.dir, LED0_ON_L + 4 * a, datos)
        for c in range(a, b + 1):
            self.sucio[c] = False
        return b - a + 1


def bytes_pulso(cuentas):
    """Cuatro bytes de canal para un pulso que arranca en 0 y dura 'cuentas'."""
    c = int(limitar(round(cuentas), 0, 4095))
    return (0x00, 0x00, c & 0xFF, c >> 8)


# ===========================================================================
# Servos y luces del tablero
# ===========================================================================
class ActuadoresPCA9685(ActuadoresBase):
    """
    destino = (nombre_de_placa, canal), por ejemplo ("PCA0", 7).

    Los instrumentos de motor paso a paso no pasan por el PCA9685: si se le
    entrega un gestor de motores (paso_a_paso.py), se le derivan a él.
    """

    CADA_VIGILANCIA_S = 2.0
    # Con un cable flojo el bus puede fallar en cada ciclo (20 por segundo): el
    # registro anota uno cada tanto y el total queda en salud().
    CADA_AVISO_BUS_S = 10.0

    def __init__(self, placas=PLACAS, bus=None, calibracion=None, motores=None):
        self.bus = bus if bus is not None else BusI2C()
        self.motores = motores
        self.placas = {}
        self.faltantes = []
        for nombre, direccion in sorted(placas.items()):
            if self.bus.responde(direccion):
                self.placas[nombre] = PCA9685(self.bus, direccion,
                                              SERVO_CFG["frecuencia_hz"])
            else:
                self.faltantes.append("%s (0x%02X)" % (nombre, direccion))
                log.warning("la placa %s (0x%02X) no responde: el tablero sigue sin ella",
                            nombre, direccion)

        self.cal = cargar_calibracion(calibracion)
        self.errores = 0
        self.ultimo_error = ""
        self._t_vigilancia = time.monotonic()
        self._t_aviso_bus = None

        # Estado inicial seguro: servos sin pulso y luces apagadas.
        self.luces = set()
        self.invertidos = set()
        for it in TABLERO:
            if not it.get("canal"):
                continue
            if it["actuador"] == LED:
                self.luces.add(tuple(it["canal"]))
            elif invertido(it["id"]):
                self.invertidos.add(tuple(it["canal"]))
        for nombre, placa in self.placas.items():
            placa.configurar()
            for c in range(16):
                if (nombre, c) in self.luces:
                    placa.poner(c, self._bytes_luz(False))
            placa.volcar()

    # -- conversión ---------------------------------------------------------
    def limites_us(self, destino):
        """Pulsos para 0 y para 180 grados del programa en ese canal.

        La calibración guarda lo medido con el transportador: el pulso que
        deja el brazo en la marca de 0° (izquierda) y en la de 180° (derecha),
        mirando el servo desde el lado del eje. Si entre el servo y la aguja
        hay un par de engranajes, el sentido se invierte (ver
        h08.config.invertido) y los dos extremos se intercambian.
        """
        c = self.cal.get("%s:%d" % tuple(destino))
        if c is None:
            a, b = SERVO_CFG["pulso_min_us"], SERVO_CFG["pulso_max_us"]
        else:
            a, b = c[0], c[1]
        if tuple(destino) in self.invertidos:
            a, b = b, a
        return a, b

    def topes_us(self, destino):
        """Pulsos que el servo no puede pasar (sus topes medidos), o None."""
        c = self.cal.get("%s:%d" % tuple(destino))
        return (c[2], c[3]) if c else None

    def _cuentas(self, placa, us):
        return us * 4096.0 * placa.frecuencia / 1e6

    @staticmethod
    def _bytes_luz(encendida):
        if LUCES_ACTIVAS_EN_BAJO:
            return SALIDA_BAJA if encendida else SALIDA_ALTA
        return SALIDA_ALTA if encendida else SALIDA_BAJA

    # -- salidas ------------------------------------------------------------
    def escribir_servo(self, destino, angulo_deg):
        placa = self.placas.get(destino[0])
        if placa is None:
            return
        us_0, us_180 = self.limites_us(destino)
        a = limitar(angulo_deg, 0.0, SERVO_CFG["barrido_deg"])
        us = us_0 + (us_180 - us_0) * a / SERVO_CFG["barrido_deg"]
        topes = self.topes_us(destino)
        if topes:
            us = limitar(us, min(topes), max(topes))
        placa.poner(destino[1], bytes_pulso(self._cuentas(placa, us)))

    def escribir_pulso(self, destino, us):
        """Pulso en microsegundos, sin calibración. Lo usa calibrar_servo.py."""
        placa = self.placas.get(destino[0])
        if placa is not None:
            placa.poner(destino[1], bytes_pulso(self._cuentas(placa, us)))

    def soltar(self, destino):
        """Quita el pulso: el servo deja de hacer fuerza."""
        placa = self.placas.get(destino[0])
        if placa is not None:
            placa.poner(destino[1], SALIDA_BAJA)

    def escribir_led(self, destino, encendido):
        placa = self.placas.get(destino[0])
        if placa is not None:
            placa.poner(destino[1], self._bytes_luz(encendido))

    def escribir_motor(self, destino, angulo_deg):
        if self.motores is not None:
            self.motores.escribir_motor(destino, angulo_deg)

    # -- ciclo --------------------------------------------------------------
    def refrescar(self):
        ahora = time.monotonic()
        vigilar = ahora - self._t_vigilancia >= self.CADA_VIGILANCIA_S
        if vigilar:
            self._t_vigilancia = ahora
        n = 0
        for nombre, placa in self.placas.items():
            try:
                if vigilar and placa.se_reinicio():
                    placa.reinicios += 1
                    log.warning("la placa %s se reinició (¿caída de tensión?): se la vuelve "
                                "a configurar y recupera sus canales", nombre)
                    placa.configurar()
                n += placa.volcar()
            except OSError as e:
                # Lo que no se pudo mandar sigue marcado como sucio y se
                # reintenta en el próximo ciclo.
                self.errores += 1
                self.ultimo_error = "%s: %s" % (nombre, e)
                if self._t_aviso_bus is None or ahora - self._t_aviso_bus >= self.CADA_AVISO_BUS_S:
                    self._t_aviso_bus = ahora
                    log.warning("error en el bus I2C con la placa %s: %s (van %d)",
                                nombre, e, self.errores)
        return n

    def cerrar(self):
        """Luces apagadas y servos sin pulso; los motores se estacionan."""
        if self.motores is not None:
            self.motores.cerrar()
        for nombre, placa in self.placas.items():
            for c in range(16):
                if (nombre, c) in self.luces:
                    placa.poner(c, self._bytes_luz(False))
                else:
                    placa.poner(c, SALIDA_BAJA)
            try:
                placa.volcar()
            except OSError:
                pass
        self.bus.cerrar()

    def descripcion(self):
        d = "PCA9685: %s" % (", ".join("%s 0x%02X" % (n, p.dir)
                                       for n, p in sorted(self.placas.items()))
                             or "ninguna")
        if self.faltantes:
            d += "  FALTAN: " + ", ".join(self.faltantes)
        if self.cal:
            d += "  (%d servos calibrados)" % len(self.cal)
        if self.motores is not None:
            d += "  + " + self.motores.descripcion()
        return d

    def salud(self):
        """Resumen para la página web y el diagnóstico."""
        return {"errores_i2c": self.errores,
                "ultimo_error": self.ultimo_error,
                "reinicios_pca": sum(p.reinicios for p in self.placas.values()),
                "faltan": self.faltantes}


# ===========================================================================
# Calibración por servo
# ===========================================================================
def cargar_calibracion(archivo):
    """Lee calibracion_servos.json (lo escribe calibrar_servo.py).

    Devuelve {"PCA0:3": (us_0, us_180, tope_a, tope_b), ...}:
      us_0, us_180    pulso con el brazo en 0° y en 180° del transportador;
                      pueden estar extrapolados si el servo no llega;
      tope_a, tope_b  los pulsos que no se pasan (los extremos alcanzables).
    También acepta el formato viejo {"min_us": .., "max_us": ..}.
    """
    if not archivo or not os.path.exists(archivo):
        return {}
    try:
        with open(archivo, encoding="utf-8") as f:
            crudo = json.load(f)
    except (OSError, ValueError):
        return {}
    cal = {}
    for clave, v in crudo.items():
        try:
            if "us_0" in v:
                a, b = float(v["us_0"]), float(v["us_180"])
                ta = float(v.get("tope_a", a))
                tb = float(v.get("tope_b", b))
            else:
                a, b = float(v["min_us"]), float(v["max_us"])
                ta, tb = a, b
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
        if all(200 <= x <= 2900 for x in (a, b)) and abs(b - a) >= 500 \
                and all(300 <= x <= 2700 for x in (ta, tb)):
            cal[clave] = (a, b, ta, tb)
    return cal
