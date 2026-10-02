# -*- coding: utf-8 -*-
"""Quién puede mirar, quién puede mandar y quién manda ahora.

Mirar no tiene clave; mandar sí (la del QR del profesor), y de los admins manda uno
solo a la vez, porque dos personas metiendo fallas distintas arruinan la
demostración. No es seguridad informática: el tablero habla HTTP y protege contra el
alumno curioso, no contra alguien decidido. Está explicado sin adornos en
docs/acceso.md, junto con el manejo de la clave y de la cookie.
"""
import json
import os
import secrets
import threading
import time

# Cuánto vive una sesión de admin sin uso. Ocho horas cubren una jornada de
# taller; pasado eso hay que volver a leer el QR.
VIDA_SESION = 8 * 3600

# Si el que tiene el mando desaparece (cerró el navegador, se quedó sin
# batería) el mando no puede quedar trabado. Pasados estos segundos sin
# señales, cualquier otro admin lo puede tomar.
MANDO_ABANDONADO = 45

# Cuando alguien pide el mando, el que lo tiene dispone de este tiempo para
# contestar. Si no contesta, el que lo pidió se lo puede quedar.
ESPERA_CESION = 30

LARGO_CLAVE = 22


def _ahora():
    return time.monotonic()


class Acceso:
    """Las tres cosas de arriba, protegidas con un candado (el servidor
    atiende cada pedido en un hilo propio).

    Todo el estado vive en memoria salvo la clave, que vive en un archivo.
    Reiniciar el tablero cierra todas las sesiones y libera el mando.
    """

    def __init__(self, archivo_clave, vida_sesion=VIDA_SESION):
        self.archivo = archivo_clave
        self.vida = vida_sesion
        self._candado = threading.Lock()
        self.sesiones = {}          # sid -> {"desde":, "visto":, "nombre":}
        self.titular = None         # sid del que tiene el mando
        self.visto_titular = 0.0
        self.pedido = None          # {"sid":, "nombre":, "cuando":}
        self.clave = self._leer_o_crear_clave()

    # La clave
    def _leer_o_crear_clave(self):
        try:
            with open(self.archivo, encoding="utf-8") as f:
                c = (json.load(f) or {}).get("clave") or ""
            if len(c) >= 12:
                return c
        except (OSError, ValueError):
            pass
        return self._escribir_clave(secrets.token_urlsafe(16)[:LARGO_CLAVE])

    def _escribir_clave(self, clave):
        d = os.path.dirname(os.path.abspath(self.archivo))
        if d and not os.path.isdir(d):
            os.makedirs(d, exist_ok=True)
        with open(self.archivo, "w", encoding="utf-8") as f:
            json.dump({"clave": clave}, f)
        try:
            # Sólo el dueño puede leerla. No frena a nadie con sudo, pero
            # evita que la clave quede legible para cualquier usuario.
            os.chmod(self.archivo, 0o600)
        except OSError:
            pass
        return clave

    def renovar_clave(self):
        """Clave nueva. Las sesiones abiertas se cierran y el mando queda libre."""
        with self._candado:
            self.clave = self._escribir_clave(
                secrets.token_urlsafe(16)[:LARGO_CLAVE])
            self.sesiones.clear()
            self.titular = None
            self.pedido = None
            return self.clave

    # Sesiones
    def _limpiar(self):
        """Borra las sesiones vencidas. Se llama con el candado tomado."""
        t = _ahora()
        muertas = [s for s, d in self.sesiones.items()
                   if t - d["visto"] > self.vida]
        for s in muertas:
            del self.sesiones[s]
        if self.titular and self.titular not in self.sesiones:
            self.titular = None
        if self.pedido and self.pedido["sid"] not in self.sesiones:
            self.pedido = None

    def entrar(self, clave, nombre=""):
        """Canjea la clave por una sesión. Devuelve el identificador, o None.

        La comparación es de tiempo constante (compare_digest), para que el
        tiempo de respuesta no dé pistas sobre la clave. Va en bytes porque con
        texto no acepta una tilde: /mando?k=ñ cortaba el pedido con un error.
        """
        if not clave:
            return None
        if not secrets.compare_digest(str(clave).encode("utf-8"), self.clave.encode("utf-8")):
            return None
        sid = secrets.token_urlsafe(18)
        with self._candado:
            self._limpiar()
            self.sesiones[sid] = {"desde": _ahora(), "visto": _ahora(),
                                  "nombre": (nombre or "")[:24]}
        return sid

    def es_admin(self, sid):
        if not sid:
            return False
        with self._candado:
            self._limpiar()
            d = self.sesiones.get(sid)
            if d is None:
                return False
            d["visto"] = _ahora()
            return True

    def salir(self, sid):
        with self._candado:
            if self.titular == sid:
                self.titular = None
            if self.pedido and self.pedido["sid"] == sid:
                self.pedido = None
            self.sesiones.pop(sid, None)

    def nombrar(self, sid, nombre):
        with self._candado:
            if sid in self.sesiones:
                self.sesiones[sid]["nombre"] = (nombre or "")[:24]

    # El mando
    def _mando_libre(self):
        """Con el candado tomado: si no hay titular o el titular se fue."""
        if self.titular is None:
            return True
        if self.titular not in self.sesiones:
            return True
        return (_ahora() - self.visto_titular) > MANDO_ABANDONADO

    def tomar_mando(self, sid):
        """Toma el mando si está libre, o si el que lo tiene no contestó."""
        with self._candado:
            self._limpiar()
            if sid not in self.sesiones:
                return False, "sesión vencida"
            if self.titular == sid:
                self.visto_titular = _ahora()
                return True, "ya lo tenías"
            if self._mando_libre():
                self.titular = sid
                self.visto_titular = _ahora()
                self.pedido = None
                return True, "tomado"
            # no está libre: sólo se lo queda el que lo pidió y esperó
            p = self.pedido
            if (p and p["sid"] == sid
                    and _ahora() - p["cuando"] >= ESPERA_CESION):
                self.titular = sid
                self.visto_titular = _ahora()
                self.pedido = None
                return True, "tomado por falta de respuesta"
            return False, "lo tiene otro dispositivo"

    def pedir_mando(self, sid):
        with self._candado:
            self._limpiar()
            if sid not in self.sesiones:
                return False
            if self.titular == sid or self._mando_libre():
                return False
            self.pedido = {"sid": sid, "cuando": _ahora(),
                           "nombre": self.sesiones[sid].get("nombre", "")}
            return True

    def ceder_mando(self, sid):
        """El titular suelta el mando. Si alguien lo pidió, pasa a ese."""
        with self._candado:
            if self.titular != sid:
                return False
            p = self.pedido
            if p and p["sid"] in self.sesiones:
                self.titular = p["sid"]
                self.visto_titular = _ahora()
            else:
                self.titular = None
            self.pedido = None
            return True

    def rechazar_pedido(self, sid):
        with self._candado:
            if self.titular != sid:
                return False
            self.pedido = None
            self.visto_titular = _ahora()
            return True

    def puede_mandar(self, sid):
        """La pregunta que hace el servidor antes de dejar pasar una orden."""
        with self._candado:
            self._limpiar()
            if sid not in self.sesiones:
                return False
            self.sesiones[sid]["visto"] = _ahora()
            if self.titular is None and not self.sesiones:
                return False
            if self.titular == sid:
                self.visto_titular = _ahora()
                return True
            # nadie manda todavía: el primero que ordena algo toma el mando
            if self._mando_libre():
                self.titular = sid
                self.visto_titular = _ahora()
                self.pedido = None
                return True
            return False

    def estado(self, sid):
        """Todo lo que necesita la página de mando, en una sola respuesta."""
        with self._candado:
            self._limpiar()
            soy_admin = sid in self.sesiones
            if soy_admin:
                self.sesiones[sid]["visto"] = _ahora()
                if self.titular == sid:
                    self.visto_titular = _ahora()
            libre = self._mando_libre()
            p = self.pedido
            resta = 0
            if p:
                resta = max(0, int(ESPERA_CESION - (_ahora() - p["cuando"])))
            return {
                "admin": soy_admin,
                "mando": bool(soy_admin and self.titular == sid),
                "mando_libre": libre,
                "hay_titular": bool(self.titular and not libre),
                "titular_nombre": (self.sesiones.get(self.titular, {})
                                   .get("nombre", "") if self.titular else ""),
                "pedido_mio": bool(p and p["sid"] == sid),
                "pedido_ajeno": bool(p and p["sid"] != sid
                                     and self.titular == sid),
                "pedido_nombre": (p or {}).get("nombre", ""),
                "pedido_resta": resta,
                "admins": len(self.sesiones),
            }
