#!/usr/bin/env bash
# ===========================================================================
#  instalar.sh - deja la Raspberry Pi 5 lista para el tablero H-08
# ===========================================================================
#  Proyecto H-08 · Tablero didáctico del Sikorsky S-55 / H-19A
#  EEST N° 7 - Taller Regional Quilmes
#
#  Se corre UNA vez, con el usuario normal (no con sudo delante), en
#  Raspberry Pi OS CON ESCRITORIO (Bookworm o posterior, 64 bits):
#
#      bash instalar.sh                 todo
#      bash instalar.sh --sin-kiosco    sin abrir el tablero en la pantalla
#      bash instalar.sh --sin-wifi      sin la red wifi propia
#      bash instalar.sh --quitar-kiosco deja de abrirse solo en la pantalla
#
#  Hace esto:
#    1. instala los paquetes del sistema (gpiozero, lgpio, i2c-tools,
#       chromium, rsync, unzip);
#    2. habilita el I2C a 400 kHz;
#    3. agrega el usuario a los grupos i2c, gpio y video;
#    4. genera la clave de administrador;
#    5. instala el servicio tablero-h08, que arranca solo al encender y se
#       apaga en orden (luces, servos y motores a cero) al apagar;
#    6. PANTALLA: el escritorio entra solo (sin pedir usuario), la pantalla
#       no se apaga, y el tablero se abre a pantalla completa (kiosco.sh);
#    7. WIFI: la Raspberry levanta su propia red (Tablero-H08) al encender,
#       para que el público entre desde el celular con el QR.
#
#  No usa entorno virtual ni pip: todo lo que hace falta viene del sistema.
#  Al terminar hay que REINICIAR una vez.
# ===========================================================================
set -e

AQUI="$(cd "$(dirname "$0")" && pwd)"
USUARIO="$(id -un)"
SERVICIO=tablero-h08
KIOSCO=si
WIFI=si
AUTOSTART="$HOME/.config/autostart/tablero-kiosco.desktop"
# El escritorio de Raspberry Pi OS (Bookworm y Trixie) es Wayland con labwc. El
# tutorial oficial de kiosco usa ~/.config/labwc/autostart; se deja el arranque
# en los dos lugares y kiosco.sh tiene un candado, así nunca se abre dos veces.
LABWC="$HOME/.config/labwc/autostart"

for a in "$@"; do
    case "$a" in
        --sin-kiosco) KIOSCO=no ;;
        --sin-wifi) WIFI=no ;;
        --quitar-kiosco)
            rm -f "$AUTOSTART"
            [ -f "$LABWC" ] && sed -i '/kiosco.sh/d' "$LABWC"
            bash "$AQUI/kiosco.sh" parar >/dev/null 2>&1 || true
            echo "Listo: el tablero ya no se abre solo en la pantalla."
            echo "El servicio sigue andando: se ve desde el navegador en http://localhost:8000/"
            exit 0 ;;
        *) echo "Opción desconocida: $a"; exit 1 ;;
    esac
done

if [ "$(id -u)" = "0" ]; then
    echo "Correrlo sin sudo delante:  bash instalar.sh"
    exit 1
fi

echo "== 1. Paquetes del sistema =="
sudo apt-get update
sudo apt-get install -y python3 python3-gpiozero python3-lgpio i2c-tools rsync unzip
if [ "$KIOSCO" = "si" ] && ! command -v chromium >/dev/null && ! command -v chromium-browser >/dev/null; then
    sudo apt-get install -y chromium || sudo apt-get install -y chromium-browser
fi

echo
echo "== 2. I2C =="
if command -v raspi-config >/dev/null; then
    sudo raspi-config nonint do_i2c 0
fi
CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt
if [ -f "$CONFIG" ]; then
    if ! grep -q "^dtparam=i2c_arm=on" "$CONFIG"; then
        echo "dtparam=i2c_arm=on" | sudo tee -a "$CONFIG" >/dev/null
    fi
    if ! grep -q "^dtparam=i2c_arm_baudrate=" "$CONFIG"; then
        echo "dtparam=i2c_arm_baudrate=400000" | sudo tee -a "$CONFIG" >/dev/null
    fi
    echo "   I2C habilitado en $CONFIG"
