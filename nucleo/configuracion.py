# -*- coding: utf-8 -*-
"""
configuracion.py - datos de la aeronave y definición del tablero
=================================================================
Sikorsky S-55 / H-19A Chickasaw - matrícula H-08 (Fuerza Aérea Argentina)
Proyecto H-08 · EEST N° 7 - Taller Regional Quilmes

Todo dato numérico del proyecto vive en este archivo: límites de la
aeronave, instrumentos, canales de las placas, pines de los motores y
geometría de la página web. Ningún otro módulo tiene constantes propias, así
que el tablero se recalibra editando este archivo, sin tocar la lógica.

--------------------------------------------------------------------------
FICHA DE LA CÉLULA H-08
--------------------------------------------------------------------------
Modelo ............ Sikorsky H-19A Chickasaw (S-55)
Número de serie ... c/n 55-135  (ex USAF 51-3873)
Operador .......... Fuerza Aérea Argentina, 1962 - 1968
Motor ............. Pratt & Whitney R-1340-57 "Wasp", radial 9 cilindros
                    600 HP a 2250 RPM (despegue) / 550 HP a 2200 RPM (continuo)
Rotor principal ... 3 palas, 16,15 m de diámetro
RPM de rotor ...... 170 a 245 RPM (operación normal ~220 RPM)
Relación reducción  10:1 (2200 RPM motor -> 220 RPM rotor)
Combustible ....... Tanque delantero 378 L + tanque trasero 322 L = 700 L
Sistema eléctrico . 24 V CC, generador de 200 A
Vne ............... 176 km/h (95 kt) a nivel del mar
Crucero ........... 137 km/h (74 kt)
Destino final ..... Preservado como material didáctico en el
                    Area Material Quilmes / Taller Regional Quilmes
--------------------------------------------------------------------------

LA RELACIÓN 10:1 Y EL TACÓMETRO DOBLE
El tacómetro doble del S-55 tiene DOS agujas concéntricas: la escala de motor
llega a 3500 RPM y la de rotor a 350 RPM. Como la reducción es 10:1, cuando el
embrague está acoplado y el motor arrastra al rotor las dos agujas quedan
SUPERPUESTAS. Si el motor falla, la rueda libre desacopla y las agujas se
SEPARAN ("needle split"): el rotor sigue girando por autorrotación mientras
la aguja de motor cae. Es uno de los detalles más didácticos del simulador.
"""

# ===========================================================================
# 1. IDENTIDAD DE LA AERONAVE (se muestra en la página web)
# ===========================================================================
AERONAVE = {
    "modelo": "Sikorsky H-19A Chickasaw (S-55)",
    "matricula": "H-08",
    "serie": "c/n 55-135 (ex USAF 51-3873)",
    "operador": "Fuerza Aérea Argentina",
    "servicio": "1962 - 1968",
    "motor": "Pratt & Whitney R-1340-57 Wasp, 600 HP",
    "referencia": "T.O. 1H-19A-1",
    "preservacion": "Taller Regional Quilmes",
}

# ===========================================================================
# 2. LÍMITES Y CONSTANTES FÍSICAS DEL H-19A
# ===========================================================================
LIM = {
    # --- Motor ---
    "rpm_motor_ralenti": 1400.0,
    "rpm_motor_crucero": 2200.0,
    "rpm_motor_despegue": 2250.0,
    "rpm_motor_max": 2400.0,
    "rpm_motor_escala": 3500.0,       # fondo de escala del tacómetro
    "rpm_arranque_corte": 600.0,      # por debajo de esto el motor no sostiene

    # --- Rotor ---
    "rpm_rotor_min": 170.0,           # arco rojo inferior
    "rpm_rotor_nom": 220.0,
    "rpm_rotor_max": 245.0,           # arco rojo superior
    "rpm_rotor_escala": 350.0,
    "reduccion": 10.0,                # motor:rotor

    # --- Presión de admisión (motor sobrealimentado) ---
    # El manómetro de admisión es ABSOLUTO, no diferencial. Con el motor
    # parado no marca cero: marca la presión barométrica del campo, unas
    # 29,9 inHg a nivel del mar. Al poner el motor en marcha la aguja BAJA,
    # porque la mariposa cerrada genera depresión en el colector.
    "map_ambiente": 29.92,            # inHg, atmósfera estándar a nivel del mar
    "map_min": 10.0,                  # fondo de escala del instrumento
    "map_ralenti": 13.0,              # mariposa cerrada, 1400 RPM
    "map_crucero": 29.0,
    "map_despegue": 36.5,             # R-1340-57 a 2250 RPM
    "map_max": 38.0,                  # línea roja
    "map_escala": 50.0,

    # --- Aceite de motor ---
    "oil_p_min": 25.0,                # psi, mínimo en ralenti
    "oil_p_nom": 80.0,
    "oil_p_max": 100.0,
    "oil_p_escala": 150.0,
    "oil_t_nom": 70.0,                # C
    "oil_t_min_despegue": 40.0,       # no se despega con el aceite más frío
    "oil_t_max": 85.0,
    "oil_t_escala": 100.0,

    # --- Cabeza de cilindro ---
    # El límite absoluto del R-1340 son 260 C (500 F). En tierra, con el
    # helicóptero quieto y sin viento relativo, la recomendación es no pasar
    # de 232 C (450 F): sin traslación el radial se recalienta rápido, y es
    # la limitación operativa clásica del tipo.
    "cht_nom": 200.0,                 # C
    "cht_tierra_max": 232.0,          # 450 F, límite en tierra
    "cht_max": 260.0,                 # 500 F, límite absoluto
    "cht_escala": 350.0,

    # --- Carburador ---
    "cat_nom": 15.0,                  # C
    "cat_hielo_min": -10.0,           # banda de riesgo de engelamiento
    "cat_hielo_max": 15.0,

    # --- Combustible ---
    "fuel_p_nom": 16.0,               # psi
    "fuel_p_min": 12.0,
    "fuel_p_escala": 25.0,
    "cap_fwd": 378.0,                 # litros
    "cap_aft": 322.0,
    "aviso_fuel_l": 45.0,             # nivel que enciende la luz ámbar
    "consumo_max_lph": 155.0,         # a potencia de despegue
    "consumo_min_lph": 22.0,          # ralenti

    # --- Transmisión principal ---
    "xmsn_p_nom": 55.0,               # psi
    "xmsn_p_min": 30.0,
    "xmsn_p_escala": 100.0,
    "xmsn_t_nom": 85.0,               # C
    "xmsn_t_max": 110.0,
    "xmsn_t_escala": 150.0,

    # --- Sistema eléctrico ---
    "bus_bateria": 24.0,              # V con generador fuera de línea
    "bus_generador": 28.0,            # V con generador en línea
    "bus_min_util": 20.0,             # por debajo los instrumentos eléctricos mueren
    "amp_escala": 200.0,
    "amp_carga_max": 120.0,
    # Aceleración didáctica de la carga y descarga de la batería: una batería
    # real tarda una hora en descargarse, y eso no se puede mostrar en clase.
    "factor_bateria": 8.0,

    # --- Vuelo ---
    "vne_kt": 95.0,
    "v_crucero_kt": 74.0,
    "v_escala_kt": 120.0,
    "vs_escala_fpm": 2000.0,
    "alt_escala_ft": 10000.0,
    "techo_ft": 10500.0,
    "viraje_estandar_dps": 3.0,       # 3 grados/s = viraje de 2 minutos

    # --- Ambiente por defecto (ISA a nivel del mar) ---
    "oat_c": 15.0,
    "qnh_hpa": 1013.0,
}

