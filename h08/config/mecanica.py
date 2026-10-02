# -*- coding: utf-8 -*-
"""Mecánica de las agujas: barrido, engranajes y el mecanismo del horizonte."""

import math as _math

# ---------------------------------------------------------------------------
# CUÁNTO BARRE CADA AGUJA
# ---------------------------------------------------------------------------
# Un instrumento de aviación no barre 180 grados: cada tipo barre lo suyo. Un
# velocímetro de tres pulgadas recorre unos 300; la aguja de millares de un
# altímetro da la vuelta entera cada 10.000 pies; la aguja de un indicador de
# viraje se mueve apenas 30 grados para cada lado; y un amperímetro de aguja
# central de la época no llega a 120.
#
# Manda el barrido real del instrumento, y la mecánica se acomoda. De este
# número sale todo lo demás, sin escribirlo dos veces:
#
#   * el dibujo de la carátula: dónde cae cada marca de la escala;
#   * la relación del par de engranajes impreso que va adentro de la réplica;
#   * el ángulo que hay que mandarle al servo.
#
# CÓMO SE RESUELVE MECÁNICAMENTE
#   barrido <= 180   el servo alcanza solo. La aguja se calza directo en su
#                    eje y el servo usa nada más que la parte del recorrido
#                    que hace falta.
#   barrido >  180   hace falta un par de engranajes que MULTIPLIQUE: el servo
#                    da 180 y la aguja tiene que dar más. La relación es
#                    barrido/180, y de ahí salen los dientes.
#
# Los valores son los típicos de cada tipo de instrumento de la época. Cada
# uno se corrige por separado: cambiar el número alcanza para que se rehagan
# la carátula, los engranajes y la tabla del servo.
# ---------------------------------------------------------------------------
BARRIDO = {
    # --- vuelo, bocas de 78 mm ---------------------------------------------
    "AIRSPEED":       300,   # velocímetro de 3 pulgadas, escala larga
    "ALTIMETER":      360,   # millares: una vuelta entera cada 10.000 pies
    "ALTIMETER_100": "CONT", # centenas: da vueltas sin parar, motor continuo
    "VSI":            300,   # variómetro de +-2000 pies por minuto
    "TURN":            60,   # la aguja de viraje se mueve +-30 y nada más
    "SLIP":            70,   # no es una aguja: es el arco que recorre la bola
    "TACH_ENG":       300,   # tacómetro doble
    "TACH_ROT":       300,   # la otra aguja del mismo instrumento
    "MAP":            270,   # manómetro de presión de admisión
    "VOR_CDI":         40,   # aguja de desvío de curso, +-20

    # --- combustible y culata, bocas de 58 mm ------------------------------
    "FUEL_QTY_FWD":   120,   # aforador de flotante: arco corto
    "FUEL_QTY_AFT":   120,
    "CHT":            270,   # termómetro de culata

    # --- motor, transmisión y eléctricos, bocas de 48 mm -------------------
    "OIL_TEMP":       270,
    "OIL_PRESS":      270,
    "FUEL_PRESS":     270,
    "CARB_AIR_TEMP":  270,
    "XMSN_OIL_TEMP":  270,
    "XMSN_OIL_PRESS": 270,
    "AMMETER":        120,   # amperímetro de aguja central, arco corto
    "VOLTMETER":      120,

    # --- las dos bocas de 122 mm -------------------------------------------
    "COMPASS":       "CONT", # la rosa da la vuelta entera, motor continuo
    "ATT_PITCH":     "MEC",  # el horizonte tiene su propio mecanismo
    "ATT_ROLL":      "MEC",
}

# Dónde va el MEDIO de la escala, en ángulo de dibujo (matemático: 90 es
# arriba). Casi todas las escalas se centran arriba; el variómetro no: su cero
# va a las 9, como en el de verdad. Lo usan las carátulas impresas
# (herramientas/caratulas.py) y la página web, que dibuja las mismas carátulas:
# por eso está acá y no en uno de los dos.
CENTRO_ESCALA = {
    "VSI": 180.0,
}

# Las tres relaciones que hacen falta y los dientes de cada par (servo, aguja).
# Módulo 0,5 con 24 dientes en la aguja: es lo que entra en las bocas de 48 mm
# y todavía sale limpio en una impresora de filamento.
ENGRANAJES = {
    1.5:    (36, 24),        # 270 grados de aguja
    5/3.0:  (40, 24),        # 300 grados
    2.0:    (48, 24),        # 360 grados
}
MODULO_ENGRANAJE = 0.5


def reduccion(id_instrumento):
    """Cuánto multiplica el par de engranajes. 1 = la aguja va directo al servo."""
    b = BARRIDO.get(id_instrumento)
    if not isinstance(b, (int, float)):
        return 1.0
    return max(1.0, b / 180.0)


