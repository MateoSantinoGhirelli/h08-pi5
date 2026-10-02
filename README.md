# Tablero H-08

Tablero didáctico de un **Sikorsky S-55 / H-19A** para la EEST N° 7 (Taller Regional
Quilmes). Un simulador de vuelo mueve 20 servos, 6 luces de alerta y el motor paso a
paso de la brújula, y sirve una página web con el tablero en vivo.

El programa corre en una **Raspberry Pi 5** (Raspberry Pi OS con escritorio) y se
desarrolla en Windows en modo simulado. Usa sólo la **biblioteca estándar de Python**:
no hace falta internet, ni pip, ni instalar nada fuera de los paquetes del sistema.

## Qué hace, encendida la Raspberry

1. **Mueve el tablero.** Los 20 servos, las 6 luces y la brújula, cada uno con la
   calibración y la mecánica de su instrumento.
2. **Muestra la pantalla.** El tablero a pantalla completa, con las mismas carátulas
   que están pegadas en los instrumentos y los QR para entrar desde el celular.
3. **Levanta su red wifi.** La red `Tablero-H08`: cualquier celular entra a
   `http://10.55.0.1:8000/` y ve el tablero en vivo.

## Probarlo en una computadora

Desde la carpeta del proyecto, con Python 3.9 o posterior:

```
py -m h08 --simulado --sin-clave        # el tablero sin hardware
```

y abrir <http://localhost:8000/> (pantalla de la Pi: `/?kiosco=1`, mando: `/mando`).

```
py -m pruebas                           # todas las pruebas (sin hardware)
py empaquetar.py                        # arma dist/H08_Pi5.zip para la Pi
```

## Instalarlo en la Raspberry Pi 5

Llevar `dist/H08_Pi5.zip` en un pendrive, descomprimirlo en `~/H08_Pi5` y, desde ahí:

```
bash deploy/instalar.sh                 # una sola vez; después hay que reiniciar
python3 -m h08 diagnostico              # revisa conexiones e instalación
```

El paso a paso completo, el cableado y cómo actualizar están en **[LEEME.md](LEEME.md)**.

## Cómo está armado

Todo el código vive en el paquete `h08/` y se corre con `python3 -m h08`. Los datos de
cada tablero (clave, calibración, posición del motor) van aparte, en `datos/`, para que
una actualización pueda reemplazar `h08/` sin miedo.

- `h08/config/` — el tablero en datos (canales, escalas, calibración, pines).
- `h08/simulacion/` — el modelo de vuelo, las fallas y los escenarios.
- `h08/hardware/` — los servos y luces (PCA9685) y la brújula (paso a paso).
- `h08/web/` — el servidor, la página y los QR.
- `h08/herramientas/` — diagnóstico, pruebas guiadas y ajustes de la Pi.
- `deploy/` — los scripts de instalación y arranque. `pruebas/` — las pruebas.

## Documentación

- **[LEEME.md](LEEME.md)** — guía completa para instalar y usar el tablero.
- **[CONTEXTO_PROYECTO.md](CONTEXTO_PROYECTO.md)** — requisitos, hardware, canales y el
  formato en que tiene que estar instalado en la Pi.
- **[docs/](docs/)** — las explicaciones largas: modelo de vuelo, hardware, acceso,
  calibración y geometría del tablero.
- **[CHANGELOG.md](CHANGELOG.md)** — qué cambió en cada versión.
