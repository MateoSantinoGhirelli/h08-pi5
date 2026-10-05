# Tablero H-08 · Programa de la Raspberry Pi 5

Sikorsky S-55 / H-19A · EEST N° 7 · Taller Regional Quilmes

Esta carpeta tiene **todo lo que tiene que estar en la Raspberry Pi 5** y nada más. Se instala una vez. Desde ahí, cada vez que se enciende la Raspberry:

1. **Arranca el servicio del tablero.** Mueve los 20 servos, las 6 luces de alerta y el motor paso a paso de la brújula, cada uno con la calibración y la mecánica de su instrumento. También sirve la página web.
2. **La pantalla conectada a la Raspberry muestra el tablero.** Se ve a pantalla completa, con las mismas carátulas que están pegadas en los instrumentos. Abajo a la derecha aparecen los dos QR para entrar desde el celular.
3. **La Raspberry levanta su propia red wifi.** La red se llama **Tablero-H08** y la clave es **sikorsky55**. Cualquier celular o tablet conectado entra a `http://10.55.0.1:8000/` y ve el tablero en vivo.

No hace falta internet, ni pip, ni instalar nada fuera de los paquetes del sistema.

---

## Qué hace falta

| | |
|---|---|
| Raspberry Pi 5 | con su fuente oficial de 27 W (5,1 V 5 A) |
| Sistema | **Raspberry Pi OS con escritorio**, 64 bits, Bookworm o posterior |
| Pantalla | HDMI (la de la Raspberry). Es opcional: sin pantalla funciona igual |
| Placa madre | armada y cableada. **Importante: J1 va con Dupont, ver abajo** |
| Fuente de servos | la del tablero (LM2596, 5 V). **Nunca** los servos desde la Pi |

---

## Un solo comando

Todo se hace con `python3 -m h08`, **desde la carpeta del programa** (`cd ~/H08_Pi5`):

| Comando | Para qué |
|---|---|
| `python3 -m h08` | el tablero (es lo que arranca el servicio solo al encender) |
| `python3 -m h08 diagnostico` | revisa conexiones e instalación, no mueve nada |
| `python3 -m h08 prueba-general` | el tablero entero, de punta a punta |
| `python3 -m h08 luces-motor` | las luces de alerta y el motor de la brújula |
| `python3 -m h08 instrumento` | instrumento por instrumento |
| `python3 -m h08 canal` | un canal suelto, para ajustar una aguja |
| `python3 -m h08 motor` | el motor suelto: sentido, bobinas y cero |
| `python3 -m h08 calibrar` | los extremos reales de un servo |

`python3 -m h08 --help` muestra la lista, y cada uno tiene su propia ayuda: `python3 -m h08 canal --help`.

---

## Instalación (una sola vez)

1. Copiar la carpeta `H08_Pi5` a la Raspberry, por ejemplo con un pendrive, y dejarla en la carpeta del usuario (`/home/USUARIO/H08_Pi5`).
2. Abrir una terminal y correr:

   ```
   cd ~/H08_Pi5
   bash deploy/instalar.sh
   sudo reboot
   ```

   `instalar.sh` se corre **sin** `sudo` adelante (la clave la pide solo). Hace esto:

   - limpia lo que haya dejado una versión anterior (el servicio y el arranque del kiosco viejos);
   - instala `gpiozero`, `lgpio`, `i2c-tools`, Chromium, `rsync` y `unzip`;
   - habilita el I2C a 400 kHz;
   - suma el usuario a los grupos `i2c`, `gpio` y `video`;
   - genera la clave del profesor;
   - instala el servicio `tablero-h08`, que arranca solo;
   - configura la pantalla: el escritorio entra sin contraseña, la pantalla no se apaga y el tablero se abre en modo kiosco;
   - deja preparada la red wifi propia para el próximo encendido.

   Opciones: `--sin-kiosco` (sin pantalla) y `--sin-wifi` (usar la red de la escuela).

