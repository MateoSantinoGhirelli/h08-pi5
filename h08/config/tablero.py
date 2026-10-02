# -*- coding: utf-8 -*-
"""Los instrumentos del tablero: escala, tabla de calibración y canal de cada uno."""

from h08.config.mecanica import tabla_alabeo, tabla_cabeceo

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
#   cal       : tabla [(valor, ángulo_actuador)], ver h08.util.interpolar_tabla
#   tau       : constante de tiempo de la aguja en segundos (inercia)
#   slew      : velocidad máxima de la aguja en grados/segundo
#   canal     : (placa, canal) donde está conectado: ("PCA0", 7), ("MOTOR", 1)
#
# El campo 'cal' hace que el tablero sea calibrable: para ajustar un
# instrumento se corrige su tabla, no el código.
# ===========================================================================

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
        "cal": tabla_cabeceo(),
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
        "cal": tabla_alabeo(),
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
