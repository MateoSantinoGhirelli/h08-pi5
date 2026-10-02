# Tablero H-08 · Estructura profesional y estilo de código

_Guía para Claude Code y para quien mantenga el programa de la Raspberry Pi 5 · octubre de 2026_

## 0. Cómo usar este documento

Este documento es la **fuente para reorganizar y pulir el código** del proyecto H08_Pi5. Dice cómo tiene que quedar la estructura de carpetas y cómo se escriben el código y los comentarios. No cambia **qué** hace el programa: eso lo define `CONTEXTO_PROYECTO.md`, que manda sobre este documento en requisitos, hardware y formato de instalación en la Pi 5.

- Prioridad si dos documentos chocan: `CONTEXTO_PROYECTO.md` (qué hace y cómo se instala) > este documento (estructura y estilo) > `CLAUDE.md` (reglas cortas).
- Todo cambio de estructura se hace **por fases** (sección 3), con las pruebas en verde al final de cada una.
- A git y a GitHub sube **sólo lo que funciona, está probado y el usuario aprobó** (sección 3.1). Claude Code nunca confirma ni sube nada por su cuenta.
- Ninguna fase cambia el comportamiento del tablero. Si un cambio de estructura obliga a cambiar comportamiento, se para y se consulta.
- Para Claude Code: este archivo existe también como `docs/GUIA_ESTRUCTURA_Y_ESTILO.md`; leé esa versión (el .docx es para personas).

## 1. Diagnóstico del proyecto actual

El programa funciona y está bien probado: 6 baterías de pruebas automáticas, pruebas guiadas en la Pi, separación clara entre modelo, mapa y hardware, y sólo biblioteca estándar. Lo que lo aleja de un proyecto profesional es la forma, no el fondo.

| Tema | Situación hoy |
|---|---|
| Tamaño | ≈ 11.500 líneas de Python en 33 archivos (nucleo/, raspberry_pi5/, pruebas/). |
| Imports | Cada script agrega carpetas a mano con `sys.path.insert(...)`. No hay un paquete importable: funciona, pero es frágil y no es lo habitual. |
| Carpetas | `raspberry_pi5/` mezcla el programa principal, los scripts de instalación, las pruebas guiadas, las herramientas de ajuste, la web y los archivos de datos privados. |
| Configuración | `configuracion.py` tiene 1.118 líneas: canales, mecánica, horizonte, placas, motor, arranque y además toda la geometría del panel web. |
| Pruebas | Scripts propios con funciones `cierto()` / `igual()`. Andan bien, pero no usan `unittest`, que viene con Python y es lo estándar. |
| Salida | Se usa `print()` también en el servicio. Lo profesional es `logging`, que systemd/journald ya recoge. |
| Versión | `VERSION.txt` lo genera `empaquetar.py`; no hay `__version__` ni `CHANGELOG`. |
| Comentarios | Muy buenos en contenido, pero con marcas de texto generado: ≈200 líneas de separadores `# =====`, el mismo encabezado «Proyecto H-08 · EEST N° 7» en 18 archivos, docstrings de módulo de 20–40 líneas con títulos en MAYÚSCULAS («POR QUÉ», «LO IMPORTANTE»), y muletillas repetidas («Por eso…», «No es X: es Y», «Así…»). |

## 2. Estructura objetivo

### 2.1 Qué condiciona la estructura

- En la Pi el programa **no se instala con pip** (Raspberry Pi OS bloquea pip al sistema) y corre desde su carpeta como servicio de systemd.
- Sólo biblioteca estándar, Python 3.9 a 3.13, y tiene que correr simulado en Windows.
- La guía de empaquetado de Python distingue la «flat layout» (el paquete en la raíz del proyecto) de la «src layout» (el paquete dentro de `src/`). La src layout evita usar sin querer la copia en desarrollo, pero **exige instalar el paquete** para usarlo. Como acá no se instala, corresponde **flat layout con un paquete propio en la raíz**, ejecutado con `python3 -m h08`.

