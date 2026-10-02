# CONTEXTO DEL PROYECTO · Tablero H-08 en la Raspberry Pi 5

> Documento para Claude Code. Explica **qué es el proyecto, qué tiene que hacer el
> programa en la Raspberry Pi 5, cómo está armado el hardware y en qué formato tiene
> que estar instalado un programa en la Pi 5**. Leelo entero antes de un cambio
> grande. Las reglas cortas de todos los días están en `CLAUDE.md`.
> El código actual ya cumple todo esto: la tarea es mantenerlo, corregirlo y
> mejorarlo **sin romper el formato descrito acá**.

---

## 1. Qué es

Tablero didáctico de cabina de un helicóptero **Sikorsky S-55 / H-19A, matrícula
H-08**, hecho por la EEST N° 7 (Taller Regional Quilmes). Una chapa con réplicas
impresas en 3D de los instrumentos. Cada aguja la mueve un servo (o un motor paso
a paso), detrás hay una placa madre propia y una **Raspberry Pi 5** corre un
simulador de vuelo que decide qué marca cada instrumento.

Sirve para enseñar: el profesor elige un modo (vuelo normal, escenario de
emergencia o una falla puntual) desde el celular, y los alumnos ven cómo
reacciona todo el tablero, en el tablero físico y en una página web.

## 2. Qué tiene que hacer el programa en la Pi (requisitos)

1. **Arrancar solo al encender**, sin teclado ni nadie que lo lance.
2. **Mover cada instrumento** según el simulador:
   - 20 servos por dos placas PCA9685 (I2C);
   - 6 luces de alerta (LED, también por PCA9685);
   - 1 motor paso a paso 28BYJ-48 para la aguja de la brújula (GPIO).
   Cada uno con su escala, su calibración, su mecánica (engranajes) y una aguja
   que se mueve con inercia, no a los saltos.
3. **Luces que se comportan como en el avión**: cada una se enciende por su
   condición del modelo, se apagan todas sin energía eléctrica, y existe la prueba
   de lámparas.
4. **Página web** (puerto 8000):
   - en la **pantalla HDMI de la Pi**, a pantalla completa (kiosco) desde el
     encendido, con los QR para entrar desde el celular;
   - en **celulares y tablets** por la **wifi propia** de la Pi (Tablero-H08);
   - la **botonera del profesor** (/mando) sólo con la clave del QR del profesor.
5. **Apagado ordenado**: al detener el servicio o apagar, luces apagadas, servos
   sin pulso y la brújula vuelve a su cero y guarda la posición.
6. **Seguir andando aunque falte hardware**: si no responde el I2C, sigue sólo
   con la página. Un error en una vuelta del lazo se cuenta y no congela nada.
7. **Pruebas** para comprobar todo: automáticas sin hardware (PC) y guiadas en
   la Pi (diagnóstico, luces y motor, instrumento por instrumento, general).
8. **Actualizarse** con un zip en un pendrive sin perder lo que es de ese tablero
   (clave, calibración de servos, posición del motor).

## 3. Hardware

### 3.1 Placas y direcciones
- Raspberry Pi 5, fuente oficial 27 W (5,1 V 5 A).
- **PCA0 = 0x40** (sin puentes) y **PCA1 = 0x41** (puente A0 soldado), bus I2C 1
  (GPIO2 SDA, GPIO3 SCL), 50 Hz, salida totem-pole (OUTDRV).
- Lógica de los PCA9685 a 3,3 V de la Pi. **V+ de servos desde una fuente aparte
  (módulo LM2596, 3 A máx.)**, nunca desde la Pi. GND unidos.
- Servos MG90S: 500–2500 µs nominal; cada uno puede tener sus extremos medidos en
  `calibracion_servos.json`.
- Motor 28BYJ-48 con su plaquita ULN2003: IN1..IN4 = **GPIO 12, 16, 20, 21**
  (patas 32, 36, 38, 40). Medio paso, 4075,77 pasos por vuelta (no 4096).
  El lugar del motor 0 (GPIO 6, 13, 19, 26) está libre.
