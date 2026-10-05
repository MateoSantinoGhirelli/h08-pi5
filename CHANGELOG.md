# Historial de cambios

Las versiones siguen [SemVer](https://semver.org/lang/es/) y el formato es el de
[Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Cada versión entregada
(la que viaja en `dist/H08_Pi5.zip`) tiene su entrada acá.

La versión que corre el tablero está en `h08/__init__.py` y se ve al arrancar y en
`python3 -m h08 diagnostico`.

## [1.0.0] - 2026-10-02

Primera versión ordenada. El programa pasó de muchos archivos sueltos al paquete
`h08`, con el código separado de los datos y las pruebas al estándar de Python. El
tablero hace lo mismo que antes: ningún canal, calibración, barrido, pin ni la red wifi
cambiaron de valor.

### Agregado
- Paquete `h08` que se arranca con `python3 -m h08` (antes `raspberry_pi5/tablero_pi5.py`).
- Subcomandos de prueba y ajuste: `diagnostico`, `prueba-general`, `luces-motor`,
  `instrumento`, `canal`, `motor`, `calibrar`.
- Carpeta `datos/` para lo que es de cada tablero (clave, calibración, posición del
  motor, informes), separada del código. Al arrancar, lo que haya quedado en
  `raspberry_pi5/` se muda solo, una vez.
- Registro con niveles (`INFO`, `AVISO`, `ERROR`); en el servicio sale con la prioridad
  que entiende `journalctl`.
- Documentación: este `CHANGELOG.md`, el `README.md` y las explicaciones largas en
  `docs/` (modelo de vuelo, hardware, acceso, calibración, geometría del tablero).

### Cambiado
- `nucleo/configuracion.py` se dividió en `h08/config/` por tema (aeronave, tablero,
  mecánica, hardware, panel), con los mismos nombres públicos.
- Las pruebas pasaron a `unittest` y se corren con `python3 -m pruebas`
  (`--rapido` saltea las lentas).
- Los scripts de instalación y arranque viven en `deploy/`; el servicio arranca con
  `ExecStart=/usr/bin/python3 -m h08`.

### Corregido
- El servidor web rechaza en el acto un pedido con un `Content-Length` enorme o
  inválido, en vez de reservar esa memoria (un visitante sin clave podía tumbar la Pi).
- Una conexión abandonada (un celular que se fue de la red sin cerrar) se cierra sola
  pasado un minuto, en vez de dejar un hilo colgado para siempre.
- La clave con una tilde (`/mando?k=ñ`) ya no corta el pedido con un error.
- `python3 -m h08` con el servicio ya en marcha avisa que el puerto está tomado antes de
  abrir las placas, en vez de dejar los servos sin pulso.
- La cámara lenta (`0,5×`) ahora avanza exactamente a esa velocidad.
- `deploy/actualizar.sh` rechaza un paquete que no es la versión nueva, o la propia
  carpeta instalada, en vez de copiarse sobre sí mismo y decir «Listo».
- La calibración de un servo y la posición de la brújula se guardan aunque `datos/` no
  exista todavía (un banco de pruebas donde el tablero nunca arrancó).
- `python3 -m h08 canal COMPASS` avisa que la brújula es el motor paso a paso y manda a
  `python3 -m h08 motor`, en vez de intentar moverla como un servo que no existe.

[1.0.0]: https://github.com/MateoSantinoGhirelli/h08-pi5/releases/tag/v1.0.0
