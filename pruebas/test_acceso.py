# -*- coding: utf-8 -*-
"""Que el visitante no pueda mandar, y que el mando se ceda.

Prueba h08/web/acceso.py sin levantar ningún servidor. Son las reglas que
deciden quien puede meterle una falla al tablero delante de un curso, así que
conviene que estén probadas de verdad y no "se ve que anda".

    python3 -m unittest pruebas.test_acceso -v
"""
import os
import tempfile
import time
import unittest

from h08.web import acceso
from h08.web.acceso import Acceso
from pruebas.comun import Prueba


def nuevo():
    d = tempfile.mkdtemp()
    return Acceso(os.path.join(d, "secreto_admin.json"))


class LaClaveYLasSesiones(Prueba):

    def test_clave_y_sesiones(self):
        """La clave se genera, se guarda, abre sesiones y se puede renovar."""
        a = nuevo()
        self.comprobar_igual("la clave se genera sola", len(a.clave) >= 12, True)
        self.comprobar("el archivo quedo escrito", os.path.exists(a.archivo))

        self.comprobar_igual("sin clave no se entra", a.entrar(""), None)
        self.comprobar_igual("con clave equivocada no se entra", a.entrar("cualquiera"), None)
        sid = a.entrar(a.clave)
        self.comprobar("con la clave correcta se entra", sid)
        self.comprobar("y queda como admin", a.es_admin(sid))
        self.comprobar_falso("un sid inventado no es admin", a.es_admin("inventado"))
        self.comprobar_falso("sin sid no es admin", a.es_admin(None))

        # la clave que se relee del archivo es la misma
        b = Acceso(a.archivo)
        self.comprobar_igual("la clave sobrevive al reinicio", b.clave, a.clave)

        vieja = a.clave
        nueva = a.renovar_clave()
        self.comprobar("renovar da una clave distinta", nueva != vieja)
        self.comprobar_falso("la sesión vieja ya no vale", a.es_admin(sid))
        self.comprobar_igual("la clave vieja ya no entra", a.entrar(vieja), None)
        self.comprobar("la nueva si", a.entrar(nueva))

    @unittest.skipIf(os.name == "nt", "Windows no tiene permisos de dueño/grupo/otros: "
                                      "se comprueba en la Pi")
    def test_el_archivo_es_solo_del_duenio(self):
        """El archivo de la clave sólo lo puede leer su dueño (600)."""
        a = nuevo()
        modo = os.stat(a.archivo).st_mode & 0o777
        self.comprobar_igual("el archivo es solo del duenio", oct(modo), oct(0o600))


class ElVisitante(Prueba):

    def test_el_visitante_no_manda(self):
        """Sin clave no se es admin ni se puede mandar."""
        a = nuevo()
        self.comprobar_falso("un visitante no es admin", a.es_admin(None))
        self.comprobar_falso("un visitante no puede mandar", a.puede_mandar(None))
        self.comprobar_falso("con un sid inventado tampoco", a.puede_mandar("robado"))
        e = a.estado(None)
        self.comprobar_falso("y su estado dice que no es admin", e["admin"])
        self.comprobar_falso("ni tiene el mando", e["mando"])


