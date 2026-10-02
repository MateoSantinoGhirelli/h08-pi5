# -*- coding: utf-8 -*-
"""
prueba_qr.py - que los codigos QR se puedan LEER
=================================================

No mira el dibujo: lo decodifica. Genera codigos con h08/web/qr.py, los
rasteriza y se los da a un lector de verdad -el de OpenCV- a ver si sale el
mismo texto que entro.

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
La prueba avisa y no falla: OpenCV no es una dependencia del tablero, es una
herramienta de este control. En la Raspberry no hace falta.
"""
import os
import random
import string
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)          # hasta pasar a unittest (fase 4)

from h08.web import qr  # noqa: E402


def _imagen(matriz, escala=8, borde=4):
    import numpy as np
    n = len(matriz)
    lado = (n + 2 * borde) * escala
    im = np.full((lado, lado), 255, dtype=np.uint8)
    for y in range(n):
        for x in range(n):
            if matriz[y][x]:
                im[(y + borde) * escala:(y + borde + 1) * escala,
                   (x + borde) * escala:(x + borde + 1) * escala] = 0
    return im


def correr():
    try:
        import cv2                                          # noqa: F401
        import numpy                                        # noqa: F401
    except ImportError:
        print("OpenCV no esta instalado: no se puede comprobar la lectura.")
        print("La prueba no falla, pero tampoco comprueba nada.")
        return 0

    import cv2
    lector = cv2.QRCodeDetector()

    casos = ["http://192.168.1.45:8000/",
             # una URL larga con clave adentro: es la del QR de administrador,
             # que es el codigo mas cargado que genera el proyecto
             "http://10.0.0.7:8000/mando?k=JXUuz0XJvfjplbVW7QOAqA",
             "http://tablero-h08.local:8000/",
             "WIFI:T:WPA;S:Tablero-H08;P:sikorsky55;;",
             "H-08", "a"]
    random.seed(20260828)
    alfabeto = string.ascii_letters + string.digits + "/:.-_?=&"
    for largo in list(range(1, 60)) + [80, 100, 120, 140, 160, 180, 200, 213]:
        casos.append("".join(random.choice(alfabeto) for _ in range(largo)))

    por_version = {}
    fallados = []
    for texto in casos:
        m = qr.matriz(texto)
        version = (len(m) - 17) // 4
        por_version.setdefault(version, [0, 0])
        try:
            leido, _, _ = lector.detectAndDecode(_imagen(m))
        except cv2.error:
            leido = ""
        if leido == texto:
            por_version[version][0] += 1
        else:
            por_version[version][1] += 1
            fallados.append((len(texto), version, leido[:30]))

    print("=" * 70)
    print("CODIGOS QR - se generan y se DECODIFICAN con un lector de verdad")
    print("=" * 70)
    print("   %d textos, de 1 a 213 caracteres" % len(casos))
    print()
    print("   version   leidos   fallados")
    for v in sorted(por_version):
        ok, mal = por_version[v]
        print("      %2d      %4d     %4d %s" % (v, ok, mal, "" if not mal else "<--"))
    print()
    if fallados:
        print("   NO SE PUDIERON LEER:")
        for largo, v, leido in fallados[:10]:
            print("      %d caracteres, version %d, se leyo %r" % (largo, v, leido))
        print("=" * 70)
        print("HAY %d CODIGO(S) QUE NO SE LEEN" % len(fallados))
        print("=" * 70)
        return 1

    # y que las diez versiones se hayan recorrido de verdad
    faltan = [v for v in range(1, 11) if v not in por_version]
    if faltan:
        print("   OJO: no se probaron las versiones %s" % faltan)
        print("=" * 70)
        return 1

    print("=" * 70)
    print("LOS %d CODIGOS SE LEEN, EN LAS DIEZ VERSIONES" % len(casos))
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(correr())