3. Después del reinicio, comprobar que todo quedó bien:

   ```
   cd ~/H08_Pi5
   python3 -m h08 diagnostico
   ```

---

## Pasar de la versión vieja a la nueva

La versión vieja arrancaba desde `raspberry_pi5/tablero_pi5.py`; la nueva, con `python3 -m h08`. Para pasar de una a la otra se reinstala limpio (`actualizar.sh` no sirve para este paso):

```
sudo systemctl stop tablero-h08
mv ~/H08_Pi5 ~/H08_Pi5_viejo          # o borrarla, si no hay nada que guardar
# copiar la carpeta H08_Pi5 nueva a /home/USUARIO/H08_Pi5
cd ~/H08_Pi5
bash deploy/instalar.sh
sudo reboot
```

Después del reinicio: `cd ~/H08_Pi5 && python3 -m h08 diagnostico`.

- `instalar.sh` borra por su cuenta el arranque del kiosco viejo (la línea de `kiosco.sh` en `~/.config/labwc/autostart` y `~/.config/autostart/tablero-kiosco.desktop`) y vuelve a escribir el servicio `tablero-h08` con el comando nuevo.
- Se genera una **clave del profesor nueva**: hay que volver a imprimir la hoja del QR (`python3 -m h08 --qr-admin --hoja datos/admin.html`).
- Si había servos calibrados o la brújula tenía su cero ajustado, antes de correr `instalar.sh` se pueden copiar `calibracion_servos.json` y `posicion_motores.json` de `~/H08_Pi5_viejo/raspberry_pi5/` a `~/H08_Pi5/datos/` (crear la carpeta si no está). Si no, los servos usan los valores nominales y la brújula arranca en 0°.
- Si en vez de reinstalar limpio la carpeta vieja quedó debajo de la nueva, el tablero pasa solo a `datos/` lo que encuentre en `raspberry_pi5/` la primera vez que arranca, sin pisar nada que ya esté en `datos/`.

---

## Cableado de la Raspberry a la placa madre

```
python3 -m h08 diagnostico --cableado
```

| Función | GPIO | Pata de la Raspberry |
|---|---|---|
| 3,3 V (lógica de los PCA9685) | – | 1 |
| SDA (I2C) | GPIO2 | 3 |
| SCL (I2C) | GPIO3 | 5 |
| GND | – | 6, 9, 14, 20, 25, 30, 34, 39 |
| Motor IN1 | GPIO12 | 32 |
| Motor IN2 | GPIO16 | 36 |
| Motor IN3 | GPIO20 | 38 |
| Motor IN4 | GPIO21 | 40 |

> **La placa salió espejada.** En J1 las columnas par e impar quedaron cambiadas, así que **el cable plano no sirve**. Hay que cablear pata por pata con Dupont hembra-hembra y seguir la tabla por **función**: SDA con SDA, IN1 con IN1, y así con cada una, mirando la serigrafía de la placa que tienen en la mano. El programa no cambia, porque las funciones son las mismas.

Los dos PCA9685 van así:

- **PCA0** en 0x40, sin puentes.
- **PCA1** en 0x41, con el puente A0 soldado.

El V+ de los dos sale de la fuente de servos. El GND de esa fuente va unido al de la Pi.

---

## Qué mueve cada canal