class UnSoloMando(Prueba):

    def test_un_solo_mando(self):
        """Con dos admins, manda uno solo; el otro lo pide y el titular cede o rechaza."""
        a = nuevo()
        p = a.entrar(a.clave, "profesor")
        q = a.entrar(a.clave, "ayudante")
        self.comprobar("los dos son admin", a.es_admin(p) and a.es_admin(q))

        self.comprobar("el primero que ordena toma el mando", a.puede_mandar(p))
        self.comprobar_falso("el segundo NO puede mandar", a.puede_mandar(q))
        self.comprobar("el primero sigue mandando", a.puede_mandar(p))

        e = a.estado(q)
        self.comprobar("el segundo ve que es admin", e["admin"])
        self.comprobar_falso("pero que no tiene el mando", e["mando"])
        self.comprobar("y que lo tiene alguien", e["hay_titular"])
        self.comprobar_igual("y con que nombre", e["titular_nombre"], "profesor")

        ok, _m = a.tomar_mando(q)
        self.comprobar_falso("no se lo puede arrebatar sin más", ok)

        self.comprobar("puede pedirlo", a.pedir_mando(q))
        e = a.estado(p)
        self.comprobar("el titular ve el pedido", e["pedido_ajeno"])
        self.comprobar_igual("y de quien es", e["pedido_nombre"], "ayudante")

        self.comprobar("el titular puede rechazar", a.rechazar_pedido(p))
        e = a.estado(p)
        self.comprobar_falso("y el pedido desaparece", e["pedido_ajeno"])
        self.comprobar_falso("el que pidio sigue sin mandar", a.puede_mandar(q))

        self.comprobar("pide de nuevo", a.pedir_mando(q))
        self.comprobar("el titular cede", a.ceder_mando(p))
        self.comprobar("y el mando pasa al que pidio", a.estado(q)["mando"])
        self.comprobar_falso("el que cedio ya no manda", a.puede_mandar(p))


class ElQueSeFue(Prueba):

    def test_el_que_se_fue(self):
        """Si el titular deja de dar señales, el mando queda libre para otro."""
        a = nuevo()
        p = a.entrar(a.clave, "profesor")
        q = a.entrar(a.clave, "ayudante")
        self.comprobar("el profesor toma el mando", a.puede_mandar(p))

        # se va: no vuelve a dar señales. Se simula moviendo el reloj hacia atras
        # en vez de esperar 45 segundos de verdad.
        a.visto_titular -= acceso.MANDO_ABANDONADO + 1
        self.comprobar("pasado el abandono, el mando se considera libre",
                       a.estado(q)["mando_libre"])
        ok, _m = a.tomar_mando(q)
        self.comprobar("y el otro lo puede tomar", ok)
        self.comprobar("ahora manda el ayudante", a.puede_mandar(q))
        self.comprobar_falso("y el que se fue ya no", a.puede_mandar(p))


class ElQueNoContesta(Prueba):

    def test_el_que_no_contesta(self):
        """Si el titular no contesta un pedido a tiempo, el que pidió se queda el mando."""
        a = nuevo()
        p = a.entrar(a.clave, "profesor")
        q = a.entrar(a.clave, "ayudante")
        a.puede_mandar(p)
        a.pedir_mando(q)
        ok, _m = a.tomar_mando(q)
        self.comprobar_falso("recien pedido, todavía no se lo puede quedar", ok)

        a.pedido["cuando"] -= acceso.ESPERA_CESION + 1
        e = a.estado(q)
        self.comprobar_igual("la cuenta regresiva llego a cero", e["pedido_resta"], 0)
        ok, motivo = a.tomar_mando(q)
        self.comprobar("pasada la espera, se lo queda", ok)
        self.comprobar_igual("y dice por que", motivo, "tomado por falta de respuesta")


class LaSesionVence(Prueba):

    def test_la_sesion_vence(self):
        """Pasada su vida útil, una sesión deja de ser admin."""
        d = tempfile.mkdtemp()
        a = Acceso(os.path.join(d, "s.json"), vida_sesion=0.2)
        sid = a.entrar(a.clave)
        self.comprobar("recien entrado es admin", a.es_admin(sid))
        time.sleep(0.35)
        self.comprobar_falso("pasada la vida de la sesión, ya no", a.es_admin(sid))
        self.comprobar_falso("y no puede mandar", a.puede_mandar(sid))


class Salir(Prueba):

    def test_salir_libera(self):
        """Salir cierra la sesión y libera el mando."""
        a = nuevo()
        p = a.entrar(a.clave, "profesor")
        a.puede_mandar(p)
        a.salir(p)
        self.comprobar_falso("el que salio no es admin", a.es_admin(p))
        q = a.entrar(a.clave, "otro")
        self.comprobar("y el mando quedo libre", a.estado(q)["mando_libre"])


if __name__ == "__main__":
    unittest.main()
