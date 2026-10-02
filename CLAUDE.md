# Tablero H-08 · programa de la Raspberry Pi 5

Tablero didáctico de un Sikorsky S-55 / H-19A (EEST N° 7, Taller Regional Quilmes).
Un simulador de vuelo mueve 20 servos, 6 luces y el motor paso a paso de la brújula,
y sirve una página web (pantalla de la Pi en modo kiosco + celulares por wifi).

- Se DESARROLLA en Windows y se prueba en modo simulado.
- Se INSTALA en una Raspberry Pi 5 con Raspberry Pi OS con escritorio (Bookworm o
  posterior; el código anda en Python 3.9 a 3.13) llevando `dist/H08_Pi5.zip` en un pendrive.
- El documento completo del proyecto (requisitos, hardware, canales, y el FORMATO en
  que tiene que estar instalado un programa en la Pi 5) es `CONTEXTO_PROYECTO.md`.
  Leerlo antes de cualquier cambio grande o de tocar instalación/arranque.
- La guía para humanos está en `LEEME.md` (leerla cuando haga falta, no se carga sola).

## Comandos (Windows: `py`; en la Pi: `python3`)

- Todo se corre desde la raíz del proyecto (`-m h08` y `-m pruebas` necesitan ver esas carpetas).
- Todas las pruebas: `py -m pruebas` (un par de minutos, sin hardware; termina con
  «Todas bien.»). Sin las lentas: `py -m pruebas --rapido` (unos 20 s). También anda
  el estándar `py -m unittest -v`. Una sola: `py -m unittest pruebas.test_acceso -v`.
- Ver el tablero: `py -m h08 --simulado --sin-clave`
  y abrir http://localhost:8000/ (pantalla de la Pi: `/?kiosco=1`, mando: `/mando`)
- Herramientas: `py -m h08 --help` lista los subcomandos (`diagnostico`,
  `prueba-general`, `luces-motor`, `instrumento`, `canal`, `motor`, `calibrar`).
- Pruebas guiadas sin hardware: `py -m h08 prueba-general --simulado --auto`
  (igual `py -m h08 instrumento --todos --simulado --auto`, `py -m h08 luces-motor --simulado --auto`)
- Armar el zip para la Pi: `py empaquetar.py` (corre las pruebas primero)

## Reglas

- **Sólo biblioteca estándar de Python** en `h08/` y `pruebas/`.
  Nada de pip ni paquetes nuevos. En la Pi sólo hay gpiozero y lgpio del sistema,
  importados adentro de funciones (en Windows no existen).
- Tiene que seguir andando en Windows en modo simulado: nada de `fcntl`, `grp`,
  `os.geteuid` ni rutas fijas de Linux fuera de un `try` o de una función que sólo
  corre en la Pi.
- Imports absolutos (`from h08.hardware import pca9685`); nada de `sys.path.insert`
  dentro de `h08/`. Toda ruta de archivo sale de `h08/rutas.py`.
- Mensajes del servicio y del núcleo: `log = logging.getLogger(__name__)` y
  `log.info/warning/exception` (lo configura `h08/registro.py`; en el journal se
  filtra con `journalctl -u tablero-h08 -p warning`). `print` sólo en las herramientas
  que le hablan a una persona en la terminal y en `--qr-admin`.
- **Nunca** crear, leer para copiar, ni meter en un zip o en git:
  `datos/secreto_admin.json`, `calibracion_servos.json`, `posicion_motores.json` (en
  instalaciones viejas, los mismos en `raspberry_pi5/`). Para probar o levantar el
  tablero en la PC, siempre con `H08_DATOS` en una carpeta temporal
  (`pruebas/__init__.py` ya lo hace): así no hay mudanza ni se crea una clave.
- Los datos del tablero (canales, escalas, calibraciones, barridos, pines, direcciones)
  viven SÓLO en `h08/config/`. No repetirlos en otro archivo.
- Si una aguja física no cae en su marca, NO se toca la tabla `cal`: las carátulas
  impresas están dibujadas con esa tabla. Se calza la aguja
  (`python3 -m h08 canal ID --valor V`) o se calibra el servo
  (`python3 -m h08 calibrar PCA0 N --asistente`). La tabla `cal` sólo cambia si se
  reimprimen las carátulas.
- Los `.sh` corren en la Pi con bash: fin de línea LF, probarlos con `bash -n`.
- Todo texto que ve una persona (mensajes, página, comentarios) va en castellano
  rioplatense (voseo), claro y sin jerga innecesaria.
- Después de cada cambio: correr `py -m pruebas`. Si se agrega algo, agregar su prueba
  en el `pruebas/test_*.py` de su tema (`unittest`): una clase `Prueba` de
  `pruebas/comun.py`, con `self.comprobar("qué se comprueba", condición)`, y `@lenta`
  si tarda más de unos segundos.
- Cambios chicos y de a uno. Antes de tocar varios archivos, proponer un plan.
- No se puede probar acá: I2C, GPIO, systemd, NetworkManager, Chromium kiosco.
  Eso se prueba en la Pi con `python3 -m h08 diagnostico` y las pruebas guiadas; cuando el
  usuario traiga un informe de `datos/informes/`, leerlo y corregir desde ahí.