def invertido(id_instrumento):
    """True si entre el servo y la aguja hay un par de engranajes.

    Un par de engranajes exteriores invierte el sentido de giro: para que la
    aguja vaya en sentido horario, el servo tiene que ir al revés. Pasa en los
    instrumentos con reducción y en el alabeo del horizonte.
    """
    return reduccion(id_instrumento) > 1.0 or id_instrumento == "ATT_ROLL"


def factor_servo(id_instrumento):
    """De ángulo de la tabla de calibración a ángulo del servo.

    La tabla de cada instrumento está escrita en 0..180, como si la esfera
    midiera 180 grados. Este factor la lleva al recorrido real del servo:

        barrido <= 180  ->  el servo recorre justo el barrido
        barrido >  180  ->  el servo recorre 180 y los engranajes hacen el resto

    Así las tablas no se tocan cuando cambia un barrido: cambia el factor.
    """
    b = BARRIDO.get(id_instrumento)
    if not isinstance(b, (int, float)):
        return 1.0
    return (b / 180.0) / reduccion(id_instrumento)


# ---------------------------------------------------------------------------
# MECÁNICA DEL HORIZONTE ARTIFICIAL
# ---------------------------------------------------------------------------
# El horizonte es el único instrumento con dos grados de libertad, y el único
# cuyo actuador no mueve la indicación en línea recta. Sus dos tablas se
# calculan a partir de la mecánica en vez de escribirse a mano: si cambia una
# pieza, cambian solas.
#
#   CABECEO. Un yugo escocés: un perno del brazo del servo entra en una
#   ranura horizontal de la corredera. A la corredera sólo le importa la
#   ALTURA del perno, así que la carrera es  y = r · sen(θ)  exactamente, no
#   aproximadamente. Para que la aguja indique proporcional al cabeceo hay
#   que cancelar ese seno:
#
#       sen(θ) = cabeceo · sen(60°) / 30   ->   θ = arcsen(cabeceo / 34.641)
#
#   El resultado no depende de la carrera elegida: si cambia la carrera
#   cambia el radio del perno, no la tabla. Con una tabla de tres puntos el
#   error llega a 2.4 grados de cabeceo a media escala; con ésta, a 0.2.
#
#   ALABEO. Un par de engranajes exteriores de módulo 1 (plato Z=70, piñón
#   Z=50) desmultiplica 1.4 a 1: el servo recorre ±84 grados para que el
#   plato gire ±60.
#
# EL SENTIDO. Hay dos inversiones y se cancelan:
#
#   1. Un servo estándar gira EN SENTIDO HORARIO al aumentar el ancho de
#      pulso, mirándolo desde la cara del eje. Los dos ejes apuntan hacia
#      adelante, así que desde el asiento del piloto ambos giran horario.
#   2. Un par de engranajes EXTERIORES invierte: el plato gira antihorario.
#   3. En un alabeo a la derecha el horizonte real se ve girar ANTIHORARIO
#      respecto del tablero. O sea que alabeo positivo = plato antihorario
#      = servo creciente. La tabla queda creciente.
#   4. En el cabeceo no hay engranaje: el perno BAJA cuando el servo crece.
#      Cabeceo positivo (nariz arriba) tiene que BAJAR el disco para que
#      suba la tierra. También queda creciente.
#
# Si al probarlo el instrumento se mueve al revés -por la marca del servo o
# por cómo quedó calzado el brazo-, se invierten los dos extremos de la tabla
# que corresponda. El mecanismo no se toca.
# ---------------------------------------------------------------------------

HORIZONTE = {
    "cabeceo_max": 30.0,        # grados de cabeceo a fondo de escala
    "servo_cabeceo": 60.0,      # grados de servo desde el centro, a fondo
    "carrera_mm": 20.0,         # cuánto corre el disco a fondo de cabeceo
    "radio_perno_mm": 23.094,   # radio del perno en el brazo del servo
    "alabeo_max": 60.0,         # grados de alabeo a fondo de escala
    "dientes_plato": 70,
    "dientes_pinon": 50,
    "paso_tabla": 5,            # cada cuántos grados se tabula el cabeceo
}


def tabla_cabeceo(h=HORIZONTE):
    """Ángulos de servo que cancelan el seno del yugo escocés."""
    k = h["cabeceo_max"] / _math.sin(_math.radians(h["servo_cabeceo"]))
    paso = h["paso_tabla"]
    n = int(h["cabeceo_max"] / paso)
    return [(p * paso, round(90.0 + _math.degrees(_math.asin(p * paso / k)), 2))
            for p in range(-n, n + 1)]


def tabla_alabeo(h=HORIZONTE):
    """Tres puntos alcanzan: un par de engranajes es exactamente lineal."""
    rel = h["dientes_plato"] / float(h["dientes_pinon"])
    tope = round(h["alabeo_max"] * rel, 2)
    return [(-h["alabeo_max"], 90.0 - tope),
            (0.0, 90.0),
            (h["alabeo_max"], 90.0 + tope)]