### 2.2 Árbol propuesto

```
H08_Pi5/
├── README.md                 qué es, instalación, uso (hoy LEEME.md)
├── CHANGELOG.md              qué cambió en cada versión
├── CLAUDE.md                 reglas cortas para Claude Code
├── pyproject.toml            nombre, versión, Python mínimo y config. de herramientas
├── empaquetar.py             arma dist/H08_Pi5.zip
├── .gitignore  .gitattributes
├── docs/
│   ├── CONTEXTO_PROYECTO.md  requisitos, hardware, formato en la Pi 5
│   ├── GUIA_ESTRUCTURA_Y_ESTILO.md   este documento
│   └── hardware.md           cableado, canales, luces (sale del README)
├── h08/                      EL PROGRAMA (paquete importable)
│   ├── __init__.py           __version__
│   ├── __main__.py           python3 -m h08  →  arranca el tablero
│   ├── rutas.py              dónde están web/, datos/ e informes/
│   ├── config/
│   │   ├── tablero.py        TABLERO: canales, escalas, calibración
│   │   ├── mecanica.py       BARRIDO, ENGRANAJES, HORIZONTE, CENTRO_ESCALA
│   │   ├── hardware.py       PLACAS, SERVO_CFG, LUCES_ACTIVAS_EN_BAJO, MOTORES
│   │   └── panel.py          geometría del panel web
│   ├── simulacion/           modelo.py, senales.py, fallas.py,
│   │                         escenarios.py, simulador.py, hilo.py
│   ├── hardware/             base.py, pca9685.py, simulado.py,
│   │                         paso_a_paso.py, mapa.py
│   ├── web/
│   │   ├── servidor.py  acceso.py  qr.py
│   │   └── static/           tablero.html, mando.html, sin_permiso.html, caratulas/
│   ├── herramientas/         diagnostico.py, probar_canal.py, probar_motor.py,
│   │                         calibrar_servo.py, prueba_*.py, interactivo.py
│   └── util.py
├── deploy/                   instalar.sh, actualizar.sh, kiosco.sh,
│                             punto_de_acceso.sh, tablero-h08.service.in
├── tests/                    unittest: test_mapa.py, test_luces.py, test_web.py…
└── datos/                    SÓLO en la Pi, fuera de git y del zip:
                              secreto_admin.json, calibracion_servos.json,
                              posicion_motores.json, informes/
```

### 2.3 Reglas de la estructura

| Regla | Cómo |
|---|---|
| Un solo paquete | Todo el código importable vive en `h08/`. Imports absolutos dentro del paquete (`from h08.hardware import pca9685`). Se eliminan todos los `sys.path.insert`. |
| Puntos de entrada | `python3 -m h08` arranca el tablero (opciones: `--simulado`, `--banco`, `--qr-admin`…). Las herramientas: `python3 -m h08.herramientas.diagnostico`, etc. El servicio: `ExecStart=/usr/bin/python3 -m h08` con `WorkingDirectory` en la raíz. |
| Código y datos separados | El código no escribe dentro de `h08/`. Los archivos que cambian (clave, calibración, posición, informes) van a `datos/`, cuya ruta sale de `h08/rutas.py` (una sola definición). Así una actualización puede reemplazar todo `h08/` sin miedo. |
| Configuración por tema | `configuracion.py` se divide en `h08/config/` por tema. `h08/config/__init__.py` reexporta los nombres para que el resto no cambie de golpe. |
| Web como archivos estáticos | `h08/web/static/` tiene HTML y carátulas; el servidor los busca con `rutas.py`, nunca con rutas relativas al directorio actual. |
| Despliegue aparte | Los `.sh` y la plantilla del servicio van en `deploy/`. Son lo único que toca el sistema (systemd, labwc, NetworkManager). |
| Pruebas estándar | `tests/` con `unittest` (biblioteca estándar): `python -m unittest discover -s tests`. Cada archivo prueba un módulo; las pruebas lentas (vuelo completo, en marcha) se marcan y se pueden saltear. |
| Registro | `logging` con un logger por módulo (`log = logging.getLogger(__name__)`). `print()` sólo en herramientas interactivas. |
| Versión única | `h08/__init__.py` define `__version__`; `pyproject.toml` y `VERSION.txt` la toman de ahí. Cada versión entregada tiene su entrada en `CHANGELOG.md`. |
| Nombres | PEP 8: módulos y funciones en minúscula con guion bajo, clases en CapWords, constantes en MAYÚSCULAS. Se mantiene el castellano en los nombres (ya es así en todo el proyecto); lo que importa es ser consistente. |
| Herramientas de calidad | Opcionales y sólo en la PC (en un entorno virtual): `ruff` para estilo y errores comunes. Su configuración va en `pyproject.toml`. Nunca son necesarias en la Pi. |

