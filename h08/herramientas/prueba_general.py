# -*- coding: utf-8 -*-
"""La prueba del tablero entero, de punta a punta.

    python3 -m h08 prueba-general              la prueba completa (unos 15 min)
    python3 -m h08 prueba-general --sin-pantalla  sin preguntar por la pantalla
    python3 -m h08 prueba-general --simulado --auto
                                               cómo es, sin hardware

Es la que se hace antes de una muestra, o después de armar o tocar algo. Pregunta sí
o no en cada paso y guarda un informe fechado en datos/informes/.

  0. diagnóstico   lo de python3 -m h08 diagnostico, sin preguntar nada
  A. hardware solo con el servicio detenido, manejando las placas directo:
                   lámparas, las 20 agujas al medio de a tres, las 20 barriendo
                   juntas mientras se mide la alimentación (es la prueba de la
                   fuente de servos), brújula N-E-S-O-N y todo suelto
  B. tablero entero con el servicio andando, operándolo como el profesor por la
                   misma API que la página de mando: arranque, pantalla, un
                   celular por wifi, prueba de luces, dos fallas (aceite y
                   generador) y la vuelta a vuelo normal

Necesita sudo para detener y arrancar el servicio (lo pide una vez).
"""

import argparse
import http.client
import json
import os
import re
import subprocess
import sys
import threading
import time

from h08 import rutas
from h08.config import TABLERO, SERVO, LED, MOTOR, ARRANQUE
from h08.herramientas import banco
from h08.herramientas import interactivo as I
from h08.util import interpolar_tabla

S0 = "0. DIAGNÓSTICO"
SA = "A. HARDWARE SOLO (servicio detenido)"
SB = "B. TABLERO ENTERO (servicio andando)"


# Servicio y API
def systemctl(orden, simulado):
    if simulado:
        return True
    r = subprocess.run(["sudo", "systemctl", orden, banco.SERVICIO])
    return r.returncode == 0


class Mando:
    """Habla con el servidor como la página de mando del profesor."""

    def __init__(self, puerto, clave=None):
        self.puerto = puerto
        self.cookie = ""
        self.clave = clave

    def _pedir(self, metodo, ruta, t=4):
        c = http.client.HTTPConnection("localhost", self.puerto, timeout=t)
        h = {"Cookie": self.cookie} if self.cookie else {}
        c.request(metodo, ruta, body=b"" if metodo == "POST" else None, headers=h)
        r = c.getresponse()
        cuerpo = r.read()
        galleta = r.getheader("Set-Cookie") or ""
        c.close()
        return r.status, cuerpo, galleta

    def estado(self):
        try:
            s, b, _ = self._pedir("GET", "/api/estado")
            return json.loads(b.decode("utf-8")) if s == 200 else None
        except (OSError, ValueError, http.client.HTTPException):
            return None

    def esperar(self, seg=40):
        fin = time.monotonic() + seg
        while time.monotonic() < fin:
            if self.estado() is not None:
                return True
            time.sleep(1)
        return False

    def entrar(self):
        """Canjea la clave del QR por la cookie y toma el mando."""
        if self.clave:
            s, _, galleta = self._pedir("GET", "/mando?k=" + self.clave)
            m = re.match(r"\s*([^=;]+=[^;]*)", galleta)
            if s != 302 or not m:
                return False
            self.cookie = m.group(1)
        s, b, _ = self._pedir("POST", "/api/mando/tomar")
        try:
            return s == 200 and json.loads(b.decode("utf-8")).get("ok", False)
        except ValueError:
            return False

    def post(self, ruta):
        try:
            s, _, _ = self._pedir("POST", ruta)
            return s == 200
        except (OSError, http.client.HTTPException):
            return False

    def valor(self, ident, campo="v"):
        e = self.estado() or {}
        return ((e.get("instrumentos") or {}).get(ident) or {}).get(campo)


def servidor_simulado():
    """Para --simulado: el mismo servidor que la Pi, en esta computadora,
    en un puerto libre, sin hardware y sin clave."""
    from h08.web import servidor as servidor_web
    from h08.hardware.simulado import ActuadoresSimulados
    from h08.simulacion.hilo import HiloSimulacion
    nucleo = HiloSimulacion(ActuadoresSimulados(), semilla=1)
    nucleo.start()
    puerto = servidor_web.puerto_libre(8090)
    srv = servidor_web.crear(nucleo, puerto, rutas.ESTATICOS, acceso=None)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return puerto, srv, nucleo


