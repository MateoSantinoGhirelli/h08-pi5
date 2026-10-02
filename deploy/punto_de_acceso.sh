#!/usr/bin/env bash
# punto_de_acceso.sh - la Raspberry levanta su propia red wifi
#
# En una muestra puede no haber wifi, o estar saturado. Con la Raspberry
# como punto de acceso el tablero funciona en cualquier lado. La red no
# tiene internet: su único servicio es la página del tablero.
#
#      sudo bash deploy/punto_de_acceso.sh encender     levanta la red ahora
#      sudo bash deploy/punto_de_acceso.sh permanente   que se levante al encender
#      sudo bash deploy/punto_de_acceso.sh preparar     que se levante recién en el
#                                                       próximo encendido (no corta
#                                                       la conexión de ahora)
#      sudo bash deploy/punto_de_acceso.sh apagar       vuelve a la red de siempre
#      sudo bash deploy/punto_de_acceso.sh estado
#
# Raspberry Pi OS (desde Bookworm) maneja la red con NetworkManager: alcanza con
# nmcli, sin hostapd ni dnsmasq.
#
# ATENCIÓN: la placa wifi pasa a ser el punto de acceso. Si se está
# conectado a la Raspberry por wifi (SSH), la conexión se corta.
#
# El servidor web lee RED, CLAVE e IP de este archivo para armar el cartel
# con los códigos QR (http://10.55.0.1:8000/cartel): se cambian sólo acá.
set -e

RED="Tablero-H08"
CLAVE="sikorsky55"          # WPA exige 8 caracteres como mínimo
IP="10.55.0.1"
CONEXION="tablero-ap"

command -v nmcli >/dev/null || {
    echo "No se encontró NetworkManager (nmcli). Usar Raspberry Pi OS Bookworm o posterior."
    exit 1
}

crear() {
    # Desde Bookworm la placa wifi viene BLOQUEADA hasta que se elige el país.
    if command -v raspi-config >/dev/null; then
        if [ -z "$(raspi-config nonint get_wifi_country 2>/dev/null)" ]; then
            raspi-config nonint do_wifi_country AR || true
        fi
    fi
    command -v rfkill >/dev/null && rfkill unblock wifi || true
    if ! nmcli -t -f NAME connection show | grep -qx "$CONEXION"; then
        nmcli connection add type wifi ifname wlan0 con-name "$CONEXION" \
              autoconnect no ssid "$RED" >/dev/null
        nmcli connection modify "$CONEXION" \
              802-11-wireless.mode ap 802-11-wireless.band bg \
              802-11-wireless.channel 6 \
              ipv4.method shared ipv4.addresses "$IP/24" \
              wifi-sec.key-mgmt wpa-psk wifi-sec.proto rsn \
              wifi-sec.pairwise ccmp wifi-sec.psk "$CLAVE"
    fi
}

case "${1:-estado}" in
encender)
    crear
    nmcli connection up "$CONEXION"
    echo
    echo "  Red ...... $RED"
    echo "  Clave .... $CLAVE"
    echo "  Página ... http://$IP:8000/"
    echo "  Cartel ... http://$IP:8000/cartel   (para imprimir y pegar)"
    ;;
permanente)
    crear
    nmcli connection modify "$CONEXION" autoconnect yes connection.autoconnect-priority 100
    nmcli connection up "$CONEXION"
    echo "Listo: al encender, la Raspberry levanta $RED sola."
    ;;
preparar)
    crear
    nmcli connection modify "$CONEXION" autoconnect yes connection.autoconnect-priority 100
    echo "Listo: desde el próximo encendido la Raspberry levanta $RED sola."
    ;;
apagar)
    nmcli connection modify "$CONEXION" autoconnect no 2>/dev/null || true
    nmcli connection down "$CONEXION" 2>/dev/null || true
    echo "Punto de acceso apagado. La Raspberry vuelve a su red de siempre."
    ;;
estado)
    if nmcli -t -f NAME connection show --active | grep -qx "$CONEXION"; then
        echo "Punto de acceso LEVANTADO: red $RED, http://$IP:8000/"
    else
        echo "Punto de acceso apagado."
    fi
    ;;
*)
    echo "Uso: sudo bash $0 encender|permanente|preparar|apagar|estado"
    exit 1
    ;;
esac
