# -*- coding: utf-8 -*-
"""
h08/config/aeronave.py - la aeronave: identidad y límites físicos del H-19A
===========================================================================
Sikorsky S-55 / H-19A Chickasaw - matrícula H-08 (Fuerza Aérea Argentina)
Proyecto H-08 · EEST N° 7 - Taller Regional Quilmes

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
