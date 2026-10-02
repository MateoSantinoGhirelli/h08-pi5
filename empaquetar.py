#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
empaquetar.py - arma el zip para llevar a la Raspberry
======================================================
Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A

En la computadora (Windows: py empaquetar.py, Linux/Mac: python3 empaquetar.py):

    py empaquetar.py                  corre las pruebas y, si pasan, arma
                                      dist/H08_Pi5.zip
    py empaquetar.py --sin-pruebas    lo arma sin correr las pruebas
    py empaquetar.py --salida E:\\     lo deja directo en el pendrive

En la Raspberry, la primera vez: descomprimirlo y  bash deploy/instalar.sh
Las siguientes:                  bash deploy/actualizar.sh /media/USUARIO/PENDRIVE/H08_Pi5.zip

El zip lleva h08/ (el programa), deploy/ (los scripts de la Pi) y pruebas/.
No lleva datos/ (ni raspberry_pi5/, donde estaban antes): son de cada tablero.

Tres cuidados que hace solo:
  * NUNCA mete secreto_admin.json, calibracion_servos.json ni
    posicion_motores.json (son de cada tablero): si aparecen, se niega.
  * Pasa los fines de línea a LF. En Windows los archivos pueden quedar con
    CRLF, y en la Raspberry bash falla con "$'\\r': command not found".
  * Escribe VERSION.txt con la fecha y una huella del contenido: la muestra
    el tablero al arrancar, así se sabe qué versión tiene cada Pi.
"""
import argparse
import datetime
import hashlib
import os
import subprocess
import sys
import zipfile

from h08 import rutas

AQUI = rutas.RAIZ
CARPETAS = ("h08", "deploy", "pruebas")
SUELTOS = ("LEEME.md", "CLAUDE.md", "CONTEXTO_PROYECTO.md", ".claude/settings.json", "empaquetar.py", ".gitignore", ".gitattributes")
PRIVADOS = set(rutas.PRIVADOS)
FUERA_DIR = {"__pycache__", "informes", "datos", ".venv", ".git", "dist", ".claude"}
FUERA_EXT = (".pyc", ".tmp", ".log", ".zip")
TEXTO = (".py", ".sh", ".md", ".html", ".svg", ".json", ".txt", ".desktop", ".css", ".js")
RAIZ_ZIP = "H08_Pi5"


def archivos():
    for f in SUELTOS:
        ruta = os.path.join(AQUI, f)
        if os.path.exists(ruta):
            yield ruta, f
    for c in CARPETAS:
        for base, dirs, fs in os.walk(os.path.join(AQUI, c)):
            dirs[:] = sorted(d for d in dirs if d not in FUERA_DIR)
            for f in sorted(fs):
                if f in PRIVADOS or f.endswith(FUERA_EXT):
                    continue
                ruta = os.path.join(base, f)
                yield ruta, os.path.relpath(ruta, AQUI).replace(os.sep, "/")


def leer(ruta, rel):
    with open(ruta, "rb") as f:
        datos = f.read()
    if rel.endswith(TEXTO) or rel in (".gitignore", ".gitattributes"):
        datos = datos.replace(b"\r\n", b"\n")
    return datos


def pruebas():
    print("Corriendo las pruebas antes de empaquetar (un par de minutos)...")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    r = subprocess.run([sys.executable, "-m", "pruebas"], env=env, cwd=AQUI)
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description="Arma H08_Pi5.zip para la Raspberry")
    ap.add_argument("--sin-pruebas", action="store_true", dest="sin_pruebas")
    ap.add_argument("--salida", default=os.path.join(AQUI, "dist"))
    a = ap.parse_args()

    if not a.sin_pruebas and not pruebas():
        print("\nHay pruebas que fallan: NO se armó el zip. Arreglarlas primero "
              "(o --sin-pruebas, bajo tu responsabilidad).")
        return 1

    lista = [(ruta, rel, leer(ruta, rel)) for ruta, rel in archivos()]
    h = hashlib.sha256()
    for _, rel, datos in lista:
        h.update(rel.encode("utf-8"))
        h.update(datos)
    ahora = datetime.datetime.now()
    version = ("H08_Pi5 %s  ·  huella %s\n"
               "Tablero didáctico H-08 · Sikorsky S-55 / H-19A · programa de la Raspberry Pi 5\n"
               "archivos  %d\n"
               "Se ve al arrancar el programa y en python3 -m h08 diagnostico.\n"
               % (ahora.strftime("%Y-%m-%d %H:%M"), h.hexdigest()[:12], len(lista) + 1))

    os.makedirs(a.salida, exist_ok=True)
    destino = os.path.join(a.salida, "H08_Pi5.zip")
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        def meter(rel, datos, ejecutable=False):
            info = zipfile.ZipInfo(RAIZ_ZIP + "/" + rel, date_time=ahora.timetuple()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if ejecutable else 0o644) << 16
            z.writestr(info, datos)
        meter("VERSION.txt", version.encode("utf-8"))
        for _, rel, datos in lista:
            meter(rel, datos, ejecutable=rel.endswith(".sh"))

    with zipfile.ZipFile(destino) as z:
        nombres = z.namelist()
    colados = [n for n in nombres if os.path.basename(n) in PRIVADOS]
    if colados:
        os.remove(destino)
        print("SE COLÓ UN ARCHIVO PRIVADO: %s. Zip borrado." % colados)
        return 1
    # la copia local también queda con la versión nueva
    with open(rutas.VERSION, "w", encoding="utf-8", newline="\n") as f:
        f.write(version)
    print("\nListo: %s  (%d archivos, %.0f kB)" % (destino, len(nombres),
                                                   os.path.getsize(destino) / 1024.0))
    print(version.splitlines()[0])
    print("En la Raspberry:  bash deploy/actualizar.sh RUTA/H08_Pi5.zip   "
          "(la primera vez: bash deploy/instalar.sh)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
