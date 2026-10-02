#!/usr/bin/env bash
# ===========================================================================
#  actualizar.sh - pasa a la Raspberry una versión nueva del programa
# ===========================================================================
#  Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
#  EEST N° 7 - Taller Regional Quilmes
#
#      bash deploy/actualizar.sh /media/$USER/PENDRIVE/H08_Pi5.zip
#      bash deploy/actualizar.sh /ruta/a/la/carpeta/H08_Pi5
#
#  Deja la carpeta igual al paquete nuevo (lo que el paquete ya no trae, se
#  borra), sin tocar lo que es de ESTE tablero y no viaja en el paquete, que
#  está en datos/:
#      secreto_admin.json       la clave del QR del profesor
#      calibracion_servos.json  lo medido en cada servo
#      posicion_motores.json    dónde quedó la aguja de la brújula
#      informes/                lo que guardan las pruebas guiadas
#  raspberry_pi5/ tampoco se toca: si quedaron datos ahí, el tablero los pasa
#  a datos/ al arrancar.
#  Guarda antes una copia de lo instalado (../H08_respaldo_FECHA) y reinicia
#  el servicio. La pantalla de la Raspberry se recarga sola con la versión
#  nueva; los celulares, al recargar la página.
#
#  Para pasar desde la versión vieja (la que arrancaba desde raspberry_pi5/)
#  no sirve: ver «Pasar de la versión vieja a la nueva» en LEEME.md.
# ===========================================================================
set -e

ORIGEN="${1:-}"
DEPLOY="$(cd "$(dirname "$0")" && pwd)"        # .../H08_Pi5/deploy
RAIZ="$(dirname "$DEPLOY")"                    # .../H08_Pi5
SERVICIO=tablero-h08

if [ -z "$ORIGEN" ] || [ ! -e "$ORIGEN" ]; then
    echo "Uso:  bash deploy/actualizar.sh ARCHIVO.zip | CARPETA"
    exit 1
fi

if ! grep -qs -- "-m h08" "/etc/systemd/system/$SERVICIO.service"; then
    echo "El servicio $SERVICIO no está instalado con la versión nueva (python3 -m h08)."
    echo "Primero:  bash deploy/instalar.sh   (ver «Pasar de la versión vieja a la nueva» en LEEME.md)"
    exit 1
fi

command -v rsync >/dev/null || { echo "Falta rsync:  sudo apt install -y rsync"; exit 1; }

TMP=""
if [ -f "$ORIGEN" ]; then
    command -v unzip >/dev/null || { echo "Falta unzip:  sudo apt install -y unzip"; exit 1; }
    TMP="$(mktemp -d)"
    unzip -q "$ORIGEN" -d "$TMP"
    ORIGEN="$TMP"
fi
# El paquete puede traer una carpeta arriba de todo (H08_Pi5/...): se busca
# la que tiene h08/__main__.py.
NUEVO="$(dirname "$(dirname "$(find "$ORIGEN" -path '*h08/__main__.py' | head -n1)")" 2>/dev/null || true)"
if [ -z "$NUEVO" ] || [ ! -f "$NUEVO/h08/__main__.py" ]; then
    echo "No encuentro h08/__main__.py dentro de $1"
    [ -n "$TMP" ] && rm -rf "$TMP"
    exit 1
fi

RESPALDO="$(dirname "$RAIZ")/H08_respaldo_$(date +%Y%m%d_%H%M%S)"
echo "== Respaldo de lo instalado en $RESPALDO =="
cp -a "$RAIZ" "$RESPALDO"

echo "== Deteniendo el tablero (agujas a cero) =="
sudo systemctl stop "$SERVICIO" 2>/dev/null || true

echo "== Copiando la versión nueva =="
# --delete borra lo que el paquete nuevo ya no trae. Lo excluido no se copia ni
# se borra: los datos del tablero, un entorno virtual si algún día hace falta
# (CONTEXTO_PROYECTO.md, 5.3) y la caché de Python.
rsync -a --delete \
    --exclude '/datos/' \
    --exclude '/raspberry_pi5/' \
    --exclude '/.venv/' \
    --exclude 'secreto_admin.json' \
    --exclude 'calibracion_servos.json' \
    --exclude 'posicion_motores.json' \
    --exclude '__pycache__' \
    --exclude 'informes/' \
    "$NUEVO"/ "$RAIZ"/
# Por si algún archivo llegó con fin de línea de Windows (CRLF)
sed -i 's/\r$//' "$DEPLOY"/*.sh 2>/dev/null || true
chmod +x "$DEPLOY"/*.sh 2>/dev/null || true
[ -n "$TMP" ] && rm -rf "$TMP"

echo "== Arrancando el tablero =="
sudo systemctl start "$SERVICIO"
sleep 3
if systemctl is-active --quiet "$SERVICIO"; then
    echo "Listo. La pantalla se recarga sola en unos segundos."
    echo "Si algo salió mal, lo anterior está entero en: $RESPALDO"
else
    echo "El servicio no arrancó:  journalctl -u $SERVICIO -n 50"
    echo "Para volver atrás:  sudo systemctl stop $SERVICIO; rm -rf '$RAIZ'; mv '$RESPALDO' '$RAIZ'; sudo systemctl start $SERVICIO"
    exit 1
fi
