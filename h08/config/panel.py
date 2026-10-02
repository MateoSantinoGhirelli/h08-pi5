# -*- coding: utf-8 -*-
"""Geometría y textos del tablero en la página web (no los usa la simulación)."""

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
