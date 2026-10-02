# El simulador de vuelo

El código está en `h08/simulacion/`: `modelo.py` (la física y el piloto virtual),
`senales.py` (lo real contra lo indicado), `fallas.py`, `escenarios.py` y `simulador.py`
(el que los junta y corre el paso de 50 ms).

## Qué se simula y qué no

No se simula un helicóptero completo de seis grados de libertad: sería costoso en CPU,
difícil de calibrar e innecesario para mover agujas. Se usa un modelo **cuasi-estático
con retardos**, que es como razona un técnico:

> Si el piloto sube el colectivo, la potencia requerida sube; el motor responde subiendo
> la presión de admisión; si la potencia entregada no alcanza, el régimen del rotor cae;
> la temperatura de culata sube despacio porque tiene mucha masa térmica…

Cada magnitud tiene un **objetivo** calculado algebraicamente y lo persigue con una
constante de tiempo propia (`aproximar` en `h08/util.py`). El resultado es físicamente
coherente, determinista, estable con cualquier paso de tiempo y explicable renglón por
renglón, que es lo que se le pide a un material didáctico.

### La única ecuación diferencial de verdad

La excepción es la inercia del rotor principal, que sí se integra:

    d(Ω)/dt = (P_disponible − P_requerida) / (I · Ω)

Esa sola ecuación produce, sin agregar nada más, los fenómenos más didácticos del
tablero:

- las RPM caen si se pide más potencia de la que hay;
- en autorrotación, **bajar** el colectivo hace **subir** el régimen del rotor;
- el «needle split» del tacómetro doble al desacoplar la rueda libre;
- el aterrizaje en autorrotación, agotando la energía cinética del rotor.

## Lo real y lo indicado

En una aeronave conviven dos cosas que conviene no confundir:

| | |
|---|---|
| **Valor real** | lo que físicamente pasa en la máquina: la presión de aceite cayó a 10 psi |
| **Valor indicado** | lo que muestra la aguja: el transmisor se cortó y marca 0, pero el motor está perfecto |

Una **falla de sistema** cambia el valor real. Una **falla de indicación** cambia sólo lo
que se ve. Distinguirlas es justamente lo que se le enseña a un piloto o a un técnico:
antes de cortar el motor, verificar si lo que falló es el motor o el instrumento.
`senales.py` mantiene las dos listas y la página muestra siempre la indicada.

Entre una y otra está el **modelo de sensor**, que agrega los defectos de todo
instrumento real:

- **retardo** (`tau`): ningún sensor responde instantáneamente;
- **ruido**: vibración del motor radial (proporcional a las RPM: un radial detenido no
  hace temblar ninguna aguja) y ruido eléctrico;
- **anomalías de indicación** que inyectan las fallas: aguja congelada, clavada en un
  valor, con ruido o oscilando;
- **pérdida de alimentación**: por debajo de 20 V en la barra, los instrumentos
  eléctricos indican cada vez más bajo, no se apagan de golpe.

El ruido se suma **después** del filtro y no se realimenta: si entrara al filtro, la
señal haría un paseo aleatorio con una desviación varias veces mayor que la declarada.
Por eso se guardan dos estados, el filtrado limpio y el que se muestra.

## Qué instrumentos dependen de la barra eléctrica

No todos los instrumentos del H-19A dependen de la barra de 24 V, y saber cuáles no es
lo que permite volar con una falla eléctrica total. Esta lista es la base del escenario
de falla eléctrica, y en el código es `_SENALES_ELECTRICAS` (`h08/simulacion/senales.py`).

### Siguen funcionando sin energía

- **Velocímetro, altímetro y variómetro:** son neumáticos. Viven del tubo pitot y de la
  toma estática; no tienen un solo cable.
- **Tacómetro doble:** lo mueve un generador tacométrico arrastrado por el motor y por la
  transmisión, así que fabrica su propia corriente. Por eso se lo puede mirar durante el
  arrastre del arrancador, cuando la barra está en 18 V y el resto del tablero está a
  media asta: es **el** instrumento del arranque.
- **Manómetros de presión de aceite, de combustible y de admisión:** son de tubo Bourdon,
  con una cañería que lleva el fluido hasta el instrumento. Mecánicos puros.
- **Temperatura de cabeza de cilindro:** termocupla. Genera su propia tensión por efecto
  Seebeck.
- **Reloj de cabina:** mecánico, de cuerda.

### Dejan de indicar con la barra caída

- **Aforadores de combustible:** flotante y puente de resistencia.
- **Temperaturas de aceite y de aire del carburador:** bulbos de resistencia.
- **Presión y temperatura de transmisión:** transmisores eléctricos.
- **Horizonte artificial e indicador de rumbo:** giróscopos alimentados por el inversor.
  No se apagan de golpe: se van cayendo, que es peor.
- **Indicador de rumbo del receptor de radionavegación** y **todas las luces de alerta.**
