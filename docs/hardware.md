# Las salidas: PCA9685 y 28BYJ-48

Cómo son los dos tipos de salida del tablero y por qué el programa los maneja así. El
código está en `h08/hardware/`; los valores, en `h08/config/hardware.py`.

## Los PCA9685 (servos y luces)

Cada placa genera 16 salidas PWM de 12 bits (4096 cuentas por período) con una base de
tiempo común. La frecuencia sale del prescaler:

    prescale = round(25 MHz / (4096 · f)) − 1        → 121 para 50 Hz

A 50 Hz el período es de 20 ms y cada cuenta vale 4,88 µs. Un servo usa pulsos de 500 a
2500 µs, o sea de 102 a 512 cuentas: unos **410 pasos para 180°, 0,44° por paso**. Con
engranajes de 270 o 300°, ese paso se multiplica en la aguja.

Cada canal ocupa cuatro registros seguidos (ON_L, ON_H, OFF_L, OFF_H). Con el
autoincremento de MODE1 activado se escriben varios canales en una sola transacción: el
programa manda de una vez el tramo que va del primer al último canal que cambió. Dos bits
fijan la salida sin PWM:

| Bit | Efecto |
|---|---|
| bit 4 de ON_H | salida siempre en alto («full ON») |
| bit 4 de OFF_H | salida siempre en bajo («full OFF», tiene prioridad) |

Se usan para las luces, que son todo o nada, y para soltar los servos: sin pulso el servo
no hace fuerza ni zumba contra un tope.

Con el bus se habla por `/dev/i2c-1` del kernel, con `os` y `fcntl`, sin instalar nada.
Cada escritura es una transacción: la dirección del registro y los datos.

### Dos cuidados propios del tablero

- **Las luces van invertidas** (`LUCES_ACTIVAS_EN_BAJO`): el PCA9685 sumidera la
  corriente, así que el LED enciende con la salida en bajo.
- **Si una placa se reinicia** por una caída de tensión vuelve dormida, sin
  autoincremento y con todas las salidas en bajo. Cada dos segundos el programa lee
  MODE1; si se reinició, la vuelve a configurar, le reenvía todos los canales y lo anota
  como aviso en el registro.
- **Un error de bus no detiene el tablero**: se cuenta, se avisa (como mucho uno cada
  10 s) y los canales que no se pudieron escribir se reintentan en el ciclo siguiente.

## El 28BYJ-48 (la aguja de la brújula)

### Por qué un paso a paso y no un servo

Dos indicaciones del tablero dan vueltas enteras: la aguja de centenas del altímetro (una
vuelta cada 1000 pies) y la de la brújula, que pasa por el norte y sigue. Un servo tiene
topes y tendría que desandar la vuelta entera cada vez. El 28BYJ-48 gira indefinidamente
en los dos sentidos y trae una reducción de 63,68:1, así que mueve la aguja sin esfuerzo.
En el tablero quedó sólo el de la brújula: las centenas del altímetro se dibujan en la
página.

### Cómo se conecta

Cada motor usa la plaquita ULN2003 con la que viene de fábrica, montada junto al motor.
Los cuatro GPIO de la Pi llegan por la placa madre y cables Dupont a IN1..IN4; el motor se
enchufa en su conector blanco. El ULN2003 es el que maneja la corriente de las bobinas
(50 Ω a 5 V: unos 100 mA cada una, 200 mA con dos a la vez): un pin de la Pi no da más de
16 mA y no tiene diodos para la descarga inductiva.

La secuencia de **medio paso** energiza una o dos bobinas por vez:

    IN1 · IN1+IN2 · IN2 · IN2+IN3 · IN3 · IN3+IN4 · IN4 · IN4+IN1

Avanzar un paso es pasar al estado siguiente; retroceder, al anterior. Si los cables
IN1..IN4 están cruzados, el motor tiembla y no gira: con `python3 -m h08 motor 1 --bobinas`
los LED de la plaquita tienen que encenderse en orden A, B, C, D.

### Cómo se mueve

Los motores tienen su propio hilo, que duerme hasta el instante del próximo paso. La
velocidad sigue un perfil trapezoidal: arranca a `vel_arranque_pps`, acelera hasta
`vel_max_pps` y frena a tiempo para detenerse justo en el objetivo. Así no pierde pasos, y
un motor que no pierde pasos no necesita sensor de posición.

- **Camino más corto:** ir de 350° a 10° son 20° hacia adelante, no 340° hacia atrás. El
  objetivo se lleva en grados «desenrollados».
- **Bobinas sueltas en reposo:** quieto más de `soltar_tras_s`, se cortan las bobinas. Un
  28BYJ-48 energizado consume y se calienta aunque no se mueva, y la reducción alcanza
  para que la aguja no se corra sola.
- **Posición guardada:** al apagar en orden, la aguja vuelve a su cero y la posición queda
  en `datos/posicion_motores.json`. Al encender se lee de ahí. Si hubo un corte de luz, la
  última posición guardada con el motor quieto sirve igual.
- **Pasos por vuelta:** 4075,77, no 4096 (ver `h08/config/hardware.py`).
