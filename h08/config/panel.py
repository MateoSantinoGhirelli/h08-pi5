# -*- coding: utf-8 -*-
"""Geometría y textos del tablero en la página web; la simulación no los usa.

La disposición sale de una foto de cabina de un S-55 y el contenido, del reporte de
aviónica del H-08 y del T.O. 1H-19A-1; los tamaños son proporcionales a las bocas de
la chapa (1,79 unidades por mm). Campos, medidas y tipos de esfera: docs/panel.md.
"""

# unidades de diseño: la página escala el lienzo a la ventana
PANEL_LIENZO = (1340, 680)

# estilo "verde": chapa estructural pintada; "negro": sub-panel atornillado encima
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
    # columna de motor, transmisión y combustible (bocas de 48 y 58 mm)
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

    # sub-panel negro de vuelo (bocas de 78 y 122 mm): arriba el velocímetro y los
    # dos grandes; en el medio altímetro, tacómetro, viraje y AN/ARN-14; abajo el
    # variómetro, la luz LOW ROTOR bajo el tacómetro que vigila y la admisión
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

# Se dibujan pero no llevan actuador: el reloj del H-19A es mecánico (se le da cuerda),
# ocupa una boca del tablero y no usa ningún canal.
PANEL_VIRTUAL = [
    {"id": "CLOCK", "n": 21, "nombre": "Reloj de cabina",
     "en": "Cockpit clock, 8-day mechanical",
     "unidad": "h:mm:ss", "escala": (0.0, 43200.0), "arcos": [],
     "actuador": "MECANICO", "senal": "t_sim", "cal": []},
]

# luces de alerta, en el orden del anunciador
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

# Las llaves del cuarto izquierdo del tablero: en el físico son decorativas, pero la
# página las anima con el estado del simulador para mostrar qué hace el piloto
# virtual en cada fase (tipos y campos en docs/panel.md).
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

# Chapas de texto sobre el tablero. Vacía a propósito: la ficha y las limitaciones
# están en la memoria técnica y en pantalla sólo van instrumentos.
PANEL_PLACAS = []