fi

echo
echo "== 3. Grupos del usuario $USUARIO =="
sudo usermod -aG i2c,gpio,video "$USUARIO"

echo
echo "== 4. Clave de administrador =="
python3 "$AQUI/tablero_pi5.py" --qr-admin >/dev/null
chmod 600 "$AQUI/secreto_admin.json"
echo "   Generada. Se ve con:  python3 tablero_pi5.py --qr-admin"

echo
echo "== 5. Servicio $SERVICIO =="
chmod +x "$AQUI"/*.sh "$AQUI"/*.py 2>/dev/null || true
sudo tee /etc/systemd/system/$SERVICIO.service >/dev/null <<FIN
[Unit]
Description=Tablero didáctico Sikorsky S-55 H-08
After=network.target

[Service]
Type=simple
User=$USUARIO
SupplementaryGroups=i2c gpio video
WorkingDirectory=$AQUI
ExecStart=/usr/bin/python3 $AQUI/tablero_pi5.py
Restart=on-failure
RestartSec=5
# Al detenerse lleva la aguja de la brújula a cero: le damos tiempo.
TimeoutStopSec=20
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
FIN
sudo systemctl daemon-reload
sudo systemctl enable $SERVICIO

echo
if [ "$KIOSCO" = "si" ]; then
    echo "== 6. Pantalla: escritorio sin contraseña, sin apagarse y el tablero abierto =="
    if command -v raspi-config >/dev/null; then
        sudo raspi-config nonint do_boot_behaviour B4    # escritorio, entra solo
        sudo raspi-config nonint do_blanking 1           # la pantalla no se apaga
    else
        echo "   (sin raspi-config: el inicio automático y el protector de pantalla hay que dejarlos a mano)"
    fi
    mkdir -p "$(dirname "$AUTOSTART")"
    cat > "$AUTOSTART" <<FIN
[Desktop Entry]
Type=Application
Name=Tablero H-08 (kiosco)
Comment=Abre el tablero a pantalla completa al encender
Exec=/bin/bash $AQUI/kiosco.sh
X-GNOME-Autostart-enabled=true
FIN
    mkdir -p "$(dirname "$LABWC")"
    touch "$LABWC"
    grep -q "kiosco.sh" "$LABWC" || echo "/bin/bash $AQUI/kiosco.sh &" >> "$LABWC"
    echo "   El tablero se abre solo al encender ($AUTOSTART y $LABWC)"
    echo "   Para usar el escritorio:  bash kiosco.sh parar"
else
    echo "== 6. Pantalla: se deja como está (--sin-kiosco) =="
fi

echo
if [ "$WIFI" = "si" ]; then
    echo "== 7. Red wifi propia =="
    # 'preparar' no la levanta ahora (cortaría una conexión por wifi, si se
    # está instalando así): queda lista para el próximo encendido.
    sudo bash "$AQUI/punto_de_acceso.sh" preparar
    echo "   Si hace falta volver a la red de la escuela:  sudo bash punto_de_acceso.sh apagar"
else
    echo "== 7. Red wifi propia: no (--sin-wifi) =="
fi

echo
echo "=========================================================================="
echo " Listo. FALTA REINICIAR UNA VEZ:   sudo reboot"
echo
echo " Después del reinicio, solo:"
echo "   - arranca el servicio del tablero (servos, luces, brújula y página);"
[ "$KIOSCO" = "si" ] && echo "   - la pantalla muestra el tablero, con los QR para entrar desde el celular;"
[ "$WIFI" = "si" ] && echo "   - la red Tablero-H08 queda levantada: http://10.55.0.1:8000/"
echo
echo " Para comprobar todo:        python3 diagnostico_pi.py"
echo " Prueba general guiada:      python3 prueba_general.py"
echo " QR del profesor:            python3 tablero_pi5.py --qr-admin"
echo " Ver lo que hace:            journalctl -u $SERVICIO -f"
echo "=========================================================================="
