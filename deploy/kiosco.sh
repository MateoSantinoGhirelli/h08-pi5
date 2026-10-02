#!/usr/bin/env bash
# kiosco.sh - el tablero a pantalla completa en la pantalla de la Raspberry
#
# Lo arranca solo el escritorio al encender (instalar.sh deja el archivo
# ~/.config/autostart/tablero-kiosco.desktop). A mano:
#
#      bash deploy/kiosco.sh         abre el tablero en modo kiosco
#      bash deploy/kiosco.sh parar   lo cierra (para usar el escritorio)
#
# Qué hace:
#    1. espera a que el servicio del tablero conteste (al encender, el
#       escritorio suele estar antes que el programa);
#    2. abre Chromium en modo kiosco en http://localhost:8000/?kiosco=1, con
#       un perfil propio (no toca el Chromium de todos los días);
#    3. si Chromium se cierra o se cuelga, lo vuelve a abrir.
#
# La página se recarga sola cuando el tablero se reinicia: después de una
# actualización (actualizar.sh) la pantalla muestra la versión nueva sin
# tocar nada.

PUERTO="${TABLERO_PUERTO:-8000}"
URL="http://localhost:${PUERTO}/?kiosco=1"
PERFIL="$HOME/.config/tablero-kiosco"
RUN="${XDG_RUNTIME_DIR:-/tmp}"
PARAR="$RUN/tablero-kiosco.parar"

if [ "${1:-}" = "parar" ]; then
    touch "$PARAR"
    pkill -f -- "--user-data-dir=$PERFIL" 2>/dev/null || true
    echo "Kiosco cerrado. Se vuelve a abrir con:  bash $0"
    exit 0
fi
rm -f "$PARAR"

# Un solo kiosco a la vez (el autostart y uno abierto a mano no se pisan).
exec 9>"$RUN/tablero-kiosco.lock"
if ! flock -n 9; then
    echo "El kiosco ya está abierto."
    exit 0
fi

NAV=""
for n in chromium chromium-browser; do
    if command -v "$n" >/dev/null; then NAV="$n"; break; fi
done
if [ -z "$NAV" ]; then
    echo "No está Chromium:  sudo apt install -y chromium"
    exit 1
fi

responde() {
    python3 - "$1" <<'FIN' >/dev/null 2>&1
import sys, urllib.request
urllib.request.urlopen(sys.argv[1], timeout=2).read(1)
FIN
}

# Chromium guarda "no se cerró bien" cuando se corta la luz y al volver
# muestra un cartel de "restaurar páginas". En un kiosco no hay quien lo cierre.
limpiar_perfil() {
    local pref="$PERFIL/Default/Preferences"
    if [ -f "$pref" ]; then
        sed -i 's/"exited_cleanly":false/"exited_cleanly":true/; s/"exit_type":"[A-Za-z]*"/"exit_type":"Normal"/' "$pref" || true
    fi
}

while [ ! -e "$PARAR" ]; do
    # 1. esperar al tablero (hasta 3 minutos; después abre igual y la página
    #    se queda reintentando sola)
    for _ in $(seq 1 180); do
        responde "http://localhost:${PUERTO}/api/estado" && break
        [ -e "$PARAR" ] && exit 0
        sleep 1
    done

    limpiar_perfil
    "$NAV" --kiosk "$URL" \
        --user-data-dir="$PERFIL" \
        --noerrdialogs --disable-infobars --no-first-run \
        --disable-session-crashed-bubble --disable-features=Translate,TranslateUI \
        --password-store=basic --check-for-update-interval=31536000 \
        --overscroll-history-navigation=0 --disable-pinch \
        --ozone-platform-hint=auto >/dev/null 2>&1

    # 2. si se cerró sin pedirlo, se vuelve a abrir
    [ -e "$PARAR" ] && break
    sleep 3
done
rm -f "$PARAR"