# ===========================================================================
# 3. TIPOS DE ACTUADOR
# ===========================================================================
SERVO = "SERVO"          # servo de 180 grados sobre una placa PCA9685
MOTOR = "MOTOR"          # paso a paso 28BYJ-48 de giro continuo, con plaquita ULN2003
LED = "LED"              # luz de alerta, encendida o apagada, sobre PCA9685

# ===========================================================================
# 4. DEFINICIÓN DEL TABLERO
# ===========================================================================
# Cada entrada describe UN actuador físico. Los campos son:
#
#   n         : número del instrumento en la lista de 33 del anteproyecto
#   nombre    : denominación en castellano
#   en        : denominación original en inglés
#   senal     : variable del modelo de vuelo que lo alimenta
#   unidad    : unidad de ingeniería
#   escala    : (mínimo, máximo) de la esfera del instrumento
#   arcos     : lista de (desde, hasta, color) para dibujar la página web
#   actuador  : SERVO | MOTOR | LED
#   cal       : tabla [(valor, ángulo_actuador)], ver utiles.interpolar_tabla
#   tau       : constante de tiempo de la aguja en segundos (inercia)
#   slew      : velocidad máxima de la aguja en grados/segundo
#   canal     : (placa, canal) donde está conectado: ("PCA0", 7), ("MOTOR", 1)
#
# El campo 'cal' hace que el tablero sea calibrable: para ajustar un
# instrumento se corrige su tabla, no el código.
# ===========================================================================

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
import math as _math

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


def _tabla_cabeceo(h=HORIZONTE):
    """Ángulos de servo que cancelan el seno del yugo escocés."""
    k = h["cabeceo_max"] / _math.sin(_math.radians(h["servo_cabeceo"]))
    paso = h["paso_tabla"]
    n = int(h["cabeceo_max"] / paso)
    return [(p * paso, round(90.0 + _math.degrees(_math.asin(p * paso / k)), 2))
            for p in range(-n, n + 1)]


def _tabla_alabeo(h=HORIZONTE):
    """Tres puntos alcanzan: un par de engranajes es exactamente lineal."""
    rel = h["dientes_plato"] / float(h["dientes_pinon"])
    tope = round(h["alabeo_max"] * rel, 2)
    return [(-h["alabeo_max"], 90.0 - tope),
            (0.0, 90.0),
            (h["alabeo_max"], 90.0 + tope)]