- **La placa madre salió espejada**: en J1 las columnas par/impar quedaron
  cambiadas, el cable plano no sirve, se cablea con Dupont **por función**. El
  código no cambia. El KiCad no se toca.

### 3.2 Canales

| Canal | Id | Tipo | Mecánica | Señal y escala |
|---|---|---|---|---|
| PCA0:0 | FUEL_QTY_FWD | SERVO | barre 120°, aguja directa | fuel_fwd_l 0..378 L |
| PCA0:1 | OIL_TEMP | SERVO | barre 270°, engranajes 36/24, servo al revés | oil_t_c 0..100 °C |
| PCA0:2 | OIL_PRESS | SERVO | 270°, 36/24, al revés | oil_p_psi 0..150 psi |
| PCA0:3 | FUEL_PRESS | SERVO | 270°, 36/24, al revés | fuel_p_psi 0..25 psi |
| PCA0:4 | CARB_AIR_TEMP | SERVO | 270°, 36/24, al revés | cat_c −50..50 °C |
| PCA0:5 | CHT | SERVO | 270°, 36/24, al revés | cht_c 0..350 °C |
| PCA0:6 | AIRSPEED | SERVO | 300°, 40/24, al revés | ias_kt 0..120 kt |
| PCA0:7 | TACH_ENG | SERVO | 300°, 40/24, al revés | n_eng_rpm 0..3500 RPM |
| PCA0:9 | ALTIMETER | SERVO | 360°, 48/24, al revés | alt_ind_ft 0..10000 ft |
| PCA0:10 | VSI | SERVO | 300°, 40/24, al revés (cero a las 9) | vs_ind_fpm −2000..2000 |
| PCA0:11 | TURN | SERVO | barre 60°, directa | turn_rate_dps −6..6 °/s |
| PCA0:13 | ATT_PITCH | SERVO | horizonte: yugo escocés | pitch_ind_deg −30..30° |
| PCA0:14 | ATT_ROLL | SERVO | horizonte: plato 70/50, al revés | roll_ind_deg −60..60° |
| PCA0:15 | VOR_CDI | SERVO | barre 40°, directa | cdi −5..5 puntos |
| PCA1:0 | MAP | SERVO | 270°, 36/24, al revés | map_inhg 10..50 inHg |
| PCA1:1 | XMSN_OIL_TEMP | SERVO | 270°, 36/24, al revés | xmsn_t_c 0..150 °C |
| PCA1:2 | XMSN_OIL_PRESS | SERVO | 270°, 36/24, al revés | xmsn_p_psi 0..100 psi |
| PCA1:3 | AMMETER | SERVO | barre 120°, directa | amp_a −50..200 A |
| PCA1:4 | VOLTMETER | SERVO | barre 120°, directa | bus_v 0..32 V |
| PCA1:5 | FUEL_QTY_AFT | SERVO | barre 120°, directa | fuel_aft_l 0..322 L |
| GPIO 12-16-20-21 | COMPASS | MOTOR | paso a paso, giro continuo, rosa fija | hdg_ind_deg 0..360° |
| PCA1:8 | LT_FUEL_FWD | LED ámbar | combustible delantero < 45 L | |
| PCA1:9 | LT_FUEL_AFT | LED ámbar | combustible trasero < 45 L | |
| PCA1:10 | LT_XMSN_PRESS | LED rojo | presión transmisión < 30 psi con rotor > 60 RPM | |
| PCA1:11 | LT_GEN | LED rojo | batería conectada y generador fuera de línea | |
| PCA1:12 | LT_LOW_ROTOR | LED rojo | rotor entre 40 y 170 RPM | |
| PCA1:13 | LT_STARTER | LED verde «IGNITION» | magnetos activos | |

Libres: PCA0:8, PCA0:12, PCA1:6, PCA1:7, PCA1:14, PCA1:15. Sólo en la página (sin
actuador): TACH_ROT, SLIP, ALTIMETER_100. El reloj es mecánico (sólo página).
La fuente de verdad de esta tabla es `nucleo/configuracion.py` (`TABLERO`): si
algo de acá difiere, manda el código.

