# -*- coding: utf-8 -*-
"""Lazo de control, arranque escalonado, placas PCA9685, servos, luces y motor."""

LAZO = {
    "hz_fisica": 20,      # 50 ms por paso. Un servo refresca a 50 Hz y la aguja
                          # más rápida del tablero tiene tau = 0,3 s.
    "hz_salida": 20,      # escrituras por segundo a las placas
    "hz_telemetria": 5,   # fotos de estado por segundo para la página web
    "banda_muerta": 2,    # en cuentas de 12 bits del PCA9685: un canal que
                          # cambia menos que esto no se escribe por I2C.
}

# Al encender, los 20 servos se moverían juntos en la primera escritura, y cada uno
# pide unos 700 mA al arrancar: la fuente LM2596 (3 A) se cae y los PCA9685 se
# reinician. De a tandas, el pico es canales_por_tanda × 0,7 A y el arranque dura
# canales / canales_por_tanda × segundos_entre_tandas: con 3 y 0,25 s, unos 2,1 A y
# menos de 2,5 s. Con una fuente holgada se puede subir; si se reinicia, bajarlo.
ARRANQUE = {
    "canales_por_tanda": 3,
    "segundos_entre_tandas": 0.25,
}

# Bus I2C 1 de la Pi (GPIO2 = SDA, GPIO3 = SCL). La dirección sale de los puentes
# A0..A5 de cada módulo: la placa 0 sin puentes (0x40), la 1 con A0 soldado (0x41).
I2C_BUS = 1
PLACAS = {"PCA0": 0x40, "PCA1": 0x41}

# Nominales de la hoja de datos del MG90S. Los extremos medidos de cada servo
# (python3 -m h08 calibrar) quedan en datos/calibracion_servos.json y mandan sobre
# estos sólo en su canal.
SERVO_CFG = {
    "pulso_min_us": 500,    # 0 grados
    "pulso_max_us": 2500,   # 180 grados
    "barrido_deg": 180.0,
    "frecuencia_hz": 50,    # período de 20 ms: 1 cuenta del PCA9685 = 4,88 us
}

# En la placa madre cada LED va con el ánodo a +5 V (J8) y el cátodo, por 220 Ω
# (R2..R7), a una salida del PCA9685 (J7), que sumidera la corriente: enciende con
# la salida en BAJO. Al dar energía, antes de que arranque el programa, todas las
# salidas están en bajo y se encienden las seis: es la prueba de lámparas del encendido.
LUCES_ACTIVAS_EN_BAJO = True

# 28BYJ-48 con su plaquita ULN2003. La reducción real es
# (32/9)(22/11)(26/9)(31/10) = 63,684, no 64: en medio paso, 64 × 63,684 = 4075,77
# pasos por vuelta. Con 4096 la aguja se corre 1,8° por vuelta. Se comprueba con
# python3 -m h08 motor 1 --vueltas 10: la aguja tiene que volver al mismo lugar.
MOTOR_CFG = {
    "pasos_por_vuelta": 4075.77,  # medio paso: 0,088 grados por paso
    "vel_max_pps": 900,           # unas 13 vueltas por minuto
    "vel_arranque_pps": 200,      # velocidad desde la que arranca sin perder pasos
    "aceleracion": 2000,          # pasos por segundo al cuadrado
    "soltar_tras_s": 0.5,         # quieto este tiempo, se cortan las bobinas
}

# Queda un solo motor, el de la brújula: el resto de las agujas lleva servo.
# pines: GPIO (BCM) de IN1..IN4 de la plaquita, en ese orden, que la placa madre lleva
# a U2; el lugar de U1 (motor 0, GPIO 6-13-19-26) queda libre.
# sentido: la rosa está pegada y el motor mueve una aguja de 47 mm, así que pidiendo
# 90° la aguja tiene que apuntar a la E. Si en el banco gira al revés, se cambia acá
# (+1 o -1) y nada más; se prueba con python3 -m h08 motor 1 --grados 90.
MOTORES = {
    1: {"id": "COMPASS", "pines": (12, 16, 20, 21), "sentido": 1},
}