TABLERO = [

    # -----------------------------------------------------------------------
    # GRUPO MOTOPROPULSOR
    # -----------------------------------------------------------------------
    {
        "id": "FUEL_QTY_FWD", "n": 2,
        "nombre": "Cantidad de combustible - tanque delantero",
        "en": "Fuel Quantity Gage - Fwd Tank",
        "senal": "fuel_fwd_l", "unidad": "L", "escala": (0.0, 378.0),
        "arcos": [(0, 45, "rojo"), (45, 378, "verde")],
        "actuador": SERVO, "tau": 1.2, "slew": 60.0,
        # Aforador no lineal: la parte baja del tanque tiene más resolución.
        "cal": [(0, 0), (45, 30), (95, 60), (190, 105), (285, 145), (378, 180)],
        "canal": ("PCA0", 0),
    },
    {
        "id": "OIL_TEMP", "n": 3,
        "nombre": "Temperatura de aceite de motor",
        "en": "Engine Oil Temperature Gage",
        "senal": "oil_t_c", "unidad": "C", "escala": (0.0, 100.0),
        "arcos": [(0, 40, "amarillo"), (40, 85, "verde"), (85, 100, "rojo")],
        "actuador": SERVO, "tau": 2.0, "slew": 45.0,
        "cal": [(0, 0), (40, 60), (70, 110), (85, 145), (100, 180)],
        "canal": ("PCA0", 1),
    },
    {
        "id": "OIL_PRESS", "n": 4,
        "nombre": "Presión de aceite de motor",
        "en": "Engine Oil Pressure Gage",
        "senal": "oil_p_psi", "unidad": "psi", "escala": (0.0, 150.0),
        "arcos": [(0, 25, "rojo"), (25, 100, "verde"), (100, 150, "rojo")],
        "actuador": SERVO, "tau": 0.4, "slew": 240.0,
        "cal": [(0, 0), (25, 40), (80, 110), (100, 135), (150, 180)],
        "canal": ("PCA0", 2),
    },
    {
        "id": "FUEL_PRESS", "n": 5,
        "nombre": "Presión de combustible",
        "en": "Fuel Pressure Gage",
        "senal": "fuel_p_psi", "unidad": "psi", "escala": (0.0, 25.0),
        "arcos": [(0, 12, "rojo"), (12, 20, "verde"), (20, 25, "amarillo")],
        "actuador": SERVO, "tau": 0.5, "slew": 200.0,
        "cal": [(0, 0), (12, 80), (16, 115), (20, 145), (25, 180)],
        "canal": ("PCA0", 3),
    },
    {
        "id": "CARB_AIR_TEMP", "n": 6,
        "nombre": "Temperatura de aire del carburador",
        "en": "Carburetor Air Temperature Gage",
        "senal": "cat_c", "unidad": "C", "escala": (-50.0, 50.0),
        "arcos": [(-50, -10, "verde"), (-10, 15, "amarillo"), (15, 50, "verde")],
        "actuador": SERVO, "tau": 1.5, "slew": 60.0,
        "cal": [(-50, 0), (-10, 65), (0, 90), (15, 118), (50, 180)],
        "canal": ("PCA0", 4),
    },
    {
        "id": "CHT", "n": 7,
        "nombre": "Temperatura de cabeza de cilindro",
        "en": "Cylinder Head Temperature Gage",
        "senal": "cht_c", "unidad": "C", "escala": (0.0, 350.0),
        "arcos": [(0, 120, "amarillo"), (120, 232, "verde"), (232, 350, "rojo")],
        "actuador": SERVO, "tau": 3.0, "slew": 45.0,
        "cal": [(0, 0), (120, 55), (200, 100), (232, 125), (260, 145), (350, 180)],
        "canal": ("PCA0", 5),
    },

    # -----------------------------------------------------------------------
    # INSTRUMENTOS DE VUELO
    # -----------------------------------------------------------------------
    {
        "id": "AIRSPEED", "n": 10,
        "nombre": "Velocímetro",
        "en": "Airspeed Indicator",
        "senal": "ias_kt", "unidad": "kt", "escala": (0.0, 120.0),
        "arcos": [(0, 20, "amarillo"), (20, 95, "verde"), (95, 120, "rojo")],
        "actuador": SERVO, "tau": 0.7, "slew": 120.0,
        # No lineal: la presión dinámica va con V², por eso el extremo bajo
        # de la esfera está comprimido.
        "cal": [(0, 0), (20, 18), (40, 52), (60, 88), (80, 125), (95, 150), (120, 180)],
        "canal": ("PCA0", 6),
    },
    {
        "id": "TACH_ENG", "n": 11,
        "nombre": "Tacómetro doble - aguja de MOTOR",
        "en": "Dual Tachometer - Engine needle",
        "senal": "n_eng_rpm", "unidad": "RPM", "escala": (0.0, 3500.0),
        "arcos": [(0, 1200, "amarillo"), (1200, 2250, "verde"), (2250, 3500, "rojo")],
        "actuador": SERVO, "tau": 0.35, "slew": 300.0,
        "cal": [(0, 0), (1000, 51), (2000, 103), (2200, 113), (2400, 123), (3500, 180)],
        "canal": ("PCA0", 7),
    },
    {
        "id": "TACH_ROT", "n": 11,
        "nombre": "Tacómetro doble - aguja de ROTOR",
        "en": "Dual Tachometer - Rotor needle",
        "senal": "n_rot_rpm", "unidad": "RPM", "escala": (0.0, 350.0),
        "arcos": [(0, 170, "rojo"), (170, 245, "verde"), (245, 350, "rojo")],
        "actuador": SERVO, "tau": 0.35, "slew": 300.0,
        # La misma tabla dividida por 10: las agujas se superponen a 10:1.
        "cal": [(0, 0), (100, 51), (200, 103), (220, 113), (240, 123), (350, 180)],
        # Sólo en la página web: en el tablero cada instrumento lleva UN servo
        # y el tacómetro físico muestra la aguja del motor. El rotor bajo lo
        # avisa la luz LOW ROTOR. El canal PCA0:8 queda libre.
        "canal": None,
    },
    {
        "id": "ALTIMETER", "n": 18,
        "nombre": "Altímetro (aguja de miles de pies)",
        "en": "Altimeter - thousands pointer",
        "senal": "alt_ind_ft", "unidad": "ft", "escala": (0.0, 10000.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.9, "slew": 90.0,
        "cal": [(0, 0), (2500, 45), (5000, 90), (7500, 135), (10000, 180)],
        "canal": ("PCA0", 9),
    },
    {
        "id": "ALTIMETER_100", "n": 18,
        "nombre": "Altímetro (aguja de centenas de pies)",
        "en": "Altimeter - hundreds pointer",
        "senal": "alt_centenas", "unidad": "ft", "escala": (0.0, 1000.0),
        "arcos": [],
        # Da vueltas enteras. Sólo en la página web: en el tablero el
        # altímetro lleva UN servo, con la aguja de miles (una vuelta cada
        # 10.000 pies, engranajes 2:1). El motor 0 (U1) queda libre.
        "actuador": MOTOR, "tau": 0.5, "slew": 600.0,
        "cal": [(0, 0), (1000, 360)],
        "canal": None,
    },
    {
        "id": "VSI", "n": 20,
        "nombre": "Variómetro / velocidad vertical",
        "en": "Vertical Velocity Indicator",
        "senal": "vs_ind_fpm", "unidad": "ft/min", "escala": (-2000.0, 2000.0),
        "arcos": [],
        # El variómetro real tiene un retardo propio de 6 a 9 segundos
        # (capilar + cápsula). El tau alto reproduce ese retardo.
        "actuador": SERVO, "tau": 2.5, "slew": 90.0,
        "cal": [(-2000, 0), (-1000, 40), (-500, 62), (0, 90),
                (500, 118), (1000, 140), (2000, 180)],
        "canal": ("PCA0", 10),
    },
    {
        "id": "TURN", "n": 19,
        "nombre": "Indicador de viraje (aguja)",
        "en": "Turn Indicator needle",
        "senal": "turn_rate_dps", "unidad": "deg/s", "escala": (-6.0, 6.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.6, "slew": 150.0,
        "cal": [(-6, 45), (-3, 65), (0, 90), (3, 115), (6, 135)],
        "canal": ("PCA0", 11),
    },
    {
        "id": "SLIP", "n": 19,
        "nombre": "Indicador de ladeo (bola)",
        "en": "Slip Indicator ball",
        "senal": "slip", "unidad": "g", "escala": (-1.0, 1.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.8, "slew": 150.0,
        "cal": [(-1, 55), (0, 90), (1, 125)],
        # Sólo en la página web: en el tablero el viraje lleva UN servo, el de
        # la aguja, y la bola queda impresa en el centro. PCA0:12 queda libre.
        "canal": None,
    },
    {
        "id": "ATT_PITCH", "n": 12,
        "nombre": "Horizonte artificial - cabeceo",
        "en": "Attitude Indicator - pitch",
        "senal": "pitch_ind_deg", "unidad": "deg", "escala": (-30.0, 30.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.5, "slew": 180.0,
        # Trece puntos, no tres: el yugo escocés es un seno y hay que cancelarlo.
        "cal": _tabla_cabeceo(),
        "canal": ("PCA0", 13),
    },
    {
        "id": "ATT_ROLL", "n": 12,
        "nombre": "Horizonte artificial - alabeo",
        "en": "Attitude Indicator - roll",
        "senal": "roll_ind_deg", "unidad": "deg", "escala": (-60.0, 60.0),
        "arcos": [],
        "actuador": SERVO, "tau": 0.4, "slew": 240.0,
        # Engranajes 1.4 a 1: el servo recorre +-84 para que el plato gire +-60.
        "cal": _tabla_alabeo(),
        "canal": ("PCA0", 14),
    },
    {
        "id": "COMPASS", "n": 14,
        "nombre": "Brújula giroscópica esclavizada",
        "en": "Slaved Gyro Magnetic Compass",
        "senal": "hdg_ind_deg", "unidad": "deg", "escala": (0.0, 360.0),
        "arcos": [],
        # Giro continuo: la rosa pasa por el norte y sigue.
        "actuador": MOTOR, "tau": 1.0, "slew": 180.0,
        "cal": [(0, 0), (360, 360)],
        "canal": ("MOTOR", 1),
    },
    {
        "id": "VOR_CDI", "n": 16,
        "nombre": "Indicador de rumbo del receptor AN/ARN-14",
        "en": "Range Course Indicator",
        "senal": "cdi", "unidad": "pts", "escala": (-5.0, 5.0),
        "arcos": [],
        "actuador": SERVO, "tau": 1.0, "slew": 60.0,
        "cal": [(-5, 60), (0, 90), (5, 120)],
        "canal": ("PCA0", 15),
    },

    # -----------------------------------------------------------------------
    # PRESIÓN DE ADMISIÓN, TRANSMISIÓN Y SISTEMA ELÉCTRICO
    # -----------------------------------------------------------------------
    {
        "id": "MAP", "n": 23,
        "nombre": "Presión de admisión",
        "en": "Manifold Pressure Gage",
        "senal": "map_inhg", "unidad": "inHg", "escala": (10.0, 50.0),
        # El arco verde llega hasta la presión de despegue; por encima de 38
        # es línea roja. Con el motor parado la aguja queda en 29,9 (presión
        # del campo), dentro del verde: no es una condición de falla.
        "arcos": [(10, 18, "amarillo"), (18, 36.5, "verde"), (38, 50, "rojo")],
        "actuador": SERVO, "tau": 0.3, "slew": 300.0,
        "cal": [(10, 0), (20, 45), (30, 90), (38, 126), (44, 153), (50, 180)],
        "canal": ("PCA1", 0),
    },
    {
        "id": "XMSN_OIL_TEMP", "n": 26,
        "nombre": "Temperatura de aceite de transmisión",
        "en": "Transmission Oil Temperature Gage",
        "senal": "xmsn_t_c", "unidad": "C", "escala": (0.0, 150.0),
        "arcos": [(0, 50, "amarillo"), (50, 110, "verde"), (110, 150, "rojo")],
        "actuador": SERVO, "tau": 3.5, "slew": 45.0,
        "cal": [(0, 0), (50, 60), (85, 100), (110, 130), (150, 180)],
        "canal": ("PCA1", 1),
    },
    {
        "id": "XMSN_OIL_PRESS", "n": 28,
        "nombre": "Presión de aceite de transmisión",
        "en": "Transmission Oil Pressure Gage",
        "senal": "xmsn_p_psi", "unidad": "psi", "escala": (0.0, 100.0),
        "arcos": [(0, 30, "rojo"), (30, 70, "verde"), (70, 100, "amarillo")],
        "actuador": SERVO, "tau": 0.5, "slew": 200.0,
        "cal": [(0, 0), (30, 60), (55, 100), (70, 128), (100, 180)],
        "canal": ("PCA1", 2),
    },
    {
        "id": "AMMETER", "n": 27,
        "nombre": "Amperímetro",
        "en": "Ammeter",
        "senal": "amp_a", "unidad": "A", "escala": (-50.0, 200.0),
        "arcos": [(-50, 0, "rojo"), (0, 150, "verde"), (150, 200, "amarillo")],
        "actuador": SERVO, "tau": 0.7, "slew": 150.0,
        "cal": [(-50, 20), (0, 45), (100, 120), (200, 180)],
        "canal": ("PCA1", 3),
    },
    {
        "id": "VOLTMETER", "n": 30,
        "nombre": "Voltímetro",
        "en": "Voltmeter",
        "senal": "bus_v", "unidad": "V", "escala": (0.0, 32.0),
        "arcos": [(0, 22, "rojo"), (22, 30, "verde"), (30, 32, "rojo")],
        "actuador": SERVO, "tau": 0.6, "slew": 150.0,
        # Escala expandida: los voltímetros de aeronave concentran la
        # resolución entre 20 y 30 V, que es la zona que importa.
        "cal": [(0, 0), (18, 25), (22, 60), (24, 85), (28, 130), (32, 180)],
        "canal": ("PCA1", 4),
    },
    {
        "id": "FUEL_QTY_AFT", "n": 31,
        "nombre": "Cantidad de combustible - tanque trasero",
        "en": "Fuel Quantity Gage - Aft Tank",
        "senal": "fuel_aft_l", "unidad": "L", "escala": (0.0, 322.0),
        "arcos": [(0, 45, "rojo"), (45, 322, "verde")],
        "actuador": SERVO, "tau": 1.2, "slew": 60.0,
        "cal": [(0, 0), (45, 32), (80, 62), (160, 105), (240, 145), (322, 180)],
        "canal": ("PCA1", 5),
    },

    # -----------------------------------------------------------------------
    # LUCES DE ALERTA
    # -----------------------------------------------------------------------
    {
        "id": "LT_FUEL_FWD", "n": 8,
        "nombre": "Luz de advertencia combustible delantero",
        "en": "Fuel Warning Light - Fwd Tank",
        "senal": "lt_fuel_fwd", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "ambar",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 8),
    },
    {
        "id": "LT_FUEL_AFT", "n": 9,
        "nombre": "Luz de advertencia combustible trasero",
        "en": "Fuel Warning Light - Aft Tank",
        "senal": "lt_fuel_aft", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "ambar",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 9),
    },
    {
        "id": "LT_XMSN_PRESS", "n": 24,
        "nombre": "Luz de alerta presión de aceite de transmisión",
        "en": "Transmission Oil Pressure Warning",
        "senal": "lt_xmsn", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "rojo",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 10),
    },
    {
        "id": "LT_GEN", "n": 29,
        "nombre": "Luz de advertencia del generador",
        "en": "Generator Warning Light",
        "senal": "lt_gen", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "rojo",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 11),
    },
    {
        "id": "LT_LOW_ROTOR", "n": 0,
        "nombre": "Luz de RPM de rotor bajo (agregada con fin didáctico)",
        "en": "Low Rotor RPM Warning",
        "senal": "lt_low_rotor", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "rojo",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 12),
    },
    {
        "id": "LT_STARTER", "n": 32,
        "nombre": "Luz de arranque / magnetos activos",
        "en": "Starter / Ignition Light",
        "senal": "lt_starter", "unidad": "on/off", "escala": (0.0, 1.0),
        "arcos": [], "color": "verde",
        "actuador": LED, "tau": 0.0, "slew": 0.0, "cal": [(0, 0), (1, 1)],
        "canal": ("PCA1", 13),
    },
]

