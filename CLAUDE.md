# Tablero H-08 · programa de la Raspberry Pi 5

Tablero didáctico de un Sikorsky S-55 / H-19A (EEST N° 7, Taller Regional Quilmes).
Un simulador de vuelo mueve 20 servos, 6 luces y el motor paso a paso de la brújula,
y sirve una página web (pantalla de la Pi en modo kiosco + celulares por wifi).

- Se DESARROLLA en Windows y se prueba en modo simulado.
- Se INSTALA en una Raspberry Pi 5 con Raspberry Pi OS con escritorio (Bookworm o
  posterior, Python 3.11) llevando `dist/H08_Pi5.zip` en un pendrive.
- El documento completo del proyecto (requisitos, hardware, canales, y el FORMATO en
  que tiene que estar instalado un programa en la Pi 5) es `CONTEXTO_PROYECTO.md`.
  Leerlo antes de cualquier cambio grande o de tocar instalación/arranque.
- La guía para humanos está en `LEEME.md` (leerla cuando haga falta, no se carga sola).

## Comandos (Windows: `py`; en la Pi: `python3`)

- Todas las pruebas: `py pruebas/correr_pruebas.py` (menos de 1 minuto, sin hardware)
- Ver el tablero: `py raspberry_pi5/tablero_pi5.py --simulado --sin-clave`
  y abrir http://localhost:8000/ (pantalla de la Pi: `/?kiosco=1`, mando: `/mando`)
- Pruebas guiadas sin hardware: `py raspberry_pi5/prueba_general.py --simulado --auto`
  (igual `prueba_instrumento.py --todos`, `prueba_luces_motor.py`)
- Armar el zip para la Pi: `py empaquetar.py` (corre las pruebas primero)

## Reglas

- **Sólo biblioteca estándar de Python** en `nucleo/`, `raspberry_pi5/` y `pruebas/`.
  Nada de pip ni paquetes nuevos. En la Pi sólo hay gpiozero y lgpio del sistema,
  importados adentro de funciones (en Windows no existen).
- Tiene que seguir andando en Windows en modo simulado: nada de `fcntl`, `grp`,
  `os.geteuid` ni rutas fijas de Linux fuera de un `try` o de una función que sólo
  corre en la Pi.
- **Nunca** crear, leer para copiar, ni meter en un zip o en git:
  `raspberry_pi5/secreto_admin.json`, `calibracion_servos.json`, `posicion_motores.json`.
- Los datos del tablero (canales, escalas, calibraciones, barridos, pines, direcciones)
  viven SÓLO en `nucleo/configuracion.py`. No repetirlos en otro archivo.
- Si una aguja física no cae en su marca, NO se toca la tabla `cal`: las carátulas
  impresas están dibujadas con esa tabla. Se calza la aguja
  (`probar_canal.py ID --valor V`) o se calibra el servo
  (`calibrar_servo.py PCA0 N --asistente`). La tabla `cal` sólo cambia si se
  reimprimen las carátulas.
- Los `.sh` corren en la Pi con bash: fin de línea LF, probarlos con `bash -n`.
- Todo texto que ve una persona (mensajes, página, comentarios) va en castellano
  rioplatense (voseo), claro y sin jerga innecesaria.
- Después de cada cambio: correr `py pruebas/correr_pruebas.py`. Si se agrega
  algo, agregar su prueba en `pruebas/` (lo nuevo de la Pi va en `prueba_pi5.py`).
- Cambios chicos y de a uno. Antes de tocar varios archivos, proponer un plan.
- No se puede probar acá: I2C, GPIO, systemd, NetworkManager, Chromium kiosco.
  Eso se prueba en la Pi con `diagnostico_pi.py` y las pruebas guiadas; cuando el
  usuario traiga un informe de `raspberry_pi5/informes/`, leerlo y corregir desde ahí.

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

- `nucleo/configuracion.py`: el tablero en datos. `TABLERO` (30 entradas),
  `BARRIDO`, `ENGRANAJES`, `HORIZONTE`, `PLACAS` (PCA0 0x40, PCA1 0x41),
  `SERVO_CFG` (500–2500 µs), `LUCES_ACTIVAS_EN_BAJO`, `MOTORES`, `ARRANQUE`.
- Flujo cada 50 ms: `modelo_vuelo` + `fallas` + `escenarios` → `simulador`
  → `senales` (real vs indicado) → `mapa_tablero` → `actuadores_pca9685` (servos y
  luces por I2C) y `paso_a_paso` (brújula por GPIO 12-16-20-21).
- `raspberry_pi5/tablero_pi5.py` arranca todo; `hilo_simulacion.py` (20 Hz) y
  `nucleo/servidor_web.py` (puerto 8000, API, QR, carátulas; órdenes sólo con la
  clave del profesor, ver `acceso.py`).
- Página: `raspberry_pi5/web/tablero.html` (sin datos propios: todo sale de
  `/api/catalogo`), `mando.html`, carátulas en `web/caratulas/` (copias de las
  impresas; no editarlas a mano).

## La cuenta que no se puede romper

valor → `interpolar_tabla(valor, cal)` (tabla en 0..180) → × `factor_servo(id)` →
ángulo del servo → pulso con la calibración del servo.

- Barrido > 180° (270, 300, 360): el servo recorre 0..180 y un par de engranajes
  multiplica (36/24, 40/24, 48/24). El par invierte el giro: `invertido(id)` da
  vuelta los pulsos (0° = 2500 µs).
- Barrido ≤ 180°: aguja directa, el servo usa sólo `barrido` grados.
- La carátula impresa y la página ponen la marca en
  `ang_dibujo = centro + B/2 − a·B/180` (B ≥ 360: `centro − a`). Si se cambia un
  barrido o una tabla `cal`, las carátulas se regeneran fuera de este paquete
  (herramientas/caratulas.py y caratulas_web.py); avisarle al usuario.

## Hardware (para no inventar)

- Luces: ánodo a +5 V, cátodo por 220 Ω al PCA1 canales 8–13 → encienden con la
  salida en BAJO. Con salida en alto (3,3 V) puede quedar una luz fantasma tenue:
  se arregla en la placa con un 1N4148 en serie, no en el programa.
- Placa madre ESPEJADA: J1 se cablea con Dupont pata por pata por función; el
  código no cambia. El KiCad no se toca.
- Fuente de servos LM2596 (3 A máx.): por eso el arranque escalonado de a 3.