| Canal | Instrumento | Cómo va la aguja |
|---|---|---|
| PCA0:0 | Combustible, tanque delantero | barre 120°, aguja directa en el servo |
| PCA0:1 | Temperatura de aceite | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:2 | Presión de aceite | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:3 | Presión de combustible | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:4 | Temperatura de aire del carburador | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:5 | Temperatura de culata | barre 270°, engranajes 36/24 (servo al revés) |
| PCA0:6 | Velocímetro | barre 300°, engranajes 40/24 (servo al revés) |
| PCA0:7 | Tacómetro (aguja del motor) | barre 300°, engranajes 40/24 (servo al revés) |
| PCA0:9 | Altímetro (miles de pies) | barre 360°, engranajes 48/24 (servo al revés) |
| PCA0:10 | Variómetro | barre 300°, engranajes 40/24 (servo al revés) |
| PCA0:11 | Viraje (aguja) | barre 60°, aguja directa |
| PCA0:13 | Horizonte, cabeceo | yugo escocés |
| PCA0:14 | Horizonte, alabeo | plato 70/50 |
| PCA0:15 | AN/ARN-14 (desvío de curso) | barre 40°, aguja directa |
| PCA1:0 | Presión de admisión | barre 270°, engranajes 36/24 (servo al revés) |
| PCA1:1 | Temperatura de transmisión | barre 270°, engranajes 36/24 (servo al revés) |
| PCA1:2 | Presión de transmisión | barre 270°, engranajes 36/24 (servo al revés) |
| PCA1:3 | Amperímetro | barre 120°, aguja directa |
| PCA1:4 | Voltímetro | barre 120°, aguja directa |
| PCA1:5 | Combustible, tanque trasero | barre 120°, aguja directa |
| GPIO 12-16-20-21 | Brújula | paso a paso 28BYJ-48, giro continuo |
| PCA1:8 | Luz FUEL FWD (ámbar) | combustible delantero bajo |
| PCA1:9 | Luz FUEL AFT (ámbar) | combustible trasero bajo |
| PCA1:10 | Luz XMSN PRESS (roja) | baja presión de transmisión con el rotor girando |
| PCA1:11 | Luz GENERATOR (roja) | batería conectada y generador fuera de línea |
| PCA1:12 | Luz LOW ROTOR (roja) | rotor por debajo de su mínimo |
| PCA1:13 | Luz IGNITION (verde) | magnetos activos |

Libres: PCA0:8, PCA0:12, PCA1:6, PCA1:7, PCA1:14, PCA1:15 y el lugar del motor 0 (GPIO 6-13-19-26).

Tres agujas existen **sólo en la página**, porque en el tablero no tienen actuador: la del rotor en el tacómetro, la bola de ladeo y las centenas del altímetro.

---

## Puesta en marcha: las pruebas, en este orden

Todas se corren desde `~/H08_Pi5`. Las pruebas guiadas preguntan «¿se movió?, ¿se encendió?» y guardan un informe con fecha en `datos/informes/`. Casi todas necesitan el servicio detenido, porque manejan las placas directo:

```
sudo systemctl stop tablero-h08        # antes
sudo systemctl start tablero-h08       # después
```

| # | Prueba | Para qué |
|---|---|---|
| 1 | `python3 -m h08 diagnostico` | **Diagnóstico de conexiones.** Revisa sistema, alimentación (baja tensión y 5 V medidos), bus I2C (qué hay conectado y si cada PCA9685 quedó configurado a 50 Hz), GPIO del motor, servicio, pantalla, wifi y archivos. No mueve nada y puede correr con el servicio en marcha. Para cada falla dice el comando que la arregla. |
| 2 | `python3 -m h08 luces-motor` | **Luces y motor.** Prueba de lámparas, cada luz de a una (así se ven dos cables cruzados), la luz fantasma, las bobinas A-B-C-D de la plaquita, N-E-S-O, el camino corto (de 350° a 10°), tres vueltas de ida y vuelta sin perder pasos, y que las bobinas se suelten en reposo. |
| 3 | `python3 -m h08 canal ID --valor V` | **Calzar la aguja** de cada instrumento sobre su marca (por ejemplo `python3 -m h08 canal AIRSPEED --valor 60`). |
| 4 | `python3 -m h08 calibrar PCA0 6 --asistente` | Sólo si un servo no llega a un extremo o zumba en el tope. |
| 5 | `python3 -m h08 instrumento --todos` | **Instrumento por instrumento.** Lleva cada aguja por los números grandes de **su** carátula, con la misma cuenta que usa el tablero en marcha, y pregunta si marca bien. También pasa por N-E-S-O en la brújula y por cada luz. Si algo falla, dice con qué se arregla. Para uno solo: `python3 -m h08 instrumento VSI`. |
| 6 | `python3 -m h08 prueba-general` | **Prueba general del tablero, de punta a punta.** Tarda unos 15 minutos; detiene y arranca el servicio sola. Tiene tres partes: diagnóstico, hardware solo y tablero entero. En el hardware solo las 20 agujas barren **juntas** mientras se mide la alimentación, y ésa es la prueba de la fuente de servos. En el tablero entero se toma el mando con la clave del profesor, se prueban las luces desde el mando, se activan dos fallas (aceite y generador) y se comprueba la pantalla y un celular. |