# Índice por id, para buscar un instrumento sin recorrer la lista
TABLERO_POR_ID = {}
for _it in TABLERO:
    TABLERO_POR_ID[_it["id"]] = _it


# ===========================================================================
# 5. PARÁMETROS DEL LAZO DE CONTROL
# ===========================================================================
LAZO = {
    "hz_fisica": 20,      # 50 ms por paso. Un servo refresca a 50 Hz y la aguja
                          # más rápida del tablero tiene tau = 0,3 s.
    "hz_salida": 20,      # escrituras por segundo a las placas
    "hz_telemetria": 5,   # fotos de estado por segundo para la página web
    "banda_muerta": 2,    # en cuentas de 12 bits del PCA9685: un canal que
                          # cambia menos que esto no se escribe por I2C.
}

# ===========================================================================
# 6. ARRANQUE, SERVOS Y MOTORES PASO A PASO
# ===========================================================================
# ---------------------------------------------------------------------------
# ARRANQUE ESCALONADO
# ---------------------------------------------------------------------------
# Al encender, ningún servo tiene todavía un ángulo escrito, así que en la
# primera escritura se moverían todos juntos. Un servo pide unos 700 mA
# mientras arranca: todos a la vez superan cualquier fuente razonable del
# tablero y los PCA9685 se reinician por baja tensión.
#
# Liberándolos de a tandas, el pico queda en:
#     canales_por_tanda x 0,7 A
# y el tablero termina de acomodarse en:
#     cantidad_de_canales / canales_por_tanda x segundos_entre_tandas
# Con 3 y 0,25 s: unos 2,1 A de pico y menos de 2,5 segundos de arranque.
#
# Con una fuente holgada se puede subir canales_por_tanda. Si el tablero se
# reinicia al encender, hay que bajarlo.
ARRANQUE = {
    "canales_por_tanda": 3,
    "segundos_entre_tandas": 0.25,
}