## Git y GitHub (lo decide el usuario)

- A git y a GitHub sube **sólo lo que funciona, está probado y el usuario aprobó**.
- **Nunca hagas `git commit` ni `git push` por tu cuenta**, ni "para guardar avances".
  Mientras se trabaja, los cambios quedan sin confirmar (y se deshacen con el
  rewind o con `git restore .` / `git clean -fd` volviendo al último commit).
- Cuando el usuario escriba **APROBADO** (con una descripción): corré las pruebas, mostrá
  `git status`, proponé UN mensaje de commit (imperativo, corto, en castellano) y recién
  ahí `git add -A`, `git commit` y `git push`. Los dos piden permiso
  (`.claude/settings.json`): esperá que el usuario los acepte.
- Si las pruebas no pasan, no se confirma nada aunque el usuario haya escrito APROBADO:
  avisale.

## Cómo está armado

- Un paquete, `h08/`, que se corre con `python3 -m h08` (`h08/__main__.py`: el
  tablero y los subcomandos). `deploy/` tiene los `.sh` de la Pi; `pruebas/`, las
  pruebas automáticas; `datos/` tiene lo que escribe cada tablero (clave,
  calibración, posición del motor, `informes/`), fuera de git y del zip. Si quedaron
  datos en `raspberry_pi5/` (versión vieja), el tablero los pasa a `datos/` al
  arrancar sin pisar nada (`rutas.migrar_datos_viejos`).
- `h08/config/`: el tablero en datos, un archivo por tema. `__init__.py` reexporta
  todo (el resto importa siempre `from h08.config import ...`):
  - `aeronave.py`: `AERONAVE`, `LIM` (límites físicos del H-19A);
  - `tablero.py`: `SERVO`/`MOTOR`/`LED`, `TABLERO` (30 entradas con su tabla `cal`
    y su canal), `TABLERO_POR_ID`;
  - `mecanica.py`: `BARRIDO`, `CENTRO_ESCALA`, `ENGRANAJES`, `HORIZONTE`,
    `reduccion()`, `invertido()`, `factor_servo()`;
  - `hardware.py`: `LAZO`, `ARRANQUE`, `PLACAS` (PCA0 0x40, PCA1 0x41), `SERVO_CFG`
    (500–2500 µs), `LUCES_ACTIVAS_EN_BAJO`, `MOTOR_CFG`, `MOTORES`;
  - `panel.py`: geometría y textos de la página (`PANEL`, `ANUNCIADOR`, ...).
- `h08/rutas.py`: dónde está cada archivo (datos, página, `VERSION.txt`, scripts).
- Flujo cada 50 ms: `simulacion/modelo` + `fallas` + `escenarios` → `simulacion/simulador`
  → `simulacion/senales` (real vs indicado) → `hardware/mapa` → `hardware/pca9685`
  (servos y luces por I2C) y `hardware/paso_a_paso` (brújula por GPIO 12-16-20-21).
- `h08/__main__.py` arranca todo; `simulacion/hilo.py` (20 Hz) y `web/servidor.py`
  (puerto 8000, API, QR, carátulas; órdenes sólo con la clave del profesor, ver
  `web/acceso.py`).
- Herramientas de la Pi (diagnóstico, pruebas guiadas, ajustes) en `h08/herramientas/`.
- Página: `h08/web/static/tablero.html` (sin datos propios: todo sale de
  `/api/catalogo`), `mando.html`, carátulas en `h08/web/static/caratulas/` (copias de
  las impresas; no editarlas a mano).

## La cuenta que no se puede romper

valor → `interpolar_tabla(valor, cal)` (tabla en 0..180) → × `factor_servo(id)` →
ángulo del servo → pulso con la calibración del servo.

- Barrido > 180° (270, 300, 360): el servo recorre 0..180 y un par de engranajes
  multiplica (36/24, 40/24, 48/24). El par invierte el giro: `invertido(id)` da
  vuelta los pulsos (0° = 2500 µs).
- Barrido ≤ 180°: aguja directa, el servo usa sólo `barrido` grados.
- La carátula impresa y la página ponen la marca en
  `ang_dibujo = centro + B/2 − a·B/180` (B ≥ 360: `centro − a`). Las carátulas (el
  PDF impreso y sus SVG en `h08/web/static/caratulas/`) se hicieron aparte y **no hay
  programa en el proyecto que las regenere**: no cambiar un barrido ni una tabla `cal`
  sin avisarle antes al usuario (ver `docs/mecanica.md`).

## Hardware (para no inventar)

- Luces: ánodo a +5 V, cátodo por 220 Ω al PCA1 canales 8–13 → encienden con la
  salida en BAJO. Con salida en alto (3,3 V) puede quedar una luz fantasma tenue:
  se arregla en la placa con un 1N4148 en serie, no en el programa.
- Placa madre ESPEJADA: J1 se cablea con Dupont pata por pata por función; el
  código no cambia. El KiCad no se toca.
- Fuente de servos LM2596 (3 A máx.): por eso el arranque escalonado de a 3.