# 0. Diagnóstico
def parte0(inf, simulado):
    print("\n" + "=" * 70 + "\n " + S0 + "\n" + "=" * 70)
    if simulado:
        inf.anotar(S0, "diagnóstico", "SALTEADO", "prueba simulada")
        print("  (salteado: prueba simulada)")
        return
    from h08.herramientas import diagnostico
    R = diagnostico.revisar(eco=False)
    malos = R.problemas()
    for ok, t, arr in R.filas:
        if ok is True:
            inf.bien(S0, t)
        elif ok is False:
            inf.mal(S0, t, arr or "")
    print("  %d controles automáticos, %d para revisar" %
          (sum(1 for f in R.filas if f[0] in (True, False)), len(malos)))
    for _, t, arr in malos:
        print("   [!!] %s\n        -> %s" % (t, arr))


# A. Hardware solo
def leer_alimentacion():
    """(throttled, 5 V de entrada) de la Pi, o (None, None)."""
    try:
        t = subprocess.run(["vcgencmd", "get_throttled"], capture_output=True,
                           text=True, timeout=3).stdout
        a = subprocess.run(["vcgencmd", "pmic_read_adc", "EXT5V_V"], capture_output=True,
                           text=True, timeout=3).stdout
        th = int(t.split("=")[1], 16) if "=" in t else None
        m = re.search(r"=([0-9.]+)V", a)
        return th, (float(m.group(1)) if m else None)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None, None


def reiniciadas(act):
    """Qué PCA9685 se reinició (por baja tensión) desde que se configuró."""
    malas = []
    for n, p in getattr(act, "placas", {}).items():
        if p is None:
            continue
        try:
            if p.se_reinicio():
                malas.append(n)
        except OSError:
            malas.append(n + " (no contesta)")
    return malas


def parteA(inf, P, simulado):
    print("\n" + "=" * 70 + "\n " + SA + "\n" + "=" * 70)
    if not simulado:
        print("  Se detiene el servicio para manejar las placas directo.")
        systemctl("stop", simulado)
    act = I.abrir_placas(simulado)
    gestor = I.abrir_motor(simulado)
    servos = [it for it in TABLERO if it["actuador"] == SERVO and it.get("canal")
              and it["canal"][0] in act.placas]
    luces = [it for it in TABLERO if it["actuador"] == LED and it.get("canal")
             and it["canal"][0] in act.placas]
    try:
        print("\n  A1. Prueba de lámparas")
        for it in luces:
            act.escribir_led(it["canal"], True)
        act.refrescar()
        I.dormir(2.5)
        r = P.si_no("¿Están encendidas las %d luces?" % len(luces))
        if r == "q":
            return False
        (inf.bien if r == "s" else inf.mal)(SA, "A1 prueba de lámparas (%d luces)" % len(luces),
                                            "" if r == "s" else "probar de a una: python3 -m h08 luces-motor --luces")
        for it in luces:
            act.escribir_led(it["canal"], False)
        act.refrescar()

        print("\n  A2. Las %d agujas al MEDIO de su escala, de a %d"
              % (len(servos), ARRANQUE["canales_por_tanda"]))
        medio = {}
        for k, it in enumerate(servos):
            lo, hi = it["escala"]
            medio[it["id"]] = I.angulo_servo(it, (lo + hi) / 2.0)
            act.escribir_servo(it["canal"], medio[it["id"]])
            if (k + 1) % ARRANQUE["canales_por_tanda"] == 0:
                act.refrescar()
                I.dormir(ARRANQUE["segundos_entre_tandas"])
        act.refrescar()
        I.dormir(1.5)
        r = P.si_no("¿Todas quedaron en el medio de su escala, quietas y sin zumbar?")
        if r == "q":
            return False
        (inf.bien if r == "s" else inf.mal)(
            SA, "A2 todas las agujas al medio",
            "" if r == "s" else (P.nota("¿Cuál no?") +
                                 "  -> python3 -m h08 instrumento ESA"))

        print("\n  A3. Las %d agujas barriendo JUNTAS (prueba de la fuente de servos)"
              % len(servos))
        th0, v0 = leer_alimentacion()
        vmin = v0
        extremos = {it["id"]: (I.angulo_servo(it, it["escala"][0]),
                               I.angulo_servo(it, it["escala"][1])) for it in servos}
        pasos = 60
        for tramo in ((0.5, 0.0), (0.0, 1.0), (1.0, 0.5)):
            for i in range(pasos + 1):
                f = tramo[0] + (tramo[1] - tramo[0]) * i / pasos
                for it in servos:
                    a, b = extremos[it["id"]]
                    act.escribir_servo(it["canal"], a + (b - a) * f)
                act.refrescar()
                I.dormir(3.0 / pasos)
                if i % 10 == 0:
                    _, v = leer_alimentacion()
                    if v is not None:
                        vmin = v if vmin is None else min(vmin, v)
        th1, _ = leer_alimentacion()
        caidas = reiniciadas(act)
        r = P.si_no("¿Se movieron todas juntas, de punta a punta, sin trabarse?")
        if r == "q":
            return False
        (inf.bien if r == "s" else inf.mal)(SA, "A3 barrido de todas juntas", P.nota() if r == "n" else "")
        if caidas:
            inf.mal(SA, "A3 los PCA9685 aguantan el barrido",
                    "se reinició %s: la fuente de servos no da abasto o el 3,3 V del "
                    "módulo se cae. Bajar ARRANQUE['canales_por_tanda'] no alcanza: "
                    "revisar LM2596 (3 A máx.) y los cables de V+" % ", ".join(caidas))
        elif not simulado:
            inf.bien(SA, "A3 los PCA9685 aguantan el barrido (ninguno se reinició)")
        if th0 is not None and th1 is not None:
            nueva = (th1 & 0x1) or ((th1 & 0x10000) and not (th0 & 0x10000))
            (inf.mal if nueva else inf.bien)(
                SA, "A3 la Raspberry no tuvo baja tensión durante el barrido",
                "masa de la fuente de servos unida mal, o los servos colgados de la Pi"
                if nueva else ("mínimo %.2f V" % vmin if vmin else ""))
        for it in servos:
            act.escribir_servo(it["canal"], medio[it["id"]])
        act.refrescar()

        print("\n  A4. Brújula: N, E, S, O y N")
        if gestor is None:
            inf.anotar(SA, "A4 brújula", "SALTEADO", "no se pudo abrir el GPIO")
        else:
            mot = next(it for it in TABLERO if it["actuador"] == MOTOR and it.get("canal"))
            for g in (0, 90, 180, 270, 0):
                gestor.escribir_motor(tuple(mot["canal"]), g)
                gestor.esperar_quietos(12)
                I.dormir(0.7)
            r = P.si_no("¿La aguja fue a N, E, S, O y volvió a N?")
            if r == "q":
                return False
            (inf.bien if r == "s" else inf.mal)(
                SA, "A4 brújula N-E-S-O-N",
                "" if r == "s" else "python3 -m h08 luces-motor --motor")

        print("\n  A5. Todo suelto y apagado")
        for it in servos:
            act.soltar(it["canal"])
        for it in luces:
            act.escribir_led(it["canal"], False)
        act.refrescar()
        I.dormir(1.0)
        r = P.si_no("¿Luces apagadas y las agujas se pueden mover con la mano (sin fuerza)?")
        if r == "q":
            return False
        (inf.bien if r == "s" else inf.mal)(SA, "A5 todo suelto y apagado")
    finally:
        if gestor is not None:
            gestor.cerrar()
        if getattr(act, "errores", 0):
            inf.mal(SA, "bus I2C sin errores", "%d errores. Último: %s"
                    % (act.errores, act.ultimo_error))
        act.cerrar()
    return True


