# Calibrar los servos

Se hace con `python3 -m h08 calibrar`, con el servicio detenido. Lo medido queda en
`datos/calibracion_servos.json`, que es de **ese** tablero y no se copia a otro.

## Por qué hace falta

El programa convierte grados en ancho de pulso con valores nominales: 500 µs son 0° y
2500 µs son 180°. Cada servo real es distinto, sobre todo los SG90 y los clones del
MG90S: con los valores nominales uno llega a 170°, otro a 195° y otro zumba contra su
tope. La aguja no cae en las marcas.

La calibración mide, con un transportador impreso, qué pulso deja el brazo del servo
exactamente en 0° y en 180°. **La tabla `cal` del instrumento no se toca**: lo único que
cambia es cómo se convierte ese ángulo en pulso.

## El transportador

Se imprime al 100 % (`Transportador_servo.pdf`), se pega sobre cartón y se apoya el servo
con el eje sobre la cruz, **mirándolo desde el lado del eje**: 0° queda a la izquierda y
180° a la derecha, por arriba.

Así se calibran todos los servos, lleven engranajes o no: el programa sabe cuáles
invierten el sentido (`invertido` en `h08/config/mecanica.py`) y lo corrige solo.

## Qué se guarda de cada servo

| | |
|---|---|
| `us_0`, `us_180` | el pulso que deja el brazo en 0° y en 180° del transportador; pueden quedar extrapolados si el servo no llega |
| `tope_a`, `tope_b` | los pulsos extremos que el servo sí alcanza, que el programa no pasa para que no zumbe contra el tope |

## Cuándo se usa

- Si un servo **no llega a un extremo** o **zumba** contra el tope.
- Si una aguja marca corrido en toda la escala por igual.

Si la aguja está corrida pero el servo llega bien a los dos extremos, no es calibración:
hay que calzar la aguja con `python3 -m h08 canal ID --valor V`.
