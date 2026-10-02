# -*- coding: utf-8 -*-
"""Mecánica de las agujas: barrido, engranajes y el mecanismo del horizonte.

Por qué cada número es el que es, y qué pasa si se cambia: docs/mecanica.md.
"""

import math as _math

# Grados que recorre la aguja de cada instrumento en su esfera. Hasta 180 el servo
# mueve la aguja directo; por encima, un par de engranajes multiplica barrido/180.
# Las carátulas impresas están dibujadas con estos valores: cambiar uno obliga a
# rehacerlas a mano (no hay un programa que lo haga) y, a veces, a imprimir otro par.
BARRIDO = {
    # vuelo, bocas de 78 mm
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

    # combustible y culata, bocas de 58 mm
    "FUEL_QTY_FWD":   120,   # aforador de flotante: arco corto
    "FUEL_QTY_AFT":   120,
    "CHT":            270,   # termómetro de culata

    # motor, transmisión y eléctricos, bocas de 48 mm
    "OIL_TEMP":       270,
    "OIL_PRESS":      270,
    "FUEL_PRESS":     270,
    "CARB_AIR_TEMP":  270,
    "XMSN_OIL_TEMP":  270,
    "XMSN_OIL_PRESS": 270,
    "AMMETER":        120,   # amperímetro de aguja central, arco corto
    "VOLTMETER":      120,

    # las dos bocas de 122 mm
    "COMPASS":       "CONT", # la rosa da la vuelta entera, motor continuo
    "ATT_PITCH":     "MEC",  # el horizonte tiene su propio mecanismo
    "ATT_ROLL":      "MEC",
}

# Medio de la escala en ángulo de dibujo (matemático: 90 es arriba). Las escalas
# se centran arriba salvo el variómetro, que tiene el cero a las 9 como el real.
# Con esto están dibujadas las carátulas impresas y la página.
CENTRO_ESCALA = {
    "VSI": 180.0,
}

# relación -> dientes (servo, aguja). Módulo 0,5 con 24 dientes en la aguja: es lo
# que entra en las bocas de 48 mm y todavía sale limpio en una impresora de filamento.
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
    """True si hay un par de engranajes entre servo y aguja: el par invierte el giro.

    Pasa en los instrumentos con reducción y en el alabeo del horizonte.
    """
    return reduccion(id_instrumento) > 1.0 or id_instrumento == "ATT_ROLL"


def factor_servo(id_instrumento):
    """De ángulo de la tabla cal (escrita en 0..180) a ángulo del servo.

    Con barrido <= 180 el servo recorre justo el barrido; por encima, recorre 180
    y los engranajes hacen el resto.
    """
    b = BARRIDO.get(id_instrumento)
    if not isinstance(b, (int, float)):
        return 1.0
    return (b / 180.0) / reduccion(id_instrumento)


# Horizonte artificial: el cabeceo va por un yugo escocés (carrera = r·sen θ, que la
# tabla cancela) y el alabeo por un plato 70/50 que invierte el giro. Las dos tablas
# se calculan de estas medidas; la mecánica y el sentido de giro, en docs/mecanica.md.
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
    """Ángulos de servo que cancelan el seno del yugo: θ = arcsen(cabeceo / 34,641).

    Trece puntos dejan un error de 0,2° de cabeceo; con tres llegaba a 2,4°.
    """
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
