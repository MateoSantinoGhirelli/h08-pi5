#!/usr/bin/env bash
# ===========================================================================
#  actualizar.sh - pasa a la Raspberry una versión nueva del programa
# ===========================================================================
#  Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
#  EEST N° 7 - Taller Regional Quilmes
#
#      bash actualizar.sh /media/$USER/PENDRIVE/H08_Pi5.zip
#      bash actualizar.sh /ruta/a/la/carpeta/H08_Pi5
#
#  Copia el programa nuevo ENCIMA del instalado, sin tocar lo que es de ESTE
#  tablero y no viaja en el paquete:
#      secreto_admin.json       la clave del QR del profesor
#      calibracion_servos.json  lo medido en cada servo
#      posicion_motores.json    dónde quedó la aguja de la brújula
#  Guarda antes una copia de lo instalado (../H08_respaldo_FECHA) y reinicia
#  el servicio. La pantalla de la Raspberry se recarga sola con la versión
#  nueva; los celulares, al recargar la página.
# ===========================================================================
set -e

ORIGEN="${1:-}"
AQUI="$(cd "$(dirname "$0")" && pwd)"          # .../H08_Pi5/raspberry_pi5
RAIZ="$(dirname "$AQUI")"                      # .../H08_Pi5
SERVICIO=tablero-h08

if [ -z "$ORIGEN" ] || [ ! -e "$ORIGEN" ]; then
    echo "Uso:  bash actualizar.sh ARCHIVO.zip | CARPETA"
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
# la que tiene raspberry_pi5/tablero_pi5.py.
NUEVO="$(dirname "$(dirname "$(find "$ORIGEN" -path '*raspberry_pi5/tablero_pi5.py' | head -n1)")" 2>/dev/null || true)"
if [ -z "$NUEVO" ] || [ ! -f "$NUEVO/raspberry_pi5/tablero_pi5.py" ]; then
    echo "No encuentro raspberry_pi5/tablero_pi5.py dentro de $1"
    [ -n "$TMP" ] && rm -rf "$TMP"
    exit 1
fi

RESPALDO="$(dirname "$RAIZ")/H08_respaldo_$(date +%Y%m%d_%H%M%S)"
echo "== Respaldo de lo instalado en $RESPALDO =="
cp -a "$RAIZ" "$RESPALDO"

echo "== Deteniendo el tablero (agujas a cero) =="
sudo systemctl stop "$SERVICIO" 2>/dev/null || true

echo "== Copiando la versión nueva =="
rsync -a \
    --exclude 'secreto_admin.json' \
    --exclude 'calibracion_servos.json' \
    --exclude 'posicion_motores.json' \
    --exclude '__pycache__' \
    --exclude 'informes/' \
    "$NUEVO"/ "$RAIZ"/
# Por si algún archivo llegó con fin de línea de Windows (CRLF)
sed -i 's/\r$//' "$AQUI"/*.sh 2>/dev/null || true
chmod +x "$AQUI"/*.sh 2>/dev/null || true
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
