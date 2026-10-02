# El tablero dibujado en la página

Los datos están en `h08/config/panel.py`. La simulación no los usa: sirven para que la
página (`h08/web/static/tablero.html`) dibuje el tablero y explique cada instrumento. La
página no tiene números propios: todo le llega por `/api/catalogo`.

## De dónde sale cada cosa

- **La disposición** (qué va a la izquierda, al centro o arriba a la derecha, y el tamaño
  relativo de cada instrumento) está copiada de una fotografía de cabina de un S-55
  aportada para el proyecto. La foto se usa sólo como referencia de **ubicación**.
- **El contenido** de cada instrumento (qué mide, en qué unidad, con qué escala, con qué
  arcos de color y en qué canal va) no sale de la foto: sale del reporte de aviónica del
  H-08 y del manual T.O. 1H-19A-1. Por eso el tablero dibujado tiene los 21 instrumentos
  del proyecto aunque en la foto se distingan menos.
- Donde la foto y el reporte no coinciden, manda el reporte: no está confirmado que la
  fotografía sea de esta misma célula.

## Medidas

`PANEL_LIENZO` es un lienzo de referencia de 1340 × 680 unidades: la página lo escala para
que entre en la ventana, así que no son píxeles fijos. El tamaño de cada instrumento es
**proporcional a su boca en la chapa del H-08**, a razón de 1,79 unidades por mm:

| Boca | Cantidad | Tamaño | Instrumentos |
|---|---|---|---|
| 122 mm | 2 | 218 | horizonte artificial y brújula |
| 78 mm | 7 | 140 | velocímetro, altímetro, variómetro, viraje, tacómetro, admisión, AN/ARN-14 |
| 58 mm | 3 | 104 | los dos aforadores y la temperatura de culata |
| 48 mm | 9 | 86 | los otros seis de motor y transmisión, amperímetro, voltímetro y reloj |

## Campos de `PANEL`

| Campo | Qué es |
|---|---|
| `desc` | para qué sirve, tomado del reporte de aviónica del H-08 (lo ve la persona al tocar el instrumento) |
| `zona` | agrupador según la columna «UBICACIÓN EN CABINA» del reporte |
| `dial` | qué tipo de esfera se dibuja |
| `pos` | (x, y) de la esquina superior izquierda en el lienzo |
| `tam` | diámetro en unidades del lienzo (ver la tabla de bocas) |

Tipos de esfera: `aguja` (redonda con una aguja), `tacometro` (dos agujas concéntricas,
motor y rotor), `altimetro` (decenas de miles, miles y centenas de pies), `horizonte`,
`viraje` (aguja más bola de ladeo), `brujula` (tarjeta giratoria bajo la línea de fe),
`cdi` (aguja vertical de desvío de radial), `reloj` y `luz` (anunciador rectangular).

## Zonas

`PANEL_ZONAS` son las regiones físicas del tablero: `verde` es la chapa estructural
pintada de verde militar y `negro` el sub-panel atornillado encima (el de los
instrumentos de vuelo).

## El panel de conmutadores

El cuarto izquierdo del tablero real del H-08 es una chapa llena de llaves, disyuntores y
dos llaves con guarda roja. En el tablero físico esos mandos son **decorativos** (no se
cablean), pero la página los dibuja y los **anima** con el estado del simulador: cuando
el piloto virtual energiza la batería, la palanca de batería sube sola. Es la forma de
mostrar, sin tocar nada, qué hace el piloto en cada fase del vuelo.

Campos de `PANEL_CONMUTADORES`:

| Campo | Qué es |
|---|---|
| `tipo` | `placa` (chapa de identificación), `rotulo` (texto de grupo), `palanca` (llave de dos posiciones), `guarda` (llave con tapa de seguridad roja), `rotativo` (selector de varias posiciones), `disyuntor` (térmico redondo, salta hacia afuera), `nota` (placa de texto) |
| `senal` | qué campo del estado del simulador lo mueve |
| `inv` | True si la llave está arriba cuando la señal es False |

`PANEL_PLACAS` (chapas de texto sobre el tablero) está vacía a propósito: la ficha de la
aeronave y sus limitaciones están en la memoria técnica, y en pantalla sólo van
instrumentos.
