# -*- coding: utf-8 -*-
"""
test_qr.py - que los codigos QR se puedan LEER
==============================================

No mira el dibujo: lo decodifica. Genera codigos con h08/web/qr.py, los
rasteriza y se los da a un lector de verdad -el de OpenCV- a ver si sale el
mismo texto que entro.

    python3 -m unittest pruebas.test_qr -v

POR QUE ASI Y NO MIRANDO EL DIBUJO
---------------------------------------------------------------------------
Escribiendo qr.py hubo tres errores, y los tres daban un codigo que a simple
vista era impecable:

  1. el polinomio generador de Reed-Solomon salia espejado, asi que los bytes
     de correccion de error eran basura;
  2. faltaba el bloque de informacion de version, que llevan las versiones 7
     en adelante, y ademas sus 36 casillas quedaban libres y el zigzag de
     datos las pisaba;
  3. el contador de caracteres estaba fijo en 8 bits, y desde la version 10
     son 16.

Ninguno de los tres se ve. El tercero es el peor de todos: las versiones 1 a
9 andaban perfecto y solo fallaba la 10, que es la que aparece con textos
largos. Un dia funciona y al otro no, sin que nadie haya tocado nada.

Por eso la prueba recorre las diez versiones y no una sola.

SI OPENCV NO ESTA
---------------------------------------------------------------------------
La prueba figura como salteada: OpenCV no es una dependencia del tablero, es
una herramienta de este control. En la Raspberry no hace falta.
"""
import random
import string
import unittest

from h08.web import qr
from pruebas.comun import Prueba

try:
    import cv2
    import numpy as np
except ImportError:
    cv2 = None


def _imagen(matriz, escala=8, borde=4):
    n = len(matriz)
    lado = (n + 2 * borde) * escala
    im = np.full((lado, lado), 255, dtype=np.uint8)
    for y in range(n):
        for x in range(n):
            if matriz[y][x]:
                im[(y + borde) * escala:(y + borde + 1) * escala,
                   (x + borde) * escala:(x + borde + 1) * escala] = 0
    return im


def casos():
    lista = ["http://192.168.1.45:8000/",
             # una URL larga con clave adentro: es la del QR de administrador,
             # que es el codigo mas cargado que genera el proyecto
             "http://10.0.0.7:8000/mando?k=JXUuz0XJvfjplbVW7QOAqA",
             "http://tablero-h08.local:8000/",
             "WIFI:T:WPA;S:Tablero-H08;P:sikorsky55;;",
             "H-08", "a"]
    azar = random.Random(20260828)
    alfabeto = string.ascii_letters + string.digits + "/:.-_?=&"
    for largo in list(range(1, 60)) + [80, 100, 120, 140, 160, 180, 200, 213]:
        lista.append("".join(azar.choice(alfabeto) for _ in range(largo)))
    return lista


@unittest.skipIf(cv2 is None, "OpenCV no está instalado: no se puede comprobar la lectura")
class LosCodigosSeLeen(Prueba):

    def test_se_leen_en_las_diez_versiones(self):
        """Cada texto de 1 a 213 caracteres se genera y un lector de verdad lo lee igual."""
        lector = cv2.QRCodeDetector()
        versiones = set()
        fallados = []
        for texto in casos():
            m = qr.matriz(texto)
            version = (len(m) - 17) // 4
            versiones.add(version)
            try:
                leido, _, _ = lector.detectAndDecode(_imagen(m))
            except cv2.error:
                leido = ""
            if leido != texto:
                fallados.append((len(texto), version, leido[:30]))
        self.comprobar("todos los códigos se leen", not fallados, fallados[:10])
        faltan = [v for v in range(1, 11) if v not in versiones]
        self.comprobar("se recorrieron las diez versiones", not faltan, faltan)


if __name__ == "__main__":
    unittest.main()