### 3.3 Luces
- Ánodo a +5 V (J8), cátodo por 220 Ω (R2..R7) al canal del PCA1 (J7):
  **encienden con la salida en BAJO** (`LUCES_ACTIVAS_EN_BAJO = True`).
- Al dar energía, antes de que arranque el servicio, el PCA9685 tiene todo en bajo
  → las 6 prenden: es la prueba de lámparas del encendido (normal).
- Sin energía en la barra (< 20 V) se apagan todas aunque la alarma siga.
- Luz fantasma posible con la salida en alto (3,3 V): se arregla con un 1N4148 en
  serie en la placa, no en el programa.

### 3.4 La cuenta de cada aguja (no romperla)
```
valor  → interpolar_tabla(valor, cal)      # tabla en 0..180 "unidades de dial"
       × factor_servo(id)                  # (barrido/180) / reducción
       = ángulo del servo 0..180
       → pulso: us_0 + (us_180 − us_0)·ángulo/180, con la calibración del servo
         y los extremos intercambiados si invertido(id) (hay par de engranajes)
```
- Barrido > 180°: el servo recorre 0..180 y el par multiplica ×1,5 / ×1,667 / ×2.
- Las carátulas impresas y la página ponen cada marca en
  `ang_dibujo = centro + B/2 − a·B/180` (si B ≥ 360: `centro − a`), con
  `centro = 90` salvo VSI (180). Por eso **la tabla `cal` no se toca para calzar
  una aguja**: se calza la aguja o se calibra el servo.

## 4. Arquitectura del software

```
H08_Pi5/
├── CLAUDE.md, CONTEXTO_PROYECTO.md, LEEME.md, VERSION.txt, empaquetar.py
├── nucleo/          modelo, fallas, escenarios, simulador, señales, mapa,
│                    actuadores (PCA9685, simulados), paso a paso, servidor web,
│                    acceso (clave), qr, utiles, configuracion
├── raspberry_pi5/   tablero_pi5.py, hilo_simulacion.py, instalar.sh,
│                    kiosco.sh, punto_de_acceso.sh, actualizar.sh, pruebas
│                    guiadas, ajustes, web/ (tablero.html, mando.html, carátulas)
└── pruebas/         correr_pruebas.py + 6 pruebas sin hardware
```

- Tres hilos: simulación a 20 Hz (`hilo_simulacion.py`), motores (`paso_a_paso.py`),
  servidor HTTP (`ThreadingHTTPServer`, hilo principal).
- El servidor manda órdenes al simulador por una `queue.Queue` y lee una "foto"
  del estado que se reemplaza entera.
- API: `/`, `/mando`, `/qr`, `/qr.svg`, `/qr_wifi.svg`, `/cartel`,
  `/caratulas/<id>.svg`, `/api/catalogo`, `/api/estado`, `POST /api/mando/*`,
  `POST /api/modo/{0..3}`, `POST /api/accion/{pausa, velocidad, prueba_luces,
  piloto_reactivo, ciclar, activar_falla, quitar_falla}`. Toda orden exige sesión
  de profesor con el mando (403 / 409).
- La página no tiene datos propios: todo sale de `/api/catalogo`.

## 5. Formato en que tiene que estar cargado un programa en la Raspberry Pi 5

Esto es lo que hay que respetar para que el programa funcione en la Pi y arranque
solo. Basado en la documentación de Raspberry Pi y en cómo está instalado hoy.

### 5.1 Sistema operativo
- **Raspberry Pi OS (64 bits) con escritorio**, grabado con Raspberry Pi Imager.
  - Bookworm (Debian 12, Python 3.11) o **Trixie** (Debian 13, salida el
    2-oct-2025, Python 3.13). El código tiene que andar en **Python 3.9 a 3.13**.
  - Escritorio Wayland con el compositor **labwc**.
  - Red con **NetworkManager** (`nmcli`).
- Usuario normal (el creado en Imager, ej. `pi` o `mateo`); el programa **no corre
  como root**.