Todas aceptan `--simulado --auto` para ver cómo son en una computadora, sin hardware.

Las pruebas automáticas del programa (no necesitan hardware) se corren con `python3 -m pruebas`, desde `~/H08_Pi5`. Terminan con «Todas bien.»; `python3 -m pruebas --rapido` saltea las que tardan.

---

## Uso de todos los días

- **Encender la Raspberry.** No hay que hacer nada más.
- **QR del profesor** (para operar el tablero desde el celular: modos, fallas, prueba de luces):

  ```
  cd ~/H08_Pi5
  python3 -m h08 --qr-admin --hoja datos/admin.html
  ```

  La hoja va en `datos/`: lo que quede suelto en la carpeta del programa lo borra la próxima actualización. Esa hoja no se pega en la pared. Si se filtra, se genera otra con `python3 -m h08 --renovar-clave`.
- **Cartel para el público**, con el QR de la red wifi y el de la página: `http://10.55.0.1:8000/cartel`, para imprimir.
- **Usar el escritorio** de la Raspberry: `bash deploy/kiosco.sh parar`. Para volver al tablero: `bash deploy/kiosco.sh`.
- **Volver a la red de la escuela:** `sudo bash deploy/punto_de_acceso.sh apagar`. Para volver a la propia: `sudo bash deploy/punto_de_acceso.sh permanente`.

---

## Actualizar a una versión nueva

Si trabajás el código en la computadora, el zip se arma ahí con `py empaquetar.py`. Primero corre las pruebas; si pasan, deja `dist/H08_Pi5.zip`. Eso se lleva a la Pi en un pendrive y se instala con el comando de abajo.

```
cd ~/H08_Pi5
bash deploy/actualizar.sh /media/USUARIO/PENDRIVE/H08_Pi5.zip
```

Guarda antes un respaldo completo (`~/H08_respaldo_FECHA`) y deja la carpeta igual a la versión nueva: lo que la versión nueva ya no trae, se borra. No toca la carpeta `datos/`, que es de **este** tablero:

- `secreto_admin.json`, la clave del profesor;
- `calibracion_servos.json`, lo medido en cada servo;
- `posicion_motores.json`, dónde quedó la aguja de la brújula;
- `informes/`, lo que guardaron las pruebas guiadas.

Después reinicia el servicio. **La pantalla de la Raspberry se recarga sola con la versión nueva.** Los celulares la ven al recargar la página.

Si en la Raspberry todavía está la versión vieja (la de `raspberry_pi5/tablero_pi5.py`), `actualizar.sh` avisa y no hace nada: ver «Pasar de la versión vieja a la nueva».

---

## Cómo funcionan las luces

- En la placa, el ánodo de cada LED va a +5 V y el cátodo va, por su resistencia de 220 Ω, a una salida del PCA9685. **La luz enciende con la salida en BAJO.** El programa ya lo tiene en cuenta (`LUCES_ACTIVAS_EN_BAJO` en `h08/config/hardware.py`).
- **Al dar energía, las seis luces se encienden** hasta que arranca el servicio, unos 20 a 30 segundos. Es normal y sirve de prueba de lámparas del encendido: la que no se enciende en ese momento tiene el LED o el cable cortado.
- Cada luz se enciende por **su** condición del modelo (ver la tabla de canales). Si la barra eléctrica cae por debajo de 20 V, se apagan todas, como en el avión.
- La **prueba de lámparas del mando** enciende las seis en el tablero **y** en la página, que ahora muestra lo que tienen las luces de verdad.
- **Luz fantasma.** Con la salida "apagada" (en alto, 3,3 V), al LED le quedan 1,7 V. Un LED rojo o ámbar puede verse apenas encendido en la oscuridad, y el programa no lo puede evitar. Se arregla en la placa con un diodo 1N4148 en serie con cada LED. `python3 -m h08 luces-motor` pregunta por esto.