# ---------------------------------------------------------------------------
# PLACAS PCA9685 (bus I2C 1 de la Raspberry Pi: GPIO2 = SDA, GPIO3 = SCL)
# ---------------------------------------------------------------------------
# La dirección se elige con los puentes A0..A5 de cada módulo. La placa 0
# queda sin puentear (0x40) y la placa 1 lleva soldado el puente A0 (0x41).
I2C_BUS = 1
PLACAS = {"PCA0": 0x40, "PCA1": 0x41}

# ---------------------------------------------------------------------------
# SERVOS
# ---------------------------------------------------------------------------
# Valores nominales de la hoja de datos del MG90S. Cada servo puede tener sus
# propios extremos medidos con calibrar_servo.py; esos quedan guardados en
# raspberry_pi5/calibracion_servos.json y reemplazan a estos sólo para ese
# canal.
SERVO_CFG = {
    "pulso_min_us": 500,    # 0 grados
    "pulso_max_us": 2500,   # 180 grados
    "barrido_deg": 180.0,
    "frecuencia_hz": 50,    # período de 20 ms: 1 cuenta del PCA9685 = 4,88 us
}

# ---------------------------------------------------------------------------
# LUCES DE ALERTA
# ---------------------------------------------------------------------------
# En la placa madre el ánodo de cada LED va a +5 V (J8) y el cátodo vuelve,
# por su resistencia de 220 ohm (R2..R7), a una salida del PCA9685 (J7). El
# PCA9685 SUMIDERA la corriente: el LED enciende cuando la salida está en
# BAJO. Por eso el programa invierte esos canales.
#
# Consecuencia práctica: al dar energía, antes de que arranque el programa,
# el PCA9685 tiene todas sus salidas en bajo y las seis luces se encienden.
# Funciona como prueba de lámparas del encendido: una luz que no prende en
# ese momento tiene el LED o el cableado cortado.
LUCES_ACTIVAS_EN_BAJO = True

# ---------------------------------------------------------------------------
# MOTORES PASO A PASO 28BYJ-48 (con su plaquita ULN2003 de fábrica)
# ---------------------------------------------------------------------------
# La reducción interna NO es 1:64 justo: es (32/9)·(22/11)·(26/9)·(31/10) =
# 63,684. En medio paso eso da 64 x 63,684 = 4075,8 pasos por vuelta del eje,
# no 4096. Con 4096 la rosa de la brújula se correría 1,8 grados por vuelta:
# después de cinco vueltas completas quedaría 9 grados corrida. Se verifica con
#     python3 probar_motor.py 1 --vueltas 10
# (después de 10 vueltas la aguja tiene que volver al mismo lugar).
MOTOR_CFG = {
    "pasos_por_vuelta": 4075.77,  # medio paso: 0,088 grados por paso
    "vel_max_pps": 900,           # unas 13 vueltas por minuto
    "vel_arranque_pps": 200,      # velocidad desde la que arranca sin perder pasos
    "aceleracion": 2000,          # pasos por segundo al cuadrado
    "soltar_tras_s": 0.5,         # quieto este tiempo, se cortan las bobinas
}

# Un motor por instrumento de giro continuo: queda uno solo, la brújula,
# porque en el tablero cada instrumento de aguja lleva un servo. 'pines' son
# los GPIO (numeración BCM) que van a IN1, IN2, IN3 e IN4 de la plaquita, en
# ese orden; son los que la placa madre lleva a las patas 1 a 4 de U2. El
# lugar de U1 (motor 0, GPIO 6-13-19-26) queda libre en la placa.
#
# 'sentido' es +1 o -1 y se ajusta en la puesta en marcha con probar_motor.py.
# La rosa de la brújula está PEGADA (fija) y el motor mueve una AGUJA de 47 mm:
# pidiendo 90 grados la aguja tiene que quedar apuntando a la E, o sea que
# gira como las agujas del reloj. Es al revés que cuando giraba la rosa, por
# eso el signo cambió de -1 a +1. Si en el banco va para el otro lado, se
# cambia acá y nada más.
MOTORES = {
    1: {"id": "COMPASS", "pines": (12, 16, 20, 21), "sentido": 1},
}


