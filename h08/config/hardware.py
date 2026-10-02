# -*- coding: utf-8 -*-
"""Lazo de control, arranque escalonado, placas PCA9685, servos, luces y motor."""

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
# datos/calibracion_servos.json y reemplazan a estos sólo para ese
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
#     python3 -m h08 motor 1 --vueltas 10
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