## 3. Plan de migración por fases

Cada fase: un plan aprobado, cambios, `python -m unittest` (o `py pruebas/correr_pruebas.py` mientras exista) en verde, tablero simulado mirado en `localhost:8000`, y la **aprobación del usuario**, que recién ahí se confirma y se sube (sección 3.1). No se empieza la siguiente sin aprobar la anterior.

| # | Fase | Qué incluye y qué cuidar |
|---|---|---|
| 0 | Red de seguridad | Todas las pruebas en verde y el último commit aprobado como punto de partida. Si algo sale mal, se vuelve ahí con `git restore .` y `git clean -fd`. |
| 1 | Paquete h08 | Mover módulos con `git mv` (conserva la historia), crear `__init__.py`/`__main__.py`, pasar a imports absolutos, borrar los `sys.path.insert`. Actualizar `instalar.sh` (ExecStart), `empaquetar.py`, `kiosco.sh`, pruebas y documentos. |
| 2 | Datos aparte | Crear `rutas.py` y `datos/`. **Migración en la Pi**: al arrancar, si existen los archivos privados en el lugar viejo y no en `datos/`, moverlos (una vez, con mensaje en el registro). `actualizar.sh` tiene que excluir `datos/` y borrar lo que quedó del árbol viejo (rsync `--delete` excluyendo `datos/`). |
| 3 | Configuración por tema | Dividir `configuracion.py` en `h08/config/`. Mantener los mismos nombres públicos. Ningún valor cambia: las pruebas de calibración lo verifican. |
| 4 | Pruebas a unittest | Pasar cada `cierto()`/`igual()` a `self.assertTrue/assertEqual`, un `TestCase` por tema. Mantener el banco de vuelo como prueba de integración. |
| 5 | Registro con logging | Servicio y núcleo con `logging`; formato simple (nivel y mensaje: journald ya pone la hora). |
| 6 | Comentarios y docstrings | Aplicar la sección 4 archivo por archivo, empezando por los más chicos. Es la fase más larga: se aprueba y se sube por módulo o por grupo chico. |
| 7 | Documentación | `README.md` corto, `docs/` con lo largo, `CHANGELOG.md` desde esta versión, `pyproject.toml`. |

Al terminar cada fase se actualizan `CLAUDE.md` y `CONTEXTO_PROYECTO.md` si cambió alguna ruta o comando (por ejemplo, el `ExecStart` del servicio o los comandos de las pruebas).

### 3.1 Qué sube a GitHub y cuándo

- Mientras se trabaja **no se hace ningún commit**. Los cambios quedan sin confirmar; para deshacerlos está el «volver atrás» de Claude Code o `git restore .` + `git clean -fd`, que vuelven al último commit aprobado.
- Cuando el usuario comprobó que anda (pruebas en verde, tablero simulado y, si corresponde, en la Pi) escribe **APROBADO** con una descripción.
- Recién ahí: `git add -A`, **un solo commit** con mensaje como el de la sección 4.5, y `git push`. Así la historia en GitHub tiene sólo versiones que funcionan, una por cambio aprobado.
- `.claude/settings.json` hace que `git commit` y `git push` siempre pidan permiso, aunque Claude Code esté en modo automático.
- Si las pruebas fallan, no se confirma aunque diga APROBADO.