# ===========================================================================
# 7. GEOMETRÍA DEL TABLERO Y DESCRIPCIONES
# ===========================================================================
# Estos datos NO los usa la simulación: los usa el panel visual de la aplicación web
# para dibujar el tablero y para explicar cada instrumento.
#
# DE DONDE SALE CADA COSA
# --------------------------------------------------------------------------
# La DISPOSICIÓN (que va a la izquierda, que al centro, que arriba a la
# derecha, el tamaño relativo de cada instrumento) está copiada de la
# fotografía de cabina de un S-55 aportada para el proyecto. La foto se usa
# como referencia de UBICACIÓN.
#
# El CONTENIDO de cada instrumento -que mide, en que unidad, con que escala,
# con que arcos de color y en qué canal del PCA9685 va- NO sale de la foto:
# sale del reporte de aviónica del H-08 y del manual T.O. 1H-19A-1. Por eso
# el tablero dibujado tiene los 21 instrumentos del proyecto aunque en la
# foto se distingan menos.
#
# Donde la foto y el reporte no coinciden manda el reporte, porque no esta
# confirmado que la fotografía sea de esta misma célula.
# --------------------------------------------------------------------------
#
# CAMPOS
#   desc  : para qué sirve, tomado del reporte de aviónica del H-08
#   zona  : agrupador según la columna "UBICACIÓN EN CABINA" del reporte
#   dial  : que tipo de esfera hay que dibujar
#   pos   : (x, y) de la esquina superior izquierda, en el lienzo del panel
#   tam   : diámetro en unidades del lienzo, PROPORCIONAL a la boca real del
#           tablero (1,79 unidades por mm). Bocas medidas en la chapa del H-08:
#               122 mm x 2  ->  218    horizonte artificial y brújula
#                78 mm x 7  ->  140    velocímetro, altímetro, variómetro,
#                                      viraje, tacómetro, admisión, AN/ARN-14
#                58 mm x 3  ->  104    los dos aforadores y culata
#                48 mm x 9  ->   86    los otros seis de motor y transmisión,
#                                      amperímetro, voltímetro y reloj
#
# Tipos de esfera:
#   "aguja"     esfera redonda común con una aguja
#   "tacometro" dos agujas concéntricas con dos escalas (motor y rotor)
#   "altimetro" tres agujas: decenas de miles, miles y centenas de pies
#   "horizonte" horizonte artificial
#   "viraje"    aguja de viraje + bola de ladeo
#   "brujula"   tarjeta giratoria bajo línea de fe
#   "cdi"       aguja vertical de desvio de radial
#   "reloj"     tres agujas de reloj
#   "luz"       anunciador rectangular
# ===========================================================================

# Lienzo de referencia. La app escala este lienzo para que entre en la
# ventana, así que estos números son unidades de diseño, no pixeles fijos.
PANEL_LIENZO = (1340, 680)

# --- Las cinco regiones físicas del tablero, tal como se ven en la foto ----
#   estilo "verde"   : chapa estructural pintada de verde militar
#   estilo "negro"   : sub-panel negro atornillado sobre la estructura
#   estilo "consola" : consola de radio bajo el tablero
PANEL_ZONAS = [
    {"id": "SW",   "estilo": "verde", "pos": (10, 10),   "tam": (292, 452),
     "titulo": "CONMUTADORES  ·  BATERÍA Y LUCES"},
    {"id": "MOT",  "estilo": "verde", "pos": (312, 10),  "tam": (326, 660),
     "titulo": "MOTOR  ·  TRANSMISIÓN  ·  COMBUSTIBLE"},
    {"id": "FLT",  "estilo": "negro", "pos": (648, 10),  "tam": (682, 660),
     "titulo": "INSTRUMENTOS DE VUELO",
     "chapa": "FLIGHT PANEL"},
]

PANEL = {
    # ---- Columna de motor, transmisión y combustible (bocas de 48 y 58) --
    "AMMETER":         {"zona": "MOTOR",  "dial": "aguja",     "pos": (327, 551),  "tam": 86,
                        "desc": "Muestra la corriente eléctrica de carga o descarga de la "
                                "batería. Negativo significa que la batería se está gastando."},
    "VOLTMETER":       {"zona": "MOTOR",  "dial": "aguja",     "pos": (439, 551), "tam": 86,
                        "desc": "Monitorea la tensión del barra eléctrica: 24 V con batería "
                                "sola, 28 V con el generador en línea."},

    "MAP":             {"zona": "VUELO", "dial": "aguja",     "pos": (1005, 452),  "tam": 140,
                        "desc": "Presión de admisión. Es la medida directa de la "
                                "POTENCIA que está entregando el motor."},
    "OIL_PRESS":       {"zona": "MOTOR", "dial": "aguja",     "pos": (327, 41),  "tam": 86,
                        "desc": "Mide la presión de lubricación del motor. Es el instrumento "
                                "que primero avisa que un motor a pistón se está muriendo."},
    "OIL_TEMP":        {"zona": "MOTOR", "dial": "aguja",     "pos": (439, 41), "tam": 86,
                        "desc": "Monitorea la temperatura del aceite lubricante del motor "
                                "principal. Sube despacio: es una tendencia, no un evento."},
    "CHT":             {"zona": "MOTOR", "dial": "aguja",     "pos": (320, 136), "tam": 104,
                        "desc": "Temperatura de cabeza de cilindro. Crucial para evitar el "
                                "sobrecalentamiento del motor radial a pistón."},
    "FUEL_PRESS":      {"zona": "MOTOR", "dial": "aguja",     "pos": (439, 143), "tam": 86,
                        "desc": "Mide la presión del combustible suministrado al carburador. "
                                "Sin ella el motor no arranca ni se sostiene."},
    "CARB_AIR_TEMP":   {"zona": "MOTOR", "dial": "aguja",     "pos": (327, 245), "tam": 86,
                        "desc": "Temperatura del aire en el carburador. Permite monitorear y "
                                "prevenir la formación de hielo en la inducción."},
    "XMSN_OIL_PRESS":  {"zona": "MOTOR", "dial": "aguja",     "pos": (327, 347), "tam": 86,
                        "desc": "Lectura en tiempo real de la presión en la caja de "
                                "transmisión principal. Su bomba la mueve el rotor."},
    "XMSN_OIL_TEMP":   {"zona": "MOTOR", "dial": "aguja",     "pos": (439, 347), "tam": 86,
                        "desc": "Monitorea que la transmisión principal no sufra "
                                "sobrecalentamiento."},
    "FUEL_QTY_FWD":    {"zona": "MOTOR", "dial": "aguja",     "pos": (320, 440), "tam": 104,
                        "desc": "Nivel de combustible disponible en el tanque delantero "
                                "(378 litros de capacidad)."},
    "FUEL_QTY_AFT":    {"zona": "MOTOR", "dial": "aguja",     "pos": (432, 440), "tam": 104,
                        "desc": "Nivel de combustible disponible en el tanque trasero "
                                "(322 litros de capacidad)."},

    # ---- Sub-panel negro de vuelo (bocas de 78 y 122) ----------------------
    # Arriba: velocímetro y los dos instrumentos grandes. En el medio:
    # altímetro, tacómetro, viraje y AN/ARN-14. Abajo: variómetro, la luz
    # LOW ROTOR bajo el tacómetro que vigila, y la presión de admisión.
    "AIRSPEED":        {"zona": "VUELO", "dial": "aguja",     "pos": (662, 30),  "tam": 140,
                        "desc": "Indica la velocidad del helicóptero respecto al aire. "
                                "Vne del H-19A: 95 nudos. Es un instrumento NEUMÁTICO: "
                                "sigue funcionando sin energía eléctrica."},
    "ATT_ROLL":        {"zona": "VUELO", "dial": "horizonte", "pos": (841, 30),  "tam": 218,
                        "desc": "Horizonte artificial. Instrumento giroscópico que muestra la "
                                "orientación en cabeceo y alabeo respecto del horizonte real."},
    "ALTIMETER":       {"zona": "VUELO", "dial": "altimetro", "pos": (662, 276),  "tam": 140,
                        "desc": "Mide la altitud barométrica mediante presión estática. "
                                "Aguja larga: centenas de pies. Aguja corta: miles."},
    "TURN":            {"zona": "VUELO", "dial": "viraje",    "pos": (1005, 276), "tam": 140,
                        "desc": "Indicador de viraje y ladeo. La aguja muestra el régimen de "
                                "giro; la bola, si el viraje está coordinado."},
    "TACH_ENG":        {"zona": "VUELO", "dial": "tacometro", "pos": (833, 276), "tam": 140,
                        "desc": "Tacómetro DOBLE. Aguja blanca: RPM del motor (escala x100). "
                                "Aguja naranja: RPM del rotor. Con el embrague acoplado la "
                                "relación es 10:1 y las agujas quedan SUPERPUESTAS. Si se "
                                "separan, la rueda libre desacopló: autorrotación."},
    "VSI":             {"zona": "VUELO", "dial": "aguja",     "pos": (662, 452), "tam": 140,
                        "desc": "Variómetro. Indica la tasa de ascenso o descenso en pies por "
                                "minuto. Tiene un retardo propio de varios segundos."},

    "COMPASS":         {"zona": "VUELO", "dial": "brujula",   "pos": (1098, 30), "tam": 218,
                        "desc": "Brújula giroscópica esclavizada. Proporciona el rumbo "
                                "magnético estabilizado del helicóptero."},
    "CLOCK":           {"zona": "MOTOR", "dial": "reloj",     "pos": (439, 245), "tam": 86,
                        "desc": "Reloj de cabina. Cronometraje para navegación, estimación de "
                                "tiempo y control de vuelo."},
    "VOR_CDI":         {"zona": "VUELO",   "dial": "cdi",       "pos": (1176, 276), "tam": 140,
                        "desc": "Indicador de rumbo del receptor AN/ARN-14. Radionavegación: "
                                "la aguja vertical muestra el desvio respecto del radial."},
}

