# -*- coding: utf-8 -*-
"""
acceso.py - quién puede mirar, quién puede mandar y quién manda ahora
======================================================================

QUÉ RESUELVE
---------------------------------------------------------------------------
El tablero se muestra en el taller: hay una pantalla proyectada, un profesor
con el celular en la mano y veinte alumnos mirando desde el suyo. Todos
tienen que poder VER el tablero en vivo; ninguno tiene que poder meterle una
falla por tocar donde no debe.

TRES COSAS DISTINTAS
---------------------------------------------------------------------------
  1. ENTRAR           cualquiera entra y mira. No hay clave para mirar.

  2. SER ADMIN        hace falta la clave, que viaja adentro del QR del
                      profesor. Ser admin habilita a mandar.

  3. TENER EL MANDO   un solo dispositivo a la vez. Si el profesor y un
                      ayudante entran los dos con el QR de admin, los dos son
                      admin, pero manda uno solo; el otro puede pedirlo.

La tercera existe porque dos personas metiendo fallas distintas al mismo
tiempo arruinan la demostración.

ALCANCE DE ESTA PROTECCIÓN
---------------------------------------------------------------------------
Esto no es seguridad informática en sentido estricto. El tablero habla HTTP,
no HTTPS: la clave viaja en claro la primera vez y la cookie de sesión en
todos los pedidos. Alguien conectado a la misma red wifi, con herramientas y
decidido, podría hacerse pasar por el profesor.

Sirve contra lo que hay en un aula o en una muestra:
  * el alumno que abre la página y toca todo para ver qué pasa;
  * el que escribe a mano la dirección /api/modo/3 en el navegador;
  * el visitante que quiere "probar" el tablero.

Se documenta así a propósito: una protección que se cree más fuerte de lo
que es resulta peor que ninguna, porque se confía en ella.

LA CLAVE
---------------------------------------------------------------------------
Es un texto aleatorio de 22 caracteres, guardado en un archivo que sólo puede
leer el usuario que corre el tablero. Se genera sola la primera vez y no
cambia, salvo que se pida:

    python3 -m h08 --renovar-clave

Al renovarla, el QR anterior deja de servir en el acto.

Ninguna ruta web muestra la clave ni el QR de administrador: se obtienen en
la terminal de la Raspberry (--qr-admin). Una página que supiera mostrar la
llave de administrador sería una página a la que se le puede pedir la llave.
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


# ===========================================================================
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

    # -- la clave -----------------------------------------------------------
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

    # -- sesiones -----------------------------------------------------------
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
        tiempo de respuesta no dé pistas sobre la clave.
        """
        if not clave:
            return None
        if not secrets.compare_digest(str(clave), self.clave):
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

    # -- el mando -----------------------------------------------------------
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