## 4. Comentarios y docstrings que se lean naturales

### 4.1 Principios

- **Explicar el porqué, no el qué.** La guía de estilo de Google lo dice así: nunca describir el código; suponer que quien lee sabe Python mejor que uno, aunque no sepa qué se intenta hacer.
- **Comentar lo que se va a tener que explicar en una revisión.** Si alguien va a preguntar «¿por qué 4075,77 y no 4096?», la respuesta va en un comentario. Si nadie lo va a preguntar, no hace falta.
- **Comentarios en línea, pocos** (PEP 8): separados por dos espacios, sin decir lo obvio.
- **Un comentario que contradice el código es peor que ninguno**: si se cambia el código, se revisa el comentario en el mismo commit.
- **Docstrings según PEP 257**: una primera línea que resume, en una sola línea si alcanza. Las secciones Args/Returns/Raises sólo cuando el nombre y el tipo no lo dicen todo.
- **Datos concretos y fuentes reales** son lo que hace sonar humano a un comentario: unidades, números medidos, el manual (T.O. 1H-19A-1), la hoja de datos del PCA9685, el modelo del servo.
- **Densidad desigual**: mucho comentario donde el código es delicado (tiempo real, engranajes, I2C), nada donde es obvio. Un archivo uniformemente comentado se lee artificial.
- **La historia va en git, no en el código**: «antes hacía X, ahora Y» va en el mensaje del commit o en el CHANGELOG.

### 4.2 Lo que hace que un comentario parezca generado

