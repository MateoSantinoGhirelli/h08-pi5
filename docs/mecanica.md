# Mecánica de las agujas

Los números están en `h08/config/mecanica.py` (`BARRIDO`, `ENGRANAJES`, `HORIZONTE`) y la
cuenta que los usa está resumida en `CLAUDE.md` («La cuenta que no se puede romper»).

## Cuánto barre cada aguja

Un instrumento de aviación no barre 180 grados: cada tipo barre lo suyo. Un velocímetro
de tres pulgadas recorre unos 300; la aguja de miles de un altímetro da la vuelta entera
cada 10.000 pies; la aguja de viraje se mueve apenas 30 grados para cada lado; y un
amperímetro de aguja central de la época no llega a 120. Los valores de `BARRIDO` son los
típicos de cada tipo de instrumento de la época.

Manda el barrido real del instrumento y la mecánica se acomoda. De ese número salen:

- **el dibujo de la carátula**: cada marca va en
  `ang_dibujo = centro + B/2 − a·B/180` (si B ≥ 360, `centro − a`), con `a` el ángulo de la
  tabla `cal` y `centro = 90` salvo el variómetro (180, su cero va a las 9);
- **el par de engranajes** impreso que va adentro de la réplica;
- **el ángulo que se le manda al servo** (`factor_servo`).

### Cómo se resuelve mecánicamente

| Barrido | Solución |
|---|---|
| ≤ 180° | El servo alcanza solo: la aguja va calzada directo en su eje y el servo usa sólo la parte del recorrido que hace falta. |
| > 180° | Hace falta un par de engranajes que **multiplique**: el servo da 180° y la aguja tiene que dar más. La relación es barrido/180. |

Los tres pares (módulo 0,5, con 24 dientes en la aguja, que es lo que entra en las bocas
de 48 mm y todavía sale limpio en una impresora de filamento):

| Barrido | Relación | Dientes servo / aguja |
|---|---|---|
| 270° | 1,5 | 36 / 24 |
| 300° | 1,667 | 40 / 24 |
| 360° | 2 | 48 / 24 |

Un par de engranajes exteriores invierte el giro: para que la aguja vaya en sentido
horario, el servo tiene que ir al revés. Por eso `invertido(id)` da vuelta los pulsos.

### Si se cambia un barrido o una tabla `cal`

Las carátulas impresas (el PDF de 5 hojas) y sus copias de la página
(`h08/web/static/caratulas/`) están dibujadas con estos números. **No hay un programa en
el proyecto que las regenere**: se hicieron aparte. Cambiar un barrido o una tabla `cal`
obliga a hacer carátulas nuevas, a reimprimirlas y, si cambia la relación, a imprimir
otro par de engranajes. Para calzar una aguja corrida no se toca nada de esto: se calza
la aguja (`python3 -m h08 canal ID --valor V`) o se calibra el servo.

## El horizonte artificial

Es el único instrumento con dos grados de libertad y el único cuyo actuador no mueve la
indicación en línea recta. Sus dos tablas se calculan a partir de la mecánica en vez de
escribirse a mano: si cambia una pieza, cambian solas (`tabla_cabeceo`, `tabla_alabeo`).

### Cabeceo: yugo escocés

Un perno del brazo del servo entra en una ranura horizontal de la corredera. A la
corredera sólo le importa la altura del perno, así que la carrera es exactamente
`y = r · sen(θ)`. Para que la aguja indique proporcional al cabeceo hay que cancelar ese
seno:

    sen(θ) = cabeceo · sen(60°) / 30   →   θ = arcsen(cabeceo / 34,641)

El resultado no depende de la carrera elegida: si cambia la carrera, cambia el radio del
perno (`radio_perno_mm`), no la tabla. Con una tabla de tres puntos el error llega a 2,4°
de cabeceo a media escala; con la de trece puntos, a 0,2°.

### Alabeo: plato 70/50

Un par de engranajes exteriores de módulo 1 (plato Z = 70, piñón Z = 50) desmultiplica 1,4
a 1: el servo recorre ±84° para que el plato gire ±60°. Tres puntos alcanzan, porque un
par de engranajes es exactamente lineal.

### El sentido: dos inversiones que se cancelan

1. Un servo estándar gira en sentido horario al aumentar el ancho de pulso, mirándolo
   desde la cara del eje. Los dos ejes apuntan hacia adelante, así que desde el asiento
   del piloto ambos giran en sentido horario.
2. Un par de engranajes exteriores invierte: el plato gira en sentido antihorario.
3. En un alabeo a la derecha el horizonte real se ve girar en sentido antihorario
   respecto del tablero: alabeo positivo = plato antihorario = servo creciente. La tabla
   de alabeo queda creciente.
4. En el cabeceo no hay engranaje: el perno baja cuando el servo crece. Cabeceo positivo
   (nariz arriba) tiene que bajar el disco para que suba la tierra. También queda
   creciente.

Si al probarlo el instrumento se mueve al revés (por la marca del servo o por cómo quedó
calzado el brazo), se invierten los dos extremos de la tabla que corresponda. El
mecanismo no se toca.
