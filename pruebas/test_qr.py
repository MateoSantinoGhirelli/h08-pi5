# -*- coding: utf-8 -*-
"""Que los códigos QR se puedan LEER.

    python3 -m unittest pruebas.test_qr -v

No mira el dibujo: lo decodifica. Genera los códigos con h08/web/qr.py, los rasteriza
y se los da a un lector de verdad, el de OpenCV, a ver si sale el mismo texto que
entró. Escribiendo qr.py aparecieron tres errores que daban códigos impecables a
simple vista: el polinomio de Reed-Solomon espejado, el bloque de información de
versión faltante (de la 7 en adelante) y el contador de caracteres fijo en 8 bits,
que desde la versión 10 son 16. El último es el peor: las versiones 1 a 9 andaban y
sólo fallaba la 10, la de los textos largos. Por eso se recorren las diez.

Si OpenCV no está, la prueba figura como salteada: no es una dependencia del tablero,
es una herramienta de este control y en la Raspberry no hace falta.
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
             # que es el código más cargado que genera el proyecto
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
