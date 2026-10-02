# -*- coding: utf-8 -*-
"""El H-19A de la matrícula H-08: su identidad y sus límites físicos (T.O. 1H-19A-1).

La ficha completa de la célula y la relación 10:1 del tacómetro doble están en
docs/aeronave.md.
"""

# lo muestra la página web
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

LIM = {
    # motor
    "rpm_motor_ralenti": 1400.0,
    "rpm_motor_crucero": 2200.0,
    "rpm_motor_despegue": 2250.0,
    "rpm_motor_max": 2400.0,
    "rpm_motor_escala": 3500.0,       # fondo de escala del tacómetro
    "rpm_arranque_corte": 600.0,      # por debajo de esto el motor no sostiene

    # rotor
    "rpm_rotor_min": 170.0,           # arco rojo inferior
    "rpm_rotor_nom": 220.0,
    "rpm_rotor_max": 245.0,           # arco rojo superior
    "rpm_rotor_escala": 350.0,
    "reduccion": 10.0,                # motor:rotor

    # presión de admisión (motor sobrealimentado)
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

    # aceite de motor
    "oil_p_min": 25.0,                # psi, mínimo en ralenti
    "oil_p_nom": 80.0,
    "oil_p_max": 100.0,
    "oil_p_escala": 150.0,
    "oil_t_nom": 70.0,                # C
    "oil_t_min_despegue": 40.0,       # no se despega con el aceite más frío
    "oil_t_max": 85.0,
    "oil_t_escala": 100.0,

    # cabeza de cilindro
    # El límite absoluto del R-1340 son 260 C (500 F). En tierra, con el
    # helicóptero quieto y sin viento relativo, la recomendación es no pasar
    # de 232 C (450 F): sin traslación el radial se recalienta rápido, y es
    # la limitación operativa clásica del tipo.
    "cht_nom": 200.0,                 # C
    "cht_tierra_max": 232.0,          # 450 F, límite en tierra
    "cht_max": 260.0,                 # 500 F, límite absoluto
    "cht_escala": 350.0,

    # carburador
    "cat_nom": 15.0,                  # C
    "cat_hielo_min": -10.0,           # banda de riesgo de engelamiento
    "cat_hielo_max": 15.0,

    # combustible
    "fuel_p_nom": 16.0,               # psi
    "fuel_p_min": 12.0,
    "fuel_p_escala": 25.0,
    "cap_fwd": 378.0,                 # litros
    "cap_aft": 322.0,
    "aviso_fuel_l": 45.0,             # nivel que enciende la luz ámbar
    "consumo_max_lph": 155.0,         # a potencia de despegue
    "consumo_min_lph": 22.0,          # ralenti

    # transmisión principal
    "xmsn_p_nom": 55.0,               # psi
    "xmsn_p_min": 30.0,
    "xmsn_p_escala": 100.0,
    "xmsn_t_nom": 85.0,               # C
    "xmsn_t_max": 110.0,
    "xmsn_t_escala": 150.0,

    # sistema eléctrico
    "bus_bateria": 24.0,              # V con generador fuera de línea
    "bus_generador": 28.0,            # V con generador en línea
    "bus_min_util": 20.0,             # por debajo los instrumentos eléctricos mueren
    "amp_escala": 200.0,
    "amp_carga_max": 120.0,
    # Aceleración didáctica de la carga y descarga de la batería: una batería
    # real tarda una hora en descargarse, y eso no se puede mostrar en clase.
    "factor_bateria": 8.0,

    # vuelo
    "vne_kt": 95.0,
    "v_crucero_kt": 74.0,
    "v_escala_kt": 120.0,
    "vs_escala_fpm": 2000.0,
    "alt_escala_ft": 10000.0,
    "techo_ft": 10500.0,
    "viraje_estandar_dps": 3.0,       # 3 grados/s = viraje de 2 minutos

    # ambiente por defecto (ISA a nivel del mar)
    "oat_c": 15.0,
    "qnh_hpa": 1013.0,
}