---

## Si algo no funciona

Todos los comandos, desde `~/H08_Pi5`.

| Síntoma | Qué hacer |
|---|---|
| La pantalla queda en el escritorio | `bash deploy/kiosco.sh`. Si al reiniciar sigue igual: `python3 -m h08 diagnostico`, punto 6 |
| La página dice «sin conexión» | `sudo systemctl status tablero-h08`, `journalctl -u tablero-h08 -n 50` |
| Algo raro y no se sabe qué | `journalctl -u tablero-h08 -p warning`: muestra sólo los avisos y errores del tablero (placa que no responde o que se reinició, errores del bus I2C, errores del programa) |
| `No module named h08` | el comando se corrió fuera de la carpeta: `cd ~/H08_Pi5` y repetir |
| Ninguna aguja se mueve | `python3 -m h08 diagnostico`: el punto 3 dice si responden los PCA9685 |
| Una sola aguja no se mueve | `python3 -m h08 instrumento ESA`, después el cable de su canal |
| La aguja marca corrido | `python3 -m h08 canal ESA --valor V` y ajustar la aguja |
| Zumba contra un tope | `python3 -m h08 calibrar PCA0 N --asistente` |
| Las placas se reinician cuando se mueven muchas agujas | Es la fuente de servos: el LM2596 da 3 A como máximo. `python3 -m h08 prueba-general` (A3) lo muestra |
| La brújula gira al revés | `sentido` en `MOTORES` (`h08/config/hardware.py`) |
| La brújula tiembla y no gira | `python3 -m h08 motor 1 --bobinas`: las bobinas tienen que ir en orden A-B-C-D |
| El celular no ve la red | `sudo bash deploy/punto_de_acceso.sh estado` (y el país del wifi: lo pone solo) |

---

## Qué hay en la carpeta

```
H08_Pi5/
├── LEEME.md                  esto
├── VERSION.txt               qué versión es
├── CONTEXTO_PROYECTO.md      el proyecto completo y el formato de instalación en la Pi 5
├── empaquetar.py             arma dist/H08_Pi5.zip para llevar a la Pi
├── .gitignore .gitattributes para git: lo privado afuera y fin de línea LF
├── docs/                     explicaciones del modelo, la mecánica y el hardware
├── h08/                      el programa: python3 -m h08
│   ├── __main__.py           el tablero y los subcomandos
│   ├── rutas.py              dónde está cada archivo
│   ├── config/               el tablero en datos: canales, escalas, calibraciones,
│   │                         placas, pines y la geometría de la página
│   ├── simulacion/           el modelo de vuelo, las fallas y los escenarios
│   ├── hardware/             las placas PCA9685 y el motor paso a paso
│   ├── web/                  el servidor, la clave del profesor, los QR y la página
│   └── herramientas/         diagnóstico, pruebas guiadas y ajustes
├── deploy/
│   ├── instalar.sh           instalación, una vez
│   ├── actualizar.sh         pasar a una versión nueva
│   ├── kiosco.sh             el tablero en la pantalla de la Raspberry
│   └── punto_de_acceso.sh    la red wifi propia
├── pruebas/                  pruebas automáticas, sin hardware: python3 -m pruebas
└── datos/                    los datos de ESTE tablero (clave, calibración, posición
                              del motor, informes); no viaja en el zip ni se borra
                              al actualizar
```