| Señal | Qué hacer |
|---|---|
| Separadores `# ==========` y `# ----------` entre secciones | Sacarlos. Si un archivo necesita secciones, probablemente son dos módulos. A lo sumo, una línea en blanco y un comentario corto. |
| El mismo encabezado en todos los archivos («Proyecto H-08 · Tablero didáctico… EEST N° 7») | Una sola vez, en el README. El docstring del módulo dice qué hace ese módulo. |
| Docstrings de módulo de 20–40 líneas con títulos en MAYÚSCULAS («POR QUÉ», «CÓMO SE CONECTA», «LO IMPORTANTE») | Docstring de 1 a 6 líneas. Lo largo y conceptual va a `docs/` (por ejemplo `docs/paso_a_paso.md`) y el código lo enlaza. |
| Muletillas: «Por eso…», «No es X: es Y», «Así…», «Ojo:», «Importante:» en serie | Usarlas cuando hacen falta, no como ritmo. Decir el dato directo. |
| Narrar pasos obvios («# Recorremos los canales», «# Devolvemos el resultado») | Borrar. |
| Comentarios que hablan al lector («Fijate que…», «Como podés ver…») | Impersonal y breve. |
| Todo con docstring largo, incluso funciones de 3 líneas | Funciones privadas y obvias: sin docstring o con una línea. |
| Rayas largas, listas numeradas y tono pulido en todos lados | Prosa corta; listas sólo cuando de verdad son pasos. |
| Explicar conceptos de manual (qué es un PWM, qué es I2C) | Sacarlo: el lector sabe o lo busca. Dejar sólo lo propio del proyecto. |
| Emojis y signos de exclamación | Nunca. |

### 4.3 Cómo se ve un buen comentario (ejemplos de este proyecto)

**Encabezado de módulo — antes** (`actuadores_base.py`, 15 líneas):

```
"""
actuadores_base.py - interfaz de la capa de salida (hardware)
==============================================================

El núcleo de simulación no sabe qué hay debajo: sólo conoce estos métodos.
Por eso el mismo código corre en una computadora sin hardware
(actuadores_simulados.py) y en la Raspberry Pi 5 moviendo los servos de
verdad (actuadores_pca9685.py). Cambiar de placa de salida es escribir otra
clase que implemente esta interfaz, sin tocar el modelo de vuelo.
..."""
```

**Después:**

```
"""Interfaz común de las salidas: servos, luces y motores.

Hay dos implementaciones: pca9685 (la Pi) y simulado (PC y pruebas).
Los destinos son tuplas (placa, canal), p. ej. ("PCA0", 7) o ("MOTOR", 1).
"""
```

**Comentario de bloque — antes** (`mapa_tablero.py`):

```
if c.tipo == LED:
    # Las luces no tienen inercia. La prueba de lámparas las
    # enciende todas: es una función real de cabina y sirve para
    # verificar el cableado antes de una clase.
    c.ang = 1.0 if (self.test_luces or valor >= 0.5) else 0.0
    continue
```

**Después:**

```
if c.tipo == LED:
    # sin inercia; la prueba de lámparas manda sobre la señal
    c.ang = 1.0 if (self.test_luces or valor >= 0.5) else 0.0
    continue
```

**Dato concreto con fuente — bien como está** (`configuracion.py`), sólo se acorta:

```
# Reducción real del 28BYJ-48: (32/9)(22/11)(26/9)(31/10) = 63,684, no 64.
# En medio paso: 64 × 63,684 = 4075,77 pasos por vuelta. Con 4096 la aguja
# se corre 1,8° por vuelta.
"pasos_por_vuelta": 4075.77,
```

**Muletilla — antes** (`modelo_vuelo.py`):

```
# --- Indicaciones giroscópicas: lo que MUESTRA el instrumento -----------
# No es la actitud real de la aeronave: es la actitud real filtrada por el
# estado del giróscopo. Con el giro cayendo, el horizonte se va quedando
# atrás y termina mostrando una actitud que ya no existe.
```

**Después:**

```
# Actitud indicada = real filtrada por el estado del giróscopo. Con el giro
# cayendo, el horizonte se atrasa y muestra una actitud que ya pasó.
```

**TODO con dueño y condición** (formato de la guía de Google):

```
# TODO(mateo): sacar cuando la placa tenga el 1N4148 en serie con cada LED.
```

### 4.4 Docstrings de funciones

```
def angulo_servo(it, valor):
    """Ángulo del servo para un valor de la escala del instrumento.

    Usa la tabla de calibración (0..180) y el factor del barrido, igual que
    mapa_tablero; los engranajes y el sentido los resuelve pca9685.
    """
```

- Primera línea: qué devuelve o qué hace, con punto final. Sin «Esta función…».
- Segunda parte sólo si hay algo que no se deduce: unidades, efectos, relación con otro módulo.
- Args/Returns/Raises cuando hay varios parámetros o tipos no obvios. Si se agregan type hints, no repetir el tipo en el docstring.

### 4.5 Mensajes de commit

```
Separar configuracion.py en h08/config por tema

Los valores no cambian; config/__init__ reexporta los mismos nombres.
Las pruebas de calibración pasan igual.
```

- Primera línea en imperativo, de menos de 60 caracteres, sin punto final.
- Cuerpo (opcional): por qué y qué cuidar. El qué ya está en el diff.

### 4.6 Una nota honesta

Estas reglas son para que el código se lea bien y se pueda mantener, que es lo que pide cualquier equipo profesional. Si la escuela o la evaluación piden declarar qué partes se hicieron con ayuda de IA, corresponde declararlo: un buen estilo no reemplaza esa transparencia.

## 5. Reglas para Claude Code (lista de control)

1. Leer `CONTEXTO_PROYECTO.md` y este documento antes de empezar una fase.
2. Trabajar en modo plan: proponer la fase, esperar aprobación, ejecutar sólo esa fase.
3. No cambiar comportamiento ni valores (canales, calibraciones, barridos, pines, red). Las pruebas lo verifican.
4. Mover archivos con `git mv`. **Nunca** `git commit` ni `git push` sin que el usuario escriba APROBADO; entonces, un solo commit y push.
5. Al final de cada fase: pruebas en verde, tablero simulado funcionando, `empaquetar.py` armando el zip, documentos actualizados si cambió una ruta o un comando.
6. Nada de dependencias nuevas en el programa. `ruff` u otras herramientas, sólo opcionales en la PC.
7. Mantener la compatibilidad con Windows en modo simulado y con Python 3.9–3.13.
8. Nunca tocar ni crear los archivos privados (`secreto_admin.json`, `calibracion_servos.json`, `posicion_motores.json`).
9. Comentarios: aplicar la sección 4. Si un comentario largo tiene información valiosa, moverla a `docs/` en vez de borrarla.
10. Si una fase obliga a una decisión que no está en este documento, parar y preguntar.

## Anexo A. Prompt para Claude Code

Copiar en el panel de Claude Code (en modo **Plan**), con la carpeta `C:\H08\H08_Pi5` abierta:

```
Vamos a llevar el proyecto H08_Pi5 a una estructura y un estilo profesionales, sin cambiar lo que hace el tablero.

Antes de proponer nada, leé enteros:
- @docs/GUIA_ESTRUCTURA_Y_ESTILO.md (la estructura objetivo, el plan por fases y cómo escribir comentarios)
- @CONTEXTO_PROYECTO.md (qué hace el programa y el formato en que tiene que estar instalado en la Raspberry Pi 5; manda sobre la guía si chocan)
- @CLAUDE.md

Después:
1. Corré las pruebas (py pruebas/correr_pruebas.py) y decime si están en verde. Si no lo están, pará: primero hay que arreglar eso.
2. Contame en pocas líneas qué entendiste del diagnóstico (sección 1) y si ves algo que la guía no tuvo en cuenta.
3. Proponé el plan detallado SÓLO de la fase 0 y la fase 1: qué archivos se mueven y adónde (con git mv), qué imports cambian, qué se actualiza en instalar.sh, actualizar.sh, kiosco.sh, empaquetar.py, las pruebas, CLAUDE.md y CONTEXTO_PROYECTO.md, y cómo vas a comprobar que el tablero se comporta igual que antes.

Reglas para todo el trabajo:
- Una fase por vez. Al terminar cada una: pruebas en verde, tablero simulado andando en localhost:8000 (normal y ?kiosco=1) y py empaquetar.py armando el zip. Después me mostrás qué cambió y esperás.
- No hagas git commit ni git push por tu cuenta, nunca. Cuando yo lo compruebe y escriba APROBADO, corrés las pruebas de nuevo y, si pasan, hacés un solo commit (mensaje como los de la sección 4.5) y git push. Si no lo apruebo, se deshace todo con git restore . y git clean -fd.
- No cambies ningún valor del tablero (canales, calibraciones, barridos, pines, red wifi) ni agregues dependencias. Sólo biblioteca estándar; tiene que seguir andando en Windows en modo simulado y en la Pi 5 con Python 3.9 a 3.13.
- No toques ni crees secreto_admin.json, calibracion_servos.json ni posicion_motores.json.
- En la fase de comentarios, aplicá la sección 4: el porqué y no el qué, sin separadores ni encabezados repetidos, docstrings cortos, datos concretos y fuentes reales. Si un comentario largo tiene información valiosa, movela a docs/ en vez de borrarla.
- Si algo te obliga a una decisión que la guía no contempla, preguntame antes de seguir.

No cambies ningún archivo hasta que yo apruebe el plan.
```

## Fuentes

- PEP 8 — Style Guide for Python Code: peps.python.org/pep-0008
- PEP 257 — Docstring Conventions: peps.python.org/pep-0257
- Python Packaging User Guide, «src layout vs flat layout»: packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout
- Google Python Style Guide (comentarios, docstrings, TODO): google.github.io/styleguide/pyguide.html
- «Was this Python written by a human or an AI? 7 signs…» (dev.to, sobre señales de código generado)
- Raspberry Pi Documentation, Raspberry Pi OS (pip bloqueado, paquetes por apt): raspberrypi.com/documentation/computers/os.html
