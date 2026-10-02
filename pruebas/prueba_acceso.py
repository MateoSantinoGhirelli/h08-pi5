#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prueba_acceso.py - que el visitante no pueda mandar, y que el mando se ceda
============================================================================

Prueba nucleo/acceso.py sin levantar ningun servidor. Son las reglas que
deciden quien puede meterle una falla al tablero delante de un curso, asi que
conviene que esten probadas de verdad y no "se ve que anda".

    python3 prueba_acceso.py
"""
import os
import sys
import tempfile
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
for _c in (os.path.join(AQUI, "..", "nucleo"), os.path.join(AQUI, "nucleo")):
    if os.path.isdir(_c):
        sys.path.insert(0, os.path.abspath(_c))
        break

import acceso                                                # noqa: E402
from acceso import Acceso                                    # noqa: E402

fallos = []


def igual(nombre, obtenido, esperado):
    ok = obtenido == esperado
    print("  %s %-52s %s" % ("ok  " if ok else "MAL ", nombre,
                             "" if ok else "-> %r (esperaba %r)"
                             % (obtenido, esperado)))
    if not ok:
        fallos.append(nombre)


def cierto(nombre, valor):
    igual(nombre, bool(valor), True)


def falso(nombre, valor):
    igual(nombre, bool(valor), False)


def nuevo():
    d = tempfile.mkdtemp()
    return Acceso(os.path.join(d, "secreto_admin.json"))


# ===========================================================================
def clave_y_sesiones():
    print("\n  LA CLAVE Y LAS SESIONES")
    a = nuevo()
    igual("la clave se genera sola", len(a.clave) >= 12, True)
    cierto("el archivo quedo escrito", os.path.exists(a.archivo))
    if os.name == "nt":
        # Windows no tiene permisos de dueño/grupo/otros: se comprueba en la Pi.
        print("  --   el archivo es solo del duenio: no aplica en Windows")
    else:
        modo = os.stat(a.archivo).st_mode & 0o777
        igual("el archivo es solo del duenio", oct(modo), oct(0o600))

    igual("sin clave no se entra", a.entrar(""), None)
    igual("con clave equivocada no se entra", a.entrar("cualquiera"), None)
    sid = a.entrar(a.clave)
    cierto("con la clave correcta se entra", sid)
    cierto("y queda como admin", a.es_admin(sid))
    falso("un sid inventado no es admin", a.es_admin("inventado"))
    falso("sin sid no es admin", a.es_admin(None))

    # la clave que se relee del archivo es la misma
    b = Acceso(a.archivo)
    igual("la clave sobrevive al reinicio", b.clave, a.clave)

    vieja = a.clave
    nueva = a.renovar_clave()
    cierto("renovar da una clave distinta", nueva != vieja)
    falso("la sesion vieja ya no vale", a.es_admin(sid))
    igual("la clave vieja ya no entra", a.entrar(vieja), None)
    cierto("la nueva si", a.entrar(nueva))


def el_visitante_no_manda():
    print("\n  EL VISITANTE")
    a = nuevo()
    falso("un visitante no es admin", a.es_admin(None))
    falso("un visitante no puede mandar", a.puede_mandar(None))
    falso("con un sid inventado tampoco", a.puede_mandar("robado"))
    e = a.estado(None)
    falso("y su estado dice que no es admin", e["admin"])
    falso("ni tiene el mando", e["mando"])


def un_solo_mando():
    print("\n  UN SOLO MANDO")
    a = nuevo()
    p = a.entrar(a.clave, "profesor")
    q = a.entrar(a.clave, "ayudante")
    cierto("los dos son admin", a.es_admin(p) and a.es_admin(q))

    cierto("el primero que ordena toma el mando", a.puede_mandar(p))
    falso("el segundo NO puede mandar", a.puede_mandar(q))
    cierto("el primero sigue mandando", a.puede_mandar(p))

    e = a.estado(q)
    cierto("el segundo ve que es admin", e["admin"])
    falso("pero que no tiene el mando", e["mando"])
    cierto("y que lo tiene alguien", e["hay_titular"])
    igual("y con que nombre", e["titular_nombre"], "profesor")

    ok, _m = a.tomar_mando(q)
    falso("no se lo puede arrebatar sin mas", ok)

    cierto("puede pedirlo", a.pedir_mando(q))
    e = a.estado(p)
    cierto("el titular ve el pedido", e["pedido_ajeno"])
    igual("y de quien es", e["pedido_nombre"], "ayudante")

    cierto("el titular puede rechazar", a.rechazar_pedido(p))
    e = a.estado(p)
    falso("y el pedido desaparece", e["pedido_ajeno"])
    falso("el que pidio sigue sin mandar", a.puede_mandar(q))

    cierto("pide de nuevo", a.pedir_mando(q))
    cierto("el titular cede", a.ceder_mando(p))
    cierto("y el mando pasa al que pidio", a.estado(q)["mando"])
    falso("el que cedio ya no manda", a.puede_mandar(p))


def el_que_se_fue():
    print("\n  EL QUE SE FUE CON LA PAGINA ABIERTA")
    a = nuevo()
    p = a.entrar(a.clave, "profesor")
    q = a.entrar(a.clave, "ayudante")
    cierto("el profesor toma el mando", a.puede_mandar(p))

    # se va: no vuelve a dar senales. Se simula moviendo el reloj hacia atras
    # en vez de esperar 45 segundos de verdad.
    a.visto_titular -= acceso.MANDO_ABANDONADO + 1
    cierto("pasado el abandono, el mando se considera libre",
           a.estado(q)["mando_libre"])
    ok, _m = a.tomar_mando(q)
    cierto("y el otro lo puede tomar", ok)
    cierto("ahora manda el ayudante", a.puede_mandar(q))
    falso("y el que se fue ya no", a.puede_mandar(p))


def el_que_no_contesta():
    print("\n  EL QUE NO CONTESTA EL PEDIDO")
    a = nuevo()
    p = a.entrar(a.clave, "profesor")
    q = a.entrar(a.clave, "ayudante")
    a.puede_mandar(p)
    a.pedir_mando(q)
    ok, _m = a.tomar_mando(q)
    falso("recien pedido, todavia no se lo puede quedar", ok)

    a.pedido["cuando"] -= acceso.ESPERA_CESION + 1
    e = a.estado(q)
    igual("la cuenta regresiva llego a cero", e["pedido_resta"], 0)
    ok, motivo = a.tomar_mando(q)
    cierto("pasada la espera, se lo queda", ok)
    igual("y dice por que", motivo, "tomado por falta de respuesta")


def la_sesion_vence():
    print("\n  LA SESION QUE VENCE")
    d = tempfile.mkdtemp()
    a = Acceso(os.path.join(d, "s.json"), vida_sesion=0.2)
    sid = a.entrar(a.clave)
    cierto("recien entrado es admin", a.es_admin(sid))
    time.sleep(0.35)
    falso("pasada la vida de la sesion, ya no", a.es_admin(sid))
    falso("y no puede mandar", a.puede_mandar(sid))


def salir_libera():
    print("\n  SALIR")
    a = nuevo()
    p = a.entrar(a.clave, "profesor")
    a.puede_mandar(p)
    a.salir(p)
    falso("el que salio no es admin", a.es_admin(p))
    q = a.entrar(a.clave, "otro")
    cierto("y el mando quedo libre", a.estado(q)["mando_libre"])


# ===========================================================================
if __name__ == "__main__":
    print("=" * 74)
    print(" ACCESO: quien mira, quien puede mandar, quien manda ahora")
    print("=" * 74)
    clave_y_sesiones()
    el_visitante_no_manda()
    un_solo_mando()
    el_que_se_fue()
    el_que_no_contesta()
    la_sesion_vence()
    salir_libera()
    print("")
    print("=" * 74)
    if fallos:
        print(" FALLARON %d:" % len(fallos))
        for f in fallos:
            print("   %s" % f)
    else:
        print(" Todo bien.")
    print("=" * 74)
    sys.exit(1 if fallos else 0)