# --- Instrumentos que se dibujan pero NO llevan actuador -------------------
# El reloj de cabina del H-19A es mecánico: se le da cuerda, no se le manda
# una señal. Ocupa un agujero del tablero y hay que dibujarlo para que el
# panel se vea completo, pero no consume ningún canal del PCA9685.
PANEL_VIRTUAL = [
    {"id": "CLOCK", "n": 21, "nombre": "Reloj de cabina",
     "en": "Cockpit clock, 8-day mechanical",
     "unidad": "h:mm:ss", "escala": (0.0, 43200.0), "arcos": [],
     "actuador": "MECANICO", "senal": "t_sim", "cal": []},
]

# --- Luces de alerta, en el orden en que van en el anunciador --------------
ANUNCIADOR = [
    {"id": "LT_FUEL_FWD", "pos": (546, 452), "tam": (88, 22),    "leyenda": "FUEL FWD",   "color": "ambar",
     "desc": "Bajo nivel de combustible en el tanque DELANTERO. Se enciende por debajo "
             "de 45 litros. Hay que cambiar de tanque."},
    {"id": "LT_FUEL_AFT", "pos": (546, 480), "tam": (88, 22),    "leyenda": "FUEL AFT",   "color": "ambar",
     "desc": "Bajo nivel de combustible en el tanque TRASERO. Mismo umbral de 45 litros."},
    {"id": "LT_XMSN_PRESS", "pos": (546, 372), "tam": (88, 22),  "leyenda": "XMSN PRESS", "color": "rojo",
     "desc": "Baja presión de aceite en la caja de transmisión del rotor principal. Es la "
             "falla más peligrosa de un helicóptero: la autorrotación NO salva una "
             "transmisión agarrotada. Aterrizar cuanto antes."},
    {"id": "LT_GEN", "pos": (546, 576), "tam": (88, 22),         "leyenda": "GENERATOR",  "color": "rojo",
     "desc": "El generador principal dejó de suministrar energía. El avión queda "
             "alimentado solo por batería, con autonomía limitada."},
    {"id": "LT_LOW_ROTOR", "pos": (833, 510), "tam": (140, 24),   "leyenda": "LOW ROTOR",  "color": "rojo",
     "desc": "Régimen de rotor por debajo de 170. El empuje va con el CUADRADO de las RPM: "
             "por debajo del límite el rotor ya no sostiene la aeronave. Colectivo abajo."},
    {"id": "LT_STARTER", "pos": (546, 76), "tam": (88, 22),     "leyenda": "IGNITION",   "color": "verde",
     "desc": "Magnetos activos. Indica que el circuito de encendido está energizado."},
]