# B. Tablero entero
def parteB(inf, P, simulado, sin_pantalla):
    print("\n" + "=" * 70 + "\n " + SB + "\n" + "=" * 70)
    srv = nucleo = None
    if simulado:
        puerto, srv, nucleo = servidor_simulado()
        mando = Mando(puerto)
    else:
        puerto = 8000
        from h08.web.acceso import Acceso
        clave = Acceso(rutas.CLAVE).clave
        mando = Mando(puerto, clave)
        print("  Arrancando el servicio (las agujas se acomodan de a tres)...")
        systemctl("start", simulado)
    try:
        ok = mando.esperar(45)
        (inf.bien if ok else inf.mal)(SB, "B1 el servicio arranca y la página contesta",
                                      "" if ok else "journalctl -u %s -n 50" % banco.SERVICIO)
        if not ok:
            return True
        hw = (mando.estado() or {}).get("hardware") or {}
        if not simulado:
            (inf.bien if "errores_i2c" in hw and not hw.get("faltan") else inf.mal)(
                SB, "B1 el servicio maneja las placas",
                "" if "errores_i2c" in hw and not hw.get("faltan")
                else "faltan placas o no abrió el I2C: python3 -m h08 diagnostico")
        I.dormir(4.0)

        if sin_pantalla:
            inf.anotar(SB, "B2 pantalla de la Raspberry", "SALTEADO", "--sin-pantalla")
        else:
            r = P.si_no("B2. ¿La pantalla de la Raspberry muestra el tablero (con los QR abajo)?")
            if r == "q":
                return False
            (inf.bien if r == "s" else inf.mal)(
                SB, "B2 pantalla de la Raspberry",
                "" if r == "s" else "bash deploy/kiosco.sh  (y ver python3 -m h08 diagnostico, punto 6)")

        from h08.web import qr
        from h08.web import servidor as servidor_web
        url = servidor_web.direccion(puerto)
        ap = servidor_web.datos_punto_de_acceso()
        print("\n  B3. Con un celular: conectarse a la red «%s» (clave %s) y entrar a"
              % (ap["red"], ap["clave"]))
        print("      %s   (o leer este código)\n" % url)
        if not P.auto:
            print(qr.texto_consola(url, borde=1))
        r = P.si_no("¿El celular muestra el tablero y las agujas se mueven?")
        if r == "q":
            return False
        (inf.bien if r == "s" else inf.mal)(
            SB, "B3 un celular entra por wifi",
            "" if r == "s" else "sudo bash deploy/punto_de_acceso.sh estado / encender")

        if not mando.entrar():
            inf.mal(SB, "B4-B7 tomar el mando con la clave del profesor",
                    "¿otro dispositivo tiene el mando? Soltarlo desde /mando")
            return True
        mando.post("/api/accion/velocidad?valor=4")
        print("\n  B4. Prueba de luces desde el mando")
        mando.post("/api/accion/prueba_luces?valor=true")
        time.sleep(2.0)
        todas = all((mando.valor(it["id"], "ang") or 0) >= 0.5
                    for it in TABLERO if it["actuador"] == LED)
        (inf.bien if todas else inf.mal)(SB, "B4 el modelo enciende las seis luces")
        r = P.si_no("¿Se encendieron las seis luces del tablero Y las de la página?")
        mando.post("/api/accion/prueba_luces?valor=false")
        if r == "q":
            return False
        (inf.bien if r == "s" else inf.mal)(SB, "B4 prueba de luces desde el mando")

        print("\n  B5. Falla: pérdida de presión de aceite (crucero a 1500 ft, rumbo 090)")
        # esperas de verdad (no se acortan en --simulado): las pone el modelo
        mando.post("/api/modo/3?id=OIL_PRESS_LOSS")
        time.sleep(3.0)
        p0 = mando.valor("OIL_PRESS")
        time.sleep(15.0)
        p1 = mando.valor("OIL_PRESS")
        cae = p0 is not None and p1 is not None and p1 < p0 - 20
        (inf.bien if cae else inf.mal)(
            SB, "B5 el modelo baja la presión de aceite",
            "%s -> %s psi" % ("?" if p0 is None else "%.0f" % p0, "?" if p1 is None else "%.0f" % p1))
        r = P.si_no("¿La aguja de PRES. ACEITE bajó hasta casi cero, y la brújula está en E?")
        if r == "q":
            return False
        (inf.bien if r == "s" else inf.mal)(SB, "B5 el tablero muestra la falla de aceite")

        print("\n  B6. Falla: generador")
        mando.post("/api/modo/3?id=GEN_FAIL")
        time.sleep(6.0)
        g = mando.valor("LT_GEN", "ang")
        (inf.bien if (g or 0) >= 0.5 else inf.mal)(SB, "B6 el modelo enciende la luz GENERATOR")
        r = P.si_no("¿Se encendió la luz GENERATOR y el amperímetro marca descarga (negativo)?")
        if r == "q":
            return False
        (inf.bien if r == "s" else inf.mal)(SB, "B6 el tablero muestra la falla del generador")

        mando.post("/api/accion/velocidad?valor=1")
        mando.post("/api/modo/1")
        mando.post("/api/mando/ceder")
        inf.bien(SB, "B7 vuelve a vuelo normal y suelta el mando")
    finally:
        if srv is not None:
            srv.shutdown()
            srv.server_close()
            nucleo.detener()
            nucleo.join(5)
    return True


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python3 -m h08 prueba-general",
                                 description="Prueba general del tablero H-08")
    ap.add_argument("--simulado", action="store_true")
    ap.add_argument("--auto", action="store_true")
    ap.add_argument("--sin-pantalla", action="store_true", dest="sin_pantalla")
    ap.add_argument("--solo", choices=("A", "B"), help="hacer sólo una parte")
    a = ap.parse_args(argv)
    I.salir_si_no_hay_consola(a.auto)
    if a.simulado:
        I.acelerar()
    elif getattr(os, "geteuid", lambda: 0)() != 0:
        print("  Se va a pedir la clave de sudo para detener y arrancar el servicio.")
        subprocess.run(["sudo", "-v"])

    P = I.Preguntas(a.auto)
    inf = I.Informe("PRUEBA GENERAL - Tablero H-08" + ("  (SIMULADA)" if a.simulado else ""))
    try:
        parte0(inf, a.simulado)
        seguir = True
        if a.solo in (None, "A"):
            seguir = parteA(inf, P, a.simulado)
        if seguir and a.solo in (None, "B"):
            parteB(inf, P, a.simulado, a.sin_pantalla)
        elif not a.simulado:
            systemctl("start", a.simulado)
    except KeyboardInterrupt:
        print("\n  Cortada. Se deja el servicio andando.")
        systemctl("start", a.simulado)
    print("\n" + inf.texto())
    print("\n  Informe guardado en: %s\n" % inf.guardar("prueba_general"))
    return 1 if inf.malos() else 0


if __name__ == "__main__":
    sys.exit(main())