### 5.2 Dónde vive el programa
- En la carpeta del usuario: **`/home/USUARIO/H08_Pi5/`** (en el código siempre
  rutas relativas al archivo con `os.path.dirname(os.path.abspath(__file__))`,
  nunca rutas fijas).
- Lo que el programa guarda (clave, calibración, posición del motor, informes)
  va **dentro de `raspberry_pi5/`**, con escritura atómica (archivo temporal +
  `os.replace`). Esos archivos son privados del tablero.

### 5.3 Dependencias
- **Biblioteca estándar de Python** para todo lo posible (servidor HTTP, I2C con
  `os` + `fcntl` sobre `/dev/i2c-1`, QR propio).
- Lo único de afuera viene **de apt**: `python3-gpiozero`, `python3-lgpio`,
  `i2c-tools`, `chromium`, `rsync`, `unzip`.
- Desde Bookworm, `pip install` al sistema está **bloqueado** ("externally
  managed environment"). No se usa pip. Si algún día hiciera falta un paquete que
  no está en apt: entorno virtual `python3 -m venv --system-site-packages .venv`
  dentro de la carpeta, y el servicio apunta a `.venv/bin/python`.

### 5.4 GPIO e I2C en la Pi 5
- La Pi 5 tiene el chip **RP1**: **RPi.GPIO no funciona**. Se usa **gpiozero**,
  que en la Pi 5 usa **lgpio** solo. Los pines están en `/dev/gpiochip0`
  (imágenes viejas: `gpiochip4`). Un pin lo usa un solo proceso a la vez: por
  eso las pruebas exigen el servicio detenido.
- I2C: `sudo raspi-config nonint do_i2c 0`; en `/boot/firmware/config.txt`
  `dtparam=i2c_arm=on` y `dtparam=i2c_arm_baudrate=400000`. Aparece
  `/dev/i2c-1`. El usuario en los grupos `i2c`, `gpio`, `video`.
- Imports de `gpiozero`/`lgpio`/`fcntl`/`grp` siempre adentro de funciones o en
  `try`, para que todo corra simulado en Windows.

### 5.5 Arranque al encender: servicio systemd
Archivo `/etc/systemd/system/tablero-h08.service` (lo escribe `instalar.sh`):
```ini
[Unit]
Description=Tablero didáctico Sikorsky S-55 H-08
After=network.target

[Service]
Type=simple
User=USUARIO
SupplementaryGroups=i2c gpio video
WorkingDirectory=/home/USUARIO/H08_Pi5/raspberry_pi5
ExecStart=/usr/bin/python3 /home/USUARIO/H08_Pi5/raspberry_pi5/tablero_pi5.py
Restart=on-failure
RestartSec=5
TimeoutStopSec=20
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```
Reglas para un programa que corre como servicio:
- Rutas absolutas en `ExecStart`; nada interactivo (`input()`), nada gráfico.
- Atrapar **SIGTERM** y apagar en orden (luces, servos, motor a cero) dentro de
  `TimeoutStopSec`.
- La salida va al registro: `journalctl -u tablero-h08 -f`.
- Comandos: `sudo systemctl enable|start|stop|restart|status tablero-h08`.

### 5.6 Pantalla en modo kiosco
- Escritorio que entra solo: `sudo raspi-config nonint do_boot_behaviour B4`.
- Pantalla que no se apaga: `sudo raspi-config nonint do_blanking 1`.
- Al iniciar el escritorio se lanza `raspberry_pi5/kiosco.sh` desde
  `~/.config/labwc/autostart` (método del tutorial oficial de kiosco de Raspberry
  Pi) y desde `~/.config/autostart/tablero-kiosco.desktop` (XDG). `kiosco.sh` tiene
  candado (`flock`): nunca abre dos.
- `kiosco.sh` espera a que el servicio conteste, abre
  `chromium --kiosk http://localhost:8000/?kiosco=1` con perfil propio
  (`--user-data-dir`), `--noerrdialogs --disable-infobars --no-first-run
  --password-store=basic`, y lo reabre si se cierra. El binario puede llamarse
  `chromium` o `chromium-browser`.
- La página en `?kiosco=1` se recarga sola cuando el servicio se reinicia.

### 5.7 Wifi propia
- `punto_de_acceso.sh` crea con `nmcli` la conexión `tablero-ap`: red
  **Tablero-H08**, clave **sikorsky55**, IP **10.55.0.1**, `ipv4.method shared`.
- Hay que fijar el país del wifi (`raspi-config nonint do_wifi_country AR`) o la
  placa queda bloqueada. El servidor lee red/clave/IP de ese script para los QR.

### 5.8 Archivos y scripts
- Scripts `.sh` con **fin de línea LF**, `#!/usr/bin/env bash`, bit de ejecución;
  probar con `bash -n` y `shellcheck`.
- Python en UTF-8 con `# -*- coding: utf-8 -*-`; archivos de texto abiertos con
  `encoding="utf-8"`.
- `instalar.sh` se corre **una vez**, sin `sudo` delante (pide la clave él):
  paquetes, I2C, grupos, clave del profesor, servicio, kiosco, wifi. Después,
  **un reinicio**.
- `actualizar.sh ZIP`: respaldo completo, para el servicio, `rsync` excluyendo
  los archivos privados, arranca el servicio.
- El zip se arma **sólo** con `empaquetar.py` (corre pruebas, excluye privados,
  normaliza LF, escribe VERSION.txt).

### 5.9 Cómo se verifica en la Pi
```
python3 diagnostico_pi.py              # sistema, alimentación, I2C, GPIO, servicio,
                                       # pantalla, wifi, archivos (no mueve nada)
sudo systemctl stop tablero-h08
python3 prueba_luces_motor.py
python3 prueba_instrumento.py --todos
sudo systemctl start tablero-h08
python3 prueba_general.py              # detiene y arranca el servicio sola
```
Los informes quedan en `raspberry_pi5/informes/`. Cuando el usuario los traiga,
leerlos y separar hardware de código.

## 6. Cómo se trabaja (en la computadora, con Windows)

- `py pruebas/correr_pruebas.py` después de cada cambio. Todo tiene que dar
  "Todas bien.".
- `py raspberry_pi5/tablero_pi5.py --simulado --sin-clave` y abrir
  `http://localhost:8000/` (`?kiosco=1`, `/mando`).
- Las pruebas guiadas aceptan `--simulado --auto`.
- `py empaquetar.py` arma `dist/H08_Pi5.zip`.
- Lo que no se puede probar en Windows (I2C, GPIO, systemd, nmcli, Chromium
  kiosco) se deja escrito para probar en la Pi y se dice claramente.

## 7. Definición de "terminado" para cualquier cambio

1. Hace lo pedido y no cambia otra cosa.
2. Sigue el formato de la sección 5 (stdlib, rutas relativas, servicio, LF…).
3. Corre en Windows simulado y en la Pi (imports protegidos).
4. Tiene su prueba en `pruebas/` y `correr_pruebas.py` da "Todas bien.".
5. Si toca la página, se miró en `localhost:8000` (normal y `?kiosco=1`).
6. Si cambia algo que ve el usuario o el procedimiento, se actualizó `LEEME.md`
   (y este documento si cambia el formato o el hardware).
7. Textos para personas en castellano rioplatense (voseo).
8. Nunca toca `secreto_admin.json`, `calibracion_servos.json`,
   `posicion_motores.json`.

## 8. Decisiones abiertas y límites conocidos

- Altímetro: el servo no da más de una vuelta; arriba de 10.000 ft la aguja queda
  arriba.
- La resolución de los PCA9685 (≈0,44° de servo) se multiplica por los engranajes.
- La fuente de servos (LM2596, 3 A) limita cuántos se mueven a la vez: arranque
  escalonado de a 3 (`ARRANQUE`).
- Luz fantasma: arreglo de hardware pendiente (1N4148).
- J1 espejado: Dupont por función, pendiente de confirmar por el usuario.