# ===========================================================================
# 7b. PANEL DE CONMUTADORES
# ===========================================================================
# El tablero real del H-08 tiene, en su cuarto izquierdo, una chapa llena de
# llaves, disyuntores y dos llaves con guarda roja. En el tablero físico esos
# mandos van a quedar DECORATIVOS -no se cablean-, pero en la aplicación se dibujan
# y se ANIMAN a partir del estado del simulador: cuando el programa energiza
# la batería, la palanca de batería sube sola.
#
# Es la forma de mostrar, sin tocar nada, que hace el piloto virtual en cada
# fase del vuelo.
#
# CAMPOS
#   tipo    "placa"     chapa de identificación grabada
#           "rotulo"    texto de grupo, grabado sobre la pintura
#           "palanca"   llave a palanca de dos posiciones
#           "guarda"    llave con tapa de seguridad roja
#           "rotativo"  selector rotativo de varias posiciones
#           "disyuntor" disyuntor térmico redondo (salta hacia afuera)
#           "nota"      placa de texto explicativo
#   señal   que campo del estado lo mueve (ver resolver en la app)
#   inv     True si la llave está arriba cuando la señal es False
# ===========================================================================
PANEL_CONMUTADORES = [
    {"tipo": "placa",  "pos": (20, 20),  "tam": (272, 22),
     "texto": "MAIN SWITCH PANEL", "sub": "H-19A"},

    {"tipo": "rotulo", "pos": (20, 48),  "tam": (272, 12), "texto": "ENERGÍA ELÉCTRICA"},
    {"tipo": "palanca", "id": "SW_BATT",  "pos": (20, 62),  "tam": (66, 80),
     "rot": "BATTERY", "sub": "24 V",   "senal": "bateria",
     "desc": "Llave general de batería. Es la primera que se toca en el arranque y la "
             "última en el corte. Sin ella no hay barra eléctrica."},
    {"tipo": "palanca", "id": "SW_GEN",   "pos": (88, 62),  "tam": (66, 80),
     "rot": "GENERATOR", "sub": "200 A", "senal": "generador",
     "desc": "Conecta el generador a la barra. Entra en línea recien cuando el motor pasa "
             "las 1000 RPM: por debajo de esa velocidad no genera tensión suficiente."},
    {"tipo": "palanca", "id": "SW_INV",   "pos": (156, 62), "tam": (66, 80),
     "rot": "INVERTER", "sub": "115 V CA", "senal": "energia",
     "desc": "Inversor de corriente alterna. Alimenta los giroscopos del horizonte "
             "artificial y de la brújula. Sigue a la barra principal."},
    {"tipo": "palanca", "id": "SW_PITOT", "pos": (224, 62), "tam": (66, 80),
     "rot": "PITOT HT", "sub": "ANTIHIELO", "senal": "bateria",
     "desc": "Calefacción del tubo pitot. Evita que se tape con hielo y deje al "
             "velocímetro sin presión dinámica."},

    {"tipo": "rotulo", "pos": (20, 150), "tam": (272, 12), "texto": "ENCENDIDO Y COMBUSTIBLE"},
    {"tipo": "rotativo", "id": "SEL_MAG", "pos": (20, 164), "tam": (88, 78),
     "rot": "IGNITION", "senal": "magnetos",
     "opciones": [["OFF", 0], ["L", 1], ["R", 2], ["BOTH", 3]],
     "desc": "Selector de magnetos. En la prueba de run-up se pasa a L y a R para "
             "verificar que cada magneto sostiene el motor por si solo. La caida "
             "normal de RPM al aislar uno es de 50 a 100 RPM."},
    {"tipo": "guarda", "id": "SW_START", "pos": (114, 164), "tam": (88, 78),
     "rot": "STARTER", "sub": "ARRANQUE", "senal": "arrancador",
     "desc": "Llave de arranque, protegida con guarda roja para que no se accione por "
             "error. Mueve el motor con energía de batería hasta que enciende solo."},
    {"tipo": "rotativo", "id": "SEL_TANQUE", "pos": (208, 164), "tam": (84, 78),
     "rot": "FUEL SEL", "senal": "tanque",
     "opciones": [["DEL", 0], ["AMB", 2], ["TRA", 1]],
     "desc": "Selector de tanque: delantero (378 L), ambos, o trasero (322 L). Una mala "
             "gestión de este selector es una causa clásica de corte de motor con "
             "combustible todavía a bordo."},

    {"tipo": "rotulo", "pos": (20, 250), "tam": (272, 12), "texto": "BOMBAS Y LUCES"},
    {"tipo": "palanca", "id": "SW_PUMP",  "pos": (20, 264),  "tam": (66, 78),
     "rot": "FUEL PUMP", "sub": "AUXILIAR", "senal": "bomba",
     "desc": "Bomba eléctrica auxiliar de combustible. Respalda a la bomba mecánica "
             "del motor y se usa siempre en arranque, despegue y aterrizaje."},
    {"tipo": "palanca", "id": "SW_PANEL", "pos": (88, 264),  "tam": (66, 78),
     "rot": "PANEL LT", "sub": "TABLERO", "senal": "luces",
     "desc": "Iluminación del tablero. El piloto virtual la enciende al conectar "
             "la batería; en esta etapa del proyecto no tiene carga conectada."},
    {"tipo": "palanca", "id": "SW_NAV",   "pos": (156, 264), "tam": (66, 78),
     "rot": "NAV LT", "sub": "POSICIÓN", "senal": "bateria",
     "desc": "Luces de posición: roja a la izquierda, verde a la derecha, blanca atrás."},
    {"tipo": "palanca", "id": "SW_ACOLL", "pos": (224, 264), "tam": (66, 78),
     "rot": "ANTI-COLL", "sub": "BALIZA", "senal": "bateria",
     "desc": "Baliza rotativa anticolisión. Se enciende antes de mover el rotor: es la "
             "señal visual de que la aeronave está viva."},

    {"tipo": "rotulo", "pos": (20, 350), "tam": (272, 12),
     "texto": "DISYUNTORES  ·  CIRCUIT BREAKERS"},
    {"tipo": "disyuntor", "id": "CB_GEN",   "pos": (20, 364),  "tam": (43, 36), "rot": "GEN",   "senal": "cb_gen"},
    {"tipo": "disyuntor", "id": "CB_BATT",  "pos": (65, 364),  "tam": (43, 36), "rot": "BATT",  "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_INST",  "pos": (110, 364), "tam": (43, 36), "rot": "INST",  "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_FUEL",  "pos": (155, 364), "tam": (43, 36), "rot": "FUEL",  "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_LTS",   "pos": (200, 364), "tam": (43, 36), "rot": "LTS",   "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_RADIO", "pos": (245, 364), "tam": (43, 36), "rot": "RADIO", "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_IGN",   "pos": (20, 402),  "tam": (43, 36), "rot": "IGN",   "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_PUMP",  "pos": (65, 402),  "tam": (43, 36), "rot": "PUMP",  "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_XMSN",  "pos": (110, 402), "tam": (43, 36), "rot": "XMSN",  "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_PITOT", "pos": (155, 402), "tam": (43, 36), "rot": "PITOT", "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_ANTI",  "pos": (200, 402), "tam": (43, 36), "rot": "ANTI",  "senal": "cb_bus"},
    {"tipo": "disyuntor", "id": "CB_AUX",   "pos": (245, 402), "tam": (43, 36), "rot": "AUX",   "senal": "cb_bus"},


]

# ===========================================================================
# 7c. CHAPAS DE DATOS
# ===========================================================================
# Chapas de texto que la página puede dibujar sobre el tablero. Vacía: la
# ficha de la aeronave y sus limitaciones están en la memoria técnica, y en
# pantalla sólo van instrumentos.
# ===========================================================================
PANEL_PLACAS = []

# --- Se vuelca todo dentro de la tabla principal ---------------------------
for _it in list(TABLERO) + PANEL_VIRTUAL:
    _p = PANEL.get(_it["id"])
    if _p:
        _it["desc"] = _p["desc"]
        _it["zona"] = _p["zona"]
        _it["dial"] = _p["dial"]
        _it["pos"] = _p["pos"]
        _it["tam"] = _p["tam"]
for _a in ANUNCIADOR:
    _t = TABLERO_POR_ID.get(_a["id"])
    if _t:
        _t["desc"] = _a["desc"]
        _t["leyenda"] = _a["leyenda"]
        _t["dial"] = "luz"
