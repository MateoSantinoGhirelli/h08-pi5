# -*- coding: utf-8 -*-
"""
h08/simulacion/modelo.py - modelo físico del H-19A y piloto virtual
===========================================================

FILOSOFÍA DEL MODELO
--------------------------------------------------------------------------
No se simula un helicóptero completo de 6 grados de libertad: sería costoso
en CPU, difícil de calibrar e innecesario para mover agujas.

Se usa un modelo CUASI-ESTÁTICO CON RETARDOS, que es como razona un técnico:

    "Si el piloto sube el mando de paso colectivo, la potencia requerida sube; el motor
     responde subiendo la presión de admisión; si la potencia entregada no
     alcanza, el régimen del rotor cae; la temperatura de culata sube despacio
     porque tiene mucha masa térmica..."

Cada magnitud tiene un OBJETIVO calculado algebraicamente y lo persigue con
una constante de tiempo propia. El resultado es físicamente coherente,
determinista, estable con cualquier paso de tiempo y explicable renglón por
renglón.

LA ÚNICA ECUACIÓN DIFERENCIAL DE VERDAD
--------------------------------------------------------------------------
La excepción es la inercia del rotor principal, que SI se integra:

        d(Omega)/dt = (P_disponible - P_requerida) / (I * Omega)

Esta ecuación produce, sin agregar nada, los fenómenos didácticos más
importantes:
  * las RPM caen si se pide más potencia de la que hay
  * en autorrotación, bajar el mando de paso colectivo hace SUBIR el régimen del rotor
  * el "needle split" del tacómetro doble al desacoplar la rueda libre
  * el aterrizaje en autorrotación agotando la energía cinética del rotor
"""

from h08.util import limitar, aproximar, mezclar, rampa
from h08.config import LIM

# ---------------------------------------------------------------------------
# Posiciones del selector de magnetos
# ---------------------------------------------------------------------------
MAG_OFF = 0
MAG_L = 1
MAG_R = 2
MAG_BOTH = 3

# Selector de tanque
TANQUE_FWD = 0
TANQUE_AFT = 1
TANQUE_AMBOS = 2


class Controles:
    """Posición de los mandos. Los escribe el piloto virtual o un escenario."""

    def __init__(self):
        self.colectivo = 0.0        # 0..1
        self.throttle = 0.0         # 0..1 (correlado al colectivo en vuelo)
        self.ciclico_lon = 0.0      # -1..1 (adelante = negativo = picar)
        self.ciclico_lat = 0.0      # -1..1
        self.pedal = 0.0            # -1..1
        self.calefaccion_carb = 0.0  # 0..1
        self.mezcla = 1.0           # 0..1 (1 = rica)

        # Llaves
        self.bateria = False
        self.generador = False
        self.magnetos = MAG_OFF
        self.arrancador = False
        self.bomba_combustible = False
        self.embrague = False        # embrague principal acoplado
        self.selector_tanque = TANQUE_AMBOS
        self.luces_tablero = 0.0     # 0..1


class SaludSistemas:
    """
    Multiplicadores de salud, de 0.0 (destruido) a 1.0 (perfecto).
    El motor de fallas escribe acá; el modelo físico solo lee.
    Esta separación es lo que permite que CUALQUIER falla sea coherente:
    no se "trucan" las agujas, se degrada el sistema y las agujas siguen.
    """

    def __init__(self):
        self.reiniciar()

    def reiniciar(self):
        self.motor = 1.0            # potencia disponible
        self.magneto_l = 1.0
        self.magneto_r = 1.0
        self.bomba_aceite = 1.0
        self.refrigeracion = 1.0    # refrigeración de CULATA (deflectores, ventilador)
        # El aceite tiene su PROPIO radiador, separado del aire que refrigera
        # las culatas. Por eso una obstrucción del enfriador de aceite calienta
        # el aceite sin cocinar las cabezas de cilindro, y un problema de
        # deflectores hace lo contrario. Con una sola salud para las dos cosas,
        # las dos fallas daban el mismo tablero y no se podían distinguir.
        self.refrigeracion_aceite = 1.0
        self.carburador = 1.0       # 1.0 = limpio, 0.0 = obstruido por hielo
        self.bomba_combustible = 1.0
        self.fuga_combustible_lph = 0.0
        self.transmision_bomba = 1.0
        self.transmision_refrig = 1.0
        self.rotor_cola = 1.0
        self.generador = 1.0
        self.bateria = 1.0
        self.embrague = 1.0         # <1.0 = patina
        self.vacio_giro = 1.0       # salud de los giróscopos
        self.estatica = 1.0


class ModeloVuelo:
    """Estado físico completo de la aeronave."""

    # -- constantes de sintonía del modelo (agrupadas para poder ajustarlas) --
    K_INERCIA_ROTOR = 850.0     # rigidez de la ecuación del rotor
    K_VERT = 900.0              # ft/min de aceleración vertical por unidad de empuje
    TAU_IAS = 6.0               # inercia longitudinal del helicóptero
    # Eficiencia con que el flujo ascendente a través del disco devuelve
    # energía al rotor en autorrotación. Está calibrada para que el régimen de
    # descenso de equilibrio quede en el orden de los 1500 ft/min, que es el
    # del S-55 real. Con un valor más alto la máquina "planeaba" a 500 ft/min,
    # que le daba al alumno una idea peligrosamente optimista del tiempo que
    # tiene para elegir dónde aterrizar.
    K_AUTOROT = 0.145

    def __init__(self):
        self.ctl = Controles()
        self.salud = SaludSistemas()
        self.reiniciar()

    # =======================================================================
    def reiniciar(self, en_frio=True):
        self.t = 0.0
        self.salud.reiniciar()

        # --- Ambiente ---
        # Temperatura de aire exterior: es el piso del que salen todas las
        # demás temperaturas (aceite, culata, carburador y transmisión).
        self.oat_c = LIM["oat_c"]
        self.qnh_hpa = LIM["qnh_hpa"]
        self.humedad = 0.45          # 0..1 - alimenta el riesgo de engelamiento

        # --- Grupo motopropulsor ---
        self.n_eng_rpm = 0.0
        self.n_rot_rpm = 0.0
        self.map_inhg = LIM["map_ambiente"]
        self.pot_requerida = 0.0     # 0..1.2  carga del rotor
        self.pot_entregada = 0.0     # 0..1.2  potencia del motor
        self.acoplado = False        # rueda libre transmitiendo motor -> rotor

        # --- Fluidos ---
        self.oil_p_psi = 0.0
        self.oil_t_c = self.oat_c
        self.cht_c = self.oat_c
        self.cat_c = self.oat_c
        self.fuel_p_psi = 0.0
        self.fuel_fwd_l = LIM["cap_fwd"]
        self.fuel_aft_l = LIM["cap_aft"]
        self.flujo_lph = 0.0
        self.hielo_carb = 0.0        # 0..1 acumulación de hielo

        # --- Transmisión ---
        self.xmsn_p_psi = 0.0
        self.xmsn_t_c = self.oat_c

        # --- Giróscopos ---
        # En el H-19 el horizonte artificial y el indicador de rumbo son
        # ELECTRICOS: los alimenta el inversor desde la barra de 24 V. Un
        # giróscopo no arranca ni se detiene instantáneamente.
        #   giro = 0  rotor detenido, el instrumento no indica nada útil
        #   giro = 1  rotor a régimen, el instrumento indica bien
        # Al energizar la barra tarda cerca de un minuto en erigirse, y al
        # quedarse sin alimentación NO se congela: se va cayendo despacio,
        # mintiendo cada vez más. Esa diferencia -entre un instrumento que
        # miente de golpe y uno que miente despacio- es lo que hace peligrosa
        # una falla eléctrica en vuelo por instrumentos.
        self.giro_att = 0.0         # régimen del giro del horizonte
        self.giro_dg = 0.0          # régimen del giro de rumbo
        self.deriva_dg_deg = 0.0    # error acumulado del indicador de rumbo
        self.deriva_att_deg = 0.0   # error acumulado del horizonte artificial

        # Altura a la que se tapó la toma estática. None = toma despejada.
        # Ver ias_ind_kt: el error del velocímetro con la estática obstruida
        # NO es un número fijo, crece a medida que la aeronave se aleja de esa
        # altura. En vuelo nivelado la falla es INVISIBLE.
        self.alt_estatica_ft = None

        # --- Eléctrico ---
        self.bus_v = 0.0
        self.amp_a = 0.0
        self.bateria_ah_max = 34.0   # capacidad típica de batería de plomo 24 V
        self.bateria_ah = 34.0
        self.gen_en_linea = False
        self.motor_vivo = False
        self.arranque_activo = False
        self.empuje = 0.0

        # --- Vuelo ---
        self.alt_ft = 0.0
        self.alt_terreno_ft = 0.0
        self.ias_kt = 0.0
        self.vs_fpm = 0.0
        self.hdg_deg = 90.0
        self.pitch_deg = 0.0
        self.roll_deg = 0.0
        self.turn_rate_dps = 0.0
        self.slip = 0.0
        self.cdi = 0.0
        self.en_tierra = True

        if not en_frio:
            self._precalentar()

    def _precalentar(self):
        """
        Arranque en caliente: deja la aeronave lista para volar.

        Se reponen todos los mandos, no sólo los evidentes: los controles
        viven fuera de reiniciar() y conservan lo que quedó del modo
        anterior. Si se venía de la fase de corte de motor (mezcla en 0 e
        ignición en OFF), sin esto el motor no volvería a arrancar.
        """
        self.ctl.bateria = True
        self.ctl.generador = True
        self.ctl.magnetos = MAG_BOTH
        self.ctl.arrancador = False
        self.ctl.bomba_combustible = True
        self.ctl.embrague = True
        self.ctl.mezcla = 1.0
        self.ctl.calefaccion_carb = 0.0
        self.ctl.selector_tanque = TANQUE_AMBOS
        self.ctl.luces_tablero = 0.7
        self.ctl.pedal = 0.0
        self.ctl.ciclico_lat = 0.0
        self.ctl.throttle = 0.48
        self.ctl.colectivo = 0.552
        self.n_eng_rpm = LIM["rpm_motor_crucero"]
        self.n_rot_rpm = LIM["rpm_rotor_nom"]
        self.map_inhg = LIM["map_crucero"]
        self.cat_c = self.oat_c - 18.0 * (1.0 - 0.72 * 0.48)
        self.fuel_p_psi = LIM["fuel_p_nom"]
        self.acoplado = True
        self.oil_p_psi = LIM["oil_p_nom"]
        self.oil_t_c = LIM["oil_t_nom"]
        self.cht_c = LIM["cht_nom"]
        self.xmsn_p_psi = LIM["xmsn_p_nom"]
        self.xmsn_t_c = LIM["xmsn_t_nom"]
        self.bus_v = LIM["bus_generador"]
        self.gen_en_linea = True
        self.giro_att = 1.0
        self.giro_dg = 1.0
        self.deriva_dg_deg = 0.0
        self.deriva_att_deg = 0.0
        self.alt_estatica_ft = None
        self.en_tierra = False

    # =======================================================================
    # PASO DE SIMULACIÓN
    # =======================================================================
    def paso(self, dt):
        self.t += dt
        self._paso_aire(dt)
        self._paso_electrico(dt)
        self._paso_motor(dt)
        self._paso_rotor(dt)
        self._paso_fluidos(dt)
        self._paso_transmision(dt)
        self._paso_combustible(dt)
        self._paso_vuelo(dt)

    # -----------------------------------------------------------------------
    # 0. EL AIRE DE AFUERA
    # -----------------------------------------------------------------------
    def _paso_aire(self, dt):
        """La temperatura exterior baja con la altura.

        Atmósfera estándar (ISA): 15 °C al nivel del mar y una caída de
        1,98 °C cada 1000 pies. Como todas las temperaturas del motor parten
        de este piso, subir a 3000 pies enfría seis grados el punto de partida
        del aceite, la culata, el carburador y la transmisión.
        """
        del dt
        self.oat_c = LIM["oat_c"] - 1.98 * (self.alt_ft / 1000.0)

    # -----------------------------------------------------------------------
    # 1. SISTEMA ELÉCTRICO
    # -----------------------------------------------------------------------
    def _paso_electrico(self, dt):
        s = self.salud
        if not self.ctl.bateria:
            self.bus_v = aproximar(self.bus_v, 0.0, dt, 0.25)
            self.amp_a = aproximar(self.amp_a, 0.0, dt, 0.3)
            self.gen_en_linea = False
            return

        # El generador entra en línea recien con el motor girando con fuerza
        quiere_gen = (self.ctl.generador and s.generador > 0.25
                      and self.n_eng_rpm > 1200.0)
        self.gen_en_linea = quiere_gen

        consumo_a = 18.0                       # instrumentos, radios, luces
        consumo_a += 12.0 * self.ctl.luces_tablero
        if self.ctl.arrancador:
            # El motor de arranque de un radial de 600 HP se lleva cientos de
            # amperes. El amperímetro se va contra el tope de descarga y la
            # barra se desploma: por eso, mientras gira el arrancador, las
            # luces bajan y los instrumentos eléctricos se caen.
            consumo_a += 180.0

        if quiere_gen:
            v_obj = LIM["bus_generador"] * mezclar(0.8, 1.0, s.generador)
            # corriente de carga: alta si la batería está baja, decae al llenarse
            deficit = limitar((self.bateria_ah_max - self.bateria_ah)
                              / self.bateria_ah_max, 0.0, 1.0)
            carga = LIM["amp_carga_max"] * deficit
            self.amp_a = aproximar(self.amp_a, consumo_a + carga, dt, 0.8)
            # 1 amperio durante 1 hora = 1 Ah. Se recarga 20 veces más rápido
            # que en la realidad para que el efecto se vea en una clase.
            self.bateria_ah = limitar(self.bateria_ah + carga * dt / 3600.0 * LIM["factor_bateria"],
                                      0.0, self.bateria_ah_max)
        else:
            # Solo batería: la tensión cae a medida que se descarga
            carga_rel = limitar(self.bateria_ah / self.bateria_ah_max, 0.0, 1.0)
            v_obj = LIM["bus_bateria"] * (0.72 + 0.28 * carga_rel) * s.bateria
            # Caída por resistencia interna: con 20 A no se nota, con los 200 A
            # del arrancador la barra se va a 18-20 V. Es lo que hace que
            # durante el arranque el tablero entero se apague a medias.
            v_obj -= 0.021 * consumo_a * (2.0 - carga_rel)
            v_obj = max(v_obj, 0.0)
            self.amp_a = aproximar(self.amp_a, -consumo_a, dt, 0.8)
            self.bateria_ah = limitar(self.bateria_ah - consumo_a * dt / 3600.0 * LIM["factor_bateria"],
                                      0.0, self.bateria_ah_max)

        self.bus_v = aproximar(self.bus_v, v_obj, dt, 0.35)
        self._paso_giroscopos(dt)
        self._paso_pitot_estatica()

    def _paso_pitot_estatica(self):
        """
        Toma estática: se anota la altura a la que se obstruyó.

        Es todo lo que hace falta para que el error del velocímetro salga solo
        (ver ias_ind_kt). Se anota una sola vez, al taparse, y se olvida
        cuando la toma se despeja o se pasa a la fuente estática alternativa.
        """
        if self.salud.estatica < 0.5:
            if self.alt_estatica_ft is None:
                self.alt_estatica_ft = self.alt_ft
        else:
            self.alt_estatica_ft = None

    def _paso_giroscopos(self, dt):
        """Erección y caída de los dos giróscopos eléctricos."""
        s = self.salud
        # El inversor necesita barra sana. Por debajo de 20 V no alcanza.
        alimentado = self.bus_v >= LIM["bus_min_util"]

        # Erección: cerca de un minuto. Caída: mucho más lenta, porque el
        # rotor sigue girando por inercia varios minutos.
        obj_att = 1.0 if alimentado else 0.0
        obj_dg = 1.0 if alimentado else 0.0
        tau_att = 22.0 if alimentado else 70.0
        tau_dg = 28.0 if alimentado else 90.0
        self.giro_att = aproximar(self.giro_att, obj_att * s.vacio_giro, dt, tau_att)
        self.giro_dg = aproximar(self.giro_dg, obj_dg * s.vacio_giro, dt, tau_dg)

        # El indicador de rumbo deriva mientras el giro no está a régimen.
        # Con el giro sano la deriva se corrige sola (va esclavizado a la
        # válvula de flujo magnético); sin alimentación se va sumando.
        if self.giro_dg > 0.97:
            self.deriva_dg_deg = aproximar(self.deriva_dg_deg, 0.0, dt, 25.0)
        else:
            self.deriva_dg_deg += (1.0 - self.giro_dg) * 2.6 * dt

        # El horizonte artificial hace lo mismo, y es peor: un giróscopo que
        # se cae NO se congela ni se pone en cero. Se VUELCA despacio y muestra
        # una actitud que no existe. El piloto que lo sigue creyéndole, mete la
        # aeronave en la actitud que el instrumento le está inventando. Por eso
        # una falla eléctrica en vuelo por instrumentos es tan peligrosa: el
        # tablero no avisa que dejó de servir, sigue indicando.
        if self.giro_att > 0.97:
            self.deriva_att_deg = aproximar(self.deriva_att_deg, 0.0, dt, 20.0)
        else:
            self.deriva_att_deg += (1.0 - self.giro_att) * 1.9 * dt
            self.deriva_att_deg = limitar(self.deriva_att_deg, -30.0, 30.0)

    # --- Indicaciones giroscópicas: lo que MUESTRA el instrumento -----------
    # No es la actitud real de la aeronave: es la actitud real filtrada por el
    # estado del giróscopo. Con el giro cayendo, el horizonte se va quedando
    # atrás y termina mostrando una actitud que ya no existe.
    @property
    def pitch_ind_deg(self):
        return self.pitch_deg * self.giro_att + 0.55 * self.deriva_att_deg

    @property
    def roll_ind_deg(self):
        return self.roll_deg * self.giro_att + self.deriva_att_deg

    @property
    def hdg_giro_deg(self):
        return (self.hdg_deg + self.deriva_dg_deg) % 360.0

    # --- Velocidad INDICADA: el sistema pitot-estática ----------------------
    # El velocímetro no mide velocidad: mide la DIFERENCIA entre la presión
    # de impacto del tubo pitot y la presión estática. Si la toma estática se
    # tapa, adentro del instrumento queda encerrada la presión que había en el
    # momento de taparse, y a partir de ahí el error del velocímetro depende
    # de cuánto se aleje la aeronave de ESA altura:
    #
    #   * volando nivelado a la misma altura   -> no hay ningún error
    #   * subiendo (menos presión afuera)      -> el velocímetro indica DE MENOS
    #   * bajando (más presión afuera)         -> indica DE MÁS
    #
    # Por eso la obstrucción de la toma estática es una falla insidiosa: no se
    # nota hasta que se cambia de altura, y entonces miente en el sentido más
    # peligroso -en el ascenso hace creer que se está lento, y el piloto baja
    # la nariz-. Por eso se modela así y no como un error fijo.
    @property
    def ias_ind_kt(self):
        if self.alt_estatica_ft is None:
            return self.ias_kt
        # ~1 kt de error por cada 100 ft de diferencia, a velocidad de crucero
        d_ft = self.alt_ft - self.alt_estatica_ft
        return max(0.0, self.ias_kt - d_ft * 0.010 * limitar(
            self.ias_kt / 74.0, 0.25, 1.5))

    @property
    def energia_ok(self):
        return self.bus_v >= LIM["bus_min_util"]

    # -----------------------------------------------------------------------
    # 2. MOTOR RADIAL R-1340-57
    # -----------------------------------------------------------------------
    def _paso_motor(self, dt):
        s = self.salud
        ctl = self.ctl

        # --- Magnetos --------------------------------------------------------
        # El R-1340 tiene doble encendido: dos bujías por cilindro, cada una
        # alimentada por un magneto distinto. Con las dos, el frente de llama
        # sale de dos puntos y la combustión termina rápido. Con una sola el
        # motor SIGUE andando, pero quema peor y pierde alrededor del 11% de
        # POTENCIA.
        #
        # La cifra del manual (50 a 100 RPM de caída) es de RÉGIMEN, no de
        # potencia. A mariposa fija el rotor consume potencia con el cubo de
        # su velocidad de giro, así que perder un 11 % de potencia baja las
        # RPM alrededor de un 4 %: las 80-90 RPM que se miden en el run-up.
        n_mag = 0
        if ctl.magnetos in (MAG_L, MAG_BOTH) and s.magneto_l > 0.5:
            n_mag += 1
        if ctl.magnetos in (MAG_R, MAG_BOTH) and s.magneto_r > 0.5:
            n_mag += 1
        if n_mag == 0:
            factor_mag = 0.0
        elif n_mag == 1:
            factor_mag = 0.89
        else:
            factor_mag = 1.0
        # Se guarda para el cálculo de temperatura de culata: con un solo
        # magneto el frente de llama sale de una bujía en vez de dos, la
        # combustión termina más tarde y la cabeza del cilindro se calienta.
        self.n_magnetos = n_mag

        # --- Combustible disponible en la toma ---------------------------
        hay_combustible = self._combustible_disponible() > 0.5
        presion_ok = self.fuel_p_psi > 4.0 or self.n_eng_rpm < 300.0

        # Presión de combustible baja: el carburador no recibe caudal
        # suficiente y el motor NO se para de golpe, se queda sin fuerza y
        # empieza a marchar áspero. La falla se nota primero a alta potencia,
        # porque es donde más caudal hace falta; en ralentí puede pasar
        # inadvertida. Por eso la aguja de presión de combustible fuera del
        # arco verde es un aviso, no una emergencia inmediata.
        if self.n_eng_rpm > 300.0 and self.fuel_p_psi < LIM["fuel_p_min"]:
            factor_fuel = limitar(
                (self.fuel_p_psi - 3.0) / (LIM["fuel_p_min"] - 3.0), 0.0, 1.0)
            factor_fuel = 0.30 + 0.70 * factor_fuel
        else:
            factor_fuel = 1.0

        # --- Hielo de carburador -----------------------------------------
        self._paso_hielo_carburador(dt)
        factor_carb = s.carburador * (1.0 - 0.85 * self.hielo_carb)

        # --- Presión de admisión ------------------------------------------
        # El manómetro de admisión es ABSOLUTO. Con el motor parado marca la
        # presión barométrica del campo, unas 29,9 inHg. Al arrancar, la
        # aguja BAJA hasta unas 13 inHg, porque la mariposa cerrada genera
        # depresión en el colector. Recién al abrir gases vuelve a subir.
        #
        # Esa caída al arrancar es la primera cosa rara que ve el alumno, y
        # es la que hace entender qué mide realmente el instrumento.
        perdida_alt = self.alt_ft * 0.001        # ~1 inHg por cada 1000 ft
        map_ambiente = LIM["map_ambiente"] - perdida_alt
        if self.n_eng_rpm < 200.0:
            map_obj = map_ambiente
        else:
            map_obj = mezclar(LIM["map_ralenti"], LIM["map_despegue"], ctl.throttle)
            map_obj -= perdida_alt
            # El hielo estrangula la admisión: la aguja cae sin tocar la
            # mariposa, que es el síntoma que delata el engelamiento.
            map_obj *= mezclar(0.35, 1.0, factor_carb)
            # La calefacción de carburador mete aire caliente, menos denso:
            # cuesta entre 1 y 2 inHg de admisión aunque no haya hielo.
            map_obj -= 1.8 * ctl.calefaccion_carb
            map_obj = limitar(map_obj, LIM["map_min"], LIM["map_max"])
        self.map_inhg = aproximar(self.map_inhg, map_obj, dt, 0.25)

        # --- Potencia disponible ------------------------------------------
        # Normalizada: 1.0 = potencia continua máxima (550 HP)
        rel_map = limitar((self.map_inhg - LIM["map_ralenti"]) /
                          (LIM["map_despegue"] - LIM["map_ralenti"]), 0.0, 1.2)
        # Un motor a pistón no "vive" por debajo de un régimen mínimo: hay que
        # arrastrarlo con el arrancador hasta que pueda sostenerse solo.
        motor_vivo = (factor_mag > 0.0 and hay_combustible and presion_ok
                      and s.motor > 0.02 and ctl.mezcla > 0.15
                      and self.n_eng_rpm > 200.0)

        if motor_vivo:
            # Con la mariposa en una posición fija, el caudal de aire que entra
            # está limitado por la propia mariposa: la potencia crece con las
            # RPM hasta que el motor "llena" ese caudal (unas 900 RPM) y de ahí
            # en más se mantiene prácticamente constante. Ese techo, combinado
            # con la fricción que crece con el cuadrado de las RPM, es lo que
            # le da al motor un régimen de equilibrio ESTABLE para cada
            # posición de mariposa. Sin este detalle el motor se embalaría.
            factor_rpm = limitar(self.n_eng_rpm / 900.0, 0.0, 1.0)
            self.pot_entregada = (rel_map * factor_mag * s.motor * ctl.mezcla
                                  * factor_rpm * factor_fuel)
            # Detonación por sobretemperatura: pasado el límite de culata la
            # mezcla se autoenciende antes de tiempo, el motor pierde fuerza y
            # se destruye. Modelarlo cierra el lazo: la cabeza deja de
            # calentarse porque el motor deja de dar potencia. Sin este
            # término la temperatura crecía sin freno hasta valores absurdos.
            if self.cht_c > LIM["cht_max"]:
                castigo = limitar((self.cht_c - LIM["cht_max"]) / 60.0, 0.0, 1.0)
                self.pot_entregada *= mezclar(1.0, 0.55, castigo)
        else:
            self.pot_entregada = 0.0

        # --- Carga total sobre el ciguenal -----------------------------------
        #   * el rotor, SOLO si el embrague está acoplado
        #   * accesorios (generador, bombas, magnetos)
        #   * fricción y bombeo, que crecen con el cuadrado de las RPM
        # Ese último término es el que hace que el motor tenga un régimen de
        # equilibrio estable para cada posición de mariposa.
        carga = (self.pot_requerida if self.acoplado else 0.04)
        carga += 0.04 + 0.14 * (self.n_eng_rpm / 2200.0) ** 2

        # --- Aporte del arrancador -------------------------------------------
        # Se desacopla solo por encima de 900 RPM (embrague de rueda libre del
        # arrancador). Mientras está engranado suma par al balance.
        # El arrancador sigue girando con la barra muy caída: es justamente lo
        # que pasa cuando se lo usa, la barra baja a 18 V y el motor de
        # arranque igual arrastra. Se lo corta a 15 V, que es donde ya no da.
        self.arranque_activo = (ctl.arrancador and self.bus_v > 15.0
                                and self.n_eng_rpm < 900.0)
        # Par de un motor serie: máximo parado y cayendo con la velocidad. Con
        # la carga de fricción del radial, el equilibrio queda cerca de las
        # 230 RPM, que es la velocidad de arrastre real de un R-1340. Esa es
        # la aguja del tacómetro subiendo despacio ANTES de que el motor
        # encienda: primero arrastra, después prende.
        if self.arranque_activo:
            p_arrancador = 0.055 + 0.30 * limitar(1.0 - self.n_eng_rpm / 250.0, 0.0, 1.0)
        else:
            p_arrancador = 0.0

        # --- RPM del motor: BALANCE DE PAR -----------------------------------
        # Si sobra potencia el motor acelera, si falta se frena. No hay ninguna
        # tabla "mariposa -> RPM": las RPM SALEN del balance. Por eso la presión
        # de admisión en crucero termina siendo la que corresponde a la potencia
        # realmente necesaria, y no un número elegido a mano. Es también lo que
        # hace que subir el mando de paso colectivo, por si solo, frene el rotor.
        if motor_vivo or self.arranque_activo:
            exceso = self.pot_entregada + p_arrancador - carga
            rpm_obj = self.n_eng_rpm + exceso * 1800.0
            rpm_obj = limitar(rpm_obj, 0.0, LIM["rpm_motor_max"] + 200.0)
            self.n_eng_rpm = aproximar(self.n_eng_rpm, rpm_obj, dt, 0.9)
        else:
            # Motor apagado: si está acoplado, el rotor lo arrastra un poco;
            # si no, se detiene por fricción.
            if self.acoplado and self.n_rot_rpm > 20.0:
                self.n_eng_rpm = aproximar(self.n_eng_rpm,
                                           self.n_rot_rpm * LIM["reduccion"] * 0.15,
                                           dt, 2.5)
            else:
                self.n_eng_rpm = aproximar(self.n_eng_rpm, 0.0, dt, 3.5)

        self.n_eng_rpm = limitar(self.n_eng_rpm, 0.0, 3200.0)
        self.motor_vivo = motor_vivo

    def _paso_hielo_carburador(self, dt):
        """
        Engelamiento de carburador: la falla clásica del R-1340.
        La expansión en el venturi enfría el aire ~15 C. Si la temperatura
        resultante cae en la banda de riesgo Y hay humedad, se forma hielo
        que estrangula la admisión -> cae la MAP -> cae la potencia.
        La calefacción de carburador lo derrite.
        """
        # La depresión del venturi es MÁXIMA con la mariposa casi cerrada y
        # mínima a plena admisión. Por eso el aire del carburador está más
        # frío a baja potencia, y el engelamiento de carburador es un
        # fenómeno de descenso y de aproximación, no de despegue.
        # Sin motor girando no pasa aire por el carburador: no hay venturi, no
        # hay evaporación de combustible y el termómetro lee sencillamente la
        # temperatura exterior.
        aspirando = limitar(self.n_eng_rpm / 400.0, 0.0, 1.0)
        caida_venturi = 18.0 * (1.0 - 0.72 * self.ctl.throttle) * aspirando
        self.cat_c = aproximar(
            self.cat_c,
            self.oat_c - caida_venturi + 55.0 * self.ctl.calefaccion_carb,
            dt, 1.2)

        # El hielo se forma más rápido cuanto más profunda es la depresión,
        # o sea cuanto MENOS potencia se lleva.
        rel_baja_pot = 0.4 + 1.2 * (1.0 - self.ctl.throttle)
        en_banda = (LIM["cat_hielo_min"] <= self.cat_c <= LIM["cat_hielo_max"])
        if en_banda and self.humedad > 0.55 and self.n_eng_rpm > 500.0:
            self.hielo_carb = limitar(
                self.hielo_carb + (self.humedad - 0.5) * 0.020 * rel_baja_pot * dt,
                0.0, 1.0)
        else:
            # se derrite: rápido con calefacción, lentísimo sin ella
            k = 0.12 if self.ctl.calefaccion_carb > 0.5 else 0.012
            self.hielo_carb = limitar(self.hielo_carb - k * dt, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 3. ROTOR PRINCIPAL  (la única integración diferencial del modelo)
    # -----------------------------------------------------------------------
    def _paso_rotor(self, dt):
        ctl = self.ctl
        s = self.salud

        # --- Potencia requerida por el rotor -------------------------------
        # Curva en U, la firma inconfundible de un helicóptero:
        #   * potencia INDUCIDA: enorme en estacionario, cae al ganar
        #     velocidad de traslación (el rotor "encuentra aire fresco")
        #   * potencia de PERFIL: casi constante, es el arrastre de las palas
        #   * potencia PARASITA: crece con el cubo de la velocidad
        # El mínimo está alrededor de 45-55 kt: por eso esa es la velocidad
        # de máxima autonomía y la de mejor planeo en autorrotación.
        v = self.ias_kt
        induc = 0.47 * (1.0 - limitar(v / 50.0, 0.0, 1.0)) ** 2
        parasita = 0.31 * (v / 95.0) ** 3
        perfil = 0.24
        req = perfil + induc + parasita
        req *= (0.35 + 1.05 * ctl.colectivo)          # el mando de paso colectivo manda
        req *= (1.0 + self.alt_ft / 22000.0)          # menos densidad, más potencia
        # La potencia que consume el rotor depende de su propio régimen: el
        # arrastre de las palas crece con el cuadrado de la velocidad de giro.
        # Un rotor lento pide menos potencia -y por eso también sustenta
        # menos-. A régimen nominal este factor vale 1 y no cambia nada; solo
        # aparece cuando el rotor se sale de su banda, que es justo donde hace
        # falta para que el sistema encuentre un equilibrio en vez de caer a
        # cero de golpe.
        rel_rot = limitar(self.n_rot_rpm / LIM["rpm_rotor_nom"], 0.0, 1.25)
        req *= mezclar(0.30, 1.0, rel_rot * rel_rot)
        self.pot_requerida = limitar(req, 0.0, 1.6)

        # --- Rueda libre / embrague ---------------------------------------
        # El rotor NUNCA arrastra al motor: si el rotor gira más rápido que
        # el motor dividido 10, la rueda libre desacopla. Esa es la
        # autorrotación, y es lo que produce el "needle split".
        n_rot_motor = self.n_eng_rpm / LIM["reduccion"]
        # Histéresis: una rueda libre real no "castañetea" en el punto de
        # enganche. Una vez acoplada aguanta un poco de rotor adelantado antes
        # de soltar, y una vez suelta necesita que el motor la alcance con
        # margen para volver a tomar. Sin esto el estado oscilaba en crucero y
        # arrastraba a todo lo que depende de él.
        margen = 2.5 if self.acoplado else -0.4
        self.acoplado = bool(ctl.embrague and s.embrague > 0.1
                             and self.motor_vivo
                             and n_rot_motor >= self.n_rot_rpm - margen)

        # --- Potencia entrante al rotor ------------------------------------
        # CAPACIDAD DE PAR DEL EMBRAGUE. Un embrague sano pasa todo lo que el
        # motor entregue. Uno gastado tiene un TECHO: por encima de ese valor
        # no transmite más, simplemente patina más. Si el techo queda por
        # debajo de lo que pide el rotor, el rotor se frena hasta que las dos
        # cosas se igualan, y ahí se queda: el motor a su régimen, el rotor
        # abajo, y las dos agujas separadas de forma estable.
        if self.acoplado:
            p_in = min(self.pot_entregada, s.embrague * 1.25)
        else:
            p_in = 0.0

        # En autorrotación el flujo ascendente a traves del disco devuelve
        # energía al rotor, proporcional a la velocidad de descenso.
        if not self.acoplado and self.vs_fpm < 0.0:
            p_in += self.K_AUTOROT * limitar(-self.vs_fpm / 1800.0, 0.0, 1.2)

        # --- Ecuación del rotor ---------------------------------------------
        #   dOmega/dt = (P_in - P_req) / (I * Omega)
        omega = max(self.n_rot_rpm, 12.0)
        d_omega = (p_in - self.pot_requerida) * self.K_INERCIA_ROTOR / omega
        # límite de aceleración: un rotor de 16 m no cambia de régimen de golpe
        d_omega = limitar(d_omega, -55.0, 45.0)
        self.n_rot_rpm = limitar(self.n_rot_rpm + d_omega * dt, 0.0, 300.0)

        # --- Resbalamiento del embrague -------------------------------------
        # Un embrague de fricción SOLO transmite par mientras haya una
        # diferencia de velocidad entre sus dos caras. Con el embrague sano esa
        # diferencia es despreciable, la transmisión impone la relación 10:1 y
        # las dos agujas del tacómetro doble van perfectamente superpuestas.
        #
        # A medida que el embrague se gasta hace falta cada vez MÁS diferencia
        # de velocidad para pasar el mismo par: el motor mantiene su régimen y
        # el rotor se queda atrás. Las dos agujas se separan CON EL MOTOR
        # ANDANDO, que es un síntoma distinto del needle split de la
        # autorrotación -donde la que cae es la aguja de motor y la de rotor
        # queda arriba-. Confundirlos es el error clásico, y por eso el H-19
        # lleva las dos agujas en una sola esfera: para poder compararlas.
        #
        # La separación crece con la potencia pedida: aumenta al subir
        # colectivo y se achica al bajarlo, que es justamente el procedimiento.
        if self.acoplado and s.embrague >= 0.98 and self.n_rot_rpm < n_rot_motor:
            self.n_rot_rpm = aproximar(self.n_rot_rpm, n_rot_motor, dt, 0.5)

        if not ctl.embrague:
            self.n_rot_rpm = aproximar(self.n_rot_rpm, 0.0, dt, 25.0)

    # -----------------------------------------------------------------------
    # 4. FLUIDOS DEL MOTOR
    # -----------------------------------------------------------------------
    def _paso_fluidos(self, dt):
        s = self.salud
        rel_rpm = self.n_eng_rpm / LIM["rpm_motor_crucero"]

        # --- Presión de aceite -----------------------------------------------
        # Depende de dos cosas: del régimen, porque la bomba es de engranajes
        # arrastrada por el motor, y de la VISCOSIDAD del aceite.
        #
        # Con el aceite helado, recién puesto en marcha, el aceite es una
        # melaza y la presión se va muy arriba: es normal ver la aguja cerca
        # del tope en los primeros minutos, y verla BAJAR sola a medida que el
        # aceite toma temperatura. Con el aceite caliente, en ralentí, la
        # presión es bastante más baja que en crucero.
        #
        # La regla de oro del radial: si a los 30 segundos de arrancar la
        # aguja no se movió, se corta el motor.
        if self.n_eng_rpm < 100.0:
            p_obj = 0.0
        else:
            # La viscosidad del aceite manda sobre la presión, en los DOS
            # extremos. Frío y espeso, la bomba no lo deja pasar y la aguja se
            # clava contra la válvula de alivio. Caliente y fluido, se escurre
            # por los mismos huecos y la presión BAJA: por eso una
            # sobretemperatura de aceite termina apareciendo también en el
            # manómetro, y por eso las dos agujas se leen juntas.
            viscosidad = 1.0 + 1.05 * limitar((45.0 - self.oil_t_c) / 45.0, 0.0, 1.0)
            viscosidad -= 0.45 * limitar(
                (self.oil_t_c - LIM["oil_t_max"]) / 35.0, 0.0, 1.0)
            p_obj = LIM["oil_p_nom"] * (limitar(rel_rpm, 0.0, 1.3) ** 1.15)
            p_obj *= s.bomba_aceite * viscosidad
            # Válvula de alivio: el radial NO deja subir la presión sin
            # límite. Con el aceite helado la aguja se clava contra el valor
            # de alivio y se queda ahí hasta que el aceite afloja.
            p_obj = limitar(p_obj, 0.0, LIM["oil_p_max"] * 1.02)
        self.oil_p_psi = aproximar(self.oil_p_psi, p_obj, dt, 0.55)

        # --- Temperatura de aceite y de culata ------------------------------
        # El H-19 lleva un ventilador de refrigeración accionado por el propio
        # motor, así que la refrigeración NO depende solo de la velocidad de
        # traslación. Aun así, en estacionario prolongado el radial se
        # recalienta: es la limitación operativa clásica del tipo.
        #
        # Se usa exponente 0,42 sobre la potencia porque la temperatura de
        # culata crece mucho más despacio que la potencia (la mezcla se
        # enriquece y el ventilador también acelera).
        flujo_ias = limitar(self.ias_kt / 70.0, 0.0, 1.0)
        pot = limitar(self.pot_entregada, 0.0, 1.4)
        vivo = limitar(self.n_eng_rpm / 700.0, 0.0, 1.0)

        cht_obj = self.oat_c + vivo * (245.0 * (pot ** 0.42) + 25.0 * (1.0 - flujo_ias))
        # Con un solo magneto la combustión es más lenta e incompleta: la
        # mezcla sigue quemándose cuando se abre la válvula de escape. Son
        # unos 15 C más de culata, y es la razón por la que la prueba de
        # magnetos se hace CORTA y no se vuela con uno solo si se puede evitar.
        if self.n_magnetos == 1:
            cht_obj += 15.0 * vivo
        if s.refrigeracion < 1.0:
            cht_obj = self.oat_c + (cht_obj - self.oat_c) / max(s.refrigeracion, 0.20)
        # TECHO FÍSICO. Sin este límite la cuenta da 500 y 600 C, que no
        # existen: mucho antes de eso el aluminio de la cabeza se ablanda, la
        # detonación destruye el pistón y el motor se para. Se corta en el
        # fondo de escala del instrumento porque es lo que ve el piloto: la
        # aguja contra el tope, que ya no informa CUÁNTO, sino que se acabó.
        cht_obj = limitar(cht_obj, self.oat_c, LIM["cht_escala"])
        self.cht_c = aproximar(self.cht_c, cht_obj, dt, 55.0)

        # El aceite se lleva el calor del motor y lo entrega en su propio
        # radiador. Su temperatura sigue a la de culata, más abajo y con mucho
        # más retardo: el aceite es una masa térmica grande y por eso su aguja
        # es la última en moverse y la última en volver.
        oil_obj = self.oat_c + 0.28 * (self.cht_c - self.oat_c)
        if s.refrigeracion_aceite < 1.0:
            oil_obj = self.oat_c + (oil_obj - self.oat_c) / max(
                s.refrigeracion_aceite, 0.25)
        oil_obj = limitar(oil_obj, self.oat_c, LIM["oil_t_escala"])
        self.oil_t_c = aproximar(self.oil_t_c, oil_obj, dt, 95.0)

        # --- Presión de combustible ------------------------------------------
        # La bomba eléctrica auxiliar sigue a la barra: con la barra caída da
        # menos caudal, no se apaga de golpe. Sin ella queda solo la bomba
        # mecánica del motor, que necesita que el motor gire.
        rel_bus = limitar((self.bus_v - 14.0) / (LIM["bus_min_util"] - 14.0), 0.0, 1.0)
        if self.ctl.bomba_combustible and rel_bus > 0.05:
            base = LIM["fuel_p_nom"] * mezclar(0.60, 1.0, rel_bus)
        else:
            base = LIM["fuel_p_nom"] * 0.55 * limitar(rel_rpm, 0.0, 1.0)
        if self._combustible_disponible() <= 0.5:
            base = 0.0
        self.fuel_p_psi = aproximar(self.fuel_p_psi,
                                    base * s.bomba_combustible, dt, 0.45)

    # -----------------------------------------------------------------------
    # 5. TRANSMISIÓN PRINCIPAL
    # -----------------------------------------------------------------------
    def _paso_transmision(self, dt):
        s = self.salud
        rel = self.n_rot_rpm / LIM["rpm_rotor_nom"]
        p_obj = LIM["xmsn_p_nom"] * (limitar(rel, 0.0, 1.3) ** 0.8) * s.transmision_bomba
        self.xmsn_p_psi = aproximar(self.xmsn_p_psi, p_obj, dt, 0.7)

        flujo_ias = limitar(self.ias_kt / 70.0, 0.0, 1.0)
        pot = limitar(self.pot_requerida, 0.0, 1.5)
        girando = limitar(self.n_rot_rpm / 120.0, 0.0, 1.0)
        t_obj = self.oat_c + girando * (115.0 * (pot ** 0.5) + 20.0 * (1.0 - flujo_ias))
        if s.transmision_refrig < 1.0:
            t_obj = self.oat_c + (t_obj - self.oat_c) / max(s.transmision_refrig, 0.20)
        # Sin presión de aceite la caja se calienta rapidísimo por fricción
        if self.xmsn_p_psi < LIM["xmsn_p_min"] and self.n_rot_rpm > 60.0:
            t_obj += 70.0 * (1.0 - self.xmsn_p_psi / LIM["xmsn_p_min"])
        # Calor del embrague que patina. Toda la potencia que el embrague NO
        # transmite se convierte en calor ahí adentro, y el bulbo de la caja es
        # el único instrumento que lo delata. Es lo que confirma que las dos
        # agujas del tacómetro se separaron por patinaje y no por otra cosa.
        if self.acoplado and s.embrague < 0.98:
            t_obj += 130.0 * (1.0 - s.embrague) * limitar(pot, 0.0, 1.2)
        # Mismo techo físico que la culata: la aguja llega al fondo de escala y
        # ahí se queda. Más allá no hay instrumento, hay caja destruida.
        t_obj = limitar(t_obj, self.oat_c, LIM["xmsn_t_escala"])
        self.xmsn_t_c = aproximar(self.xmsn_t_c, t_obj, dt, 110.0)

    # -----------------------------------------------------------------------
    # 6. COMBUSTIBLE
    # -----------------------------------------------------------------------
    def _combustible_disponible(self):
        sel = self.ctl.selector_tanque
        if sel == TANQUE_FWD:
            return self.fuel_fwd_l
        if sel == TANQUE_AFT:
            return self.fuel_aft_l
        return self.fuel_fwd_l + self.fuel_aft_l

    def _paso_combustible(self, dt):
        if self.n_eng_rpm > 200.0:
            self.flujo_lph = mezclar(LIM["consumo_min_lph"], LIM["consumo_max_lph"],
                                     limitar(self.pot_entregada, 0.0, 1.2))
        else:
            self.flujo_lph = 0.0

        # UNA FUGA NO ES UN CONSUMO. El motor consume del tanque SELECCIONADO;
        # una cañería rota pierde del tanque donde está la rotura, se haya
        # seleccionado o no. Por eso los dos aforadores dejan de bajar juntos y
        # empiezan a separarse: esa asimetría es lo que permite identificar el
        # tanque afectado y cerrarlo, que es justamente lo que pide el
        # procedimiento. Si la fuga se repartiera entre los dos tanques no
        # habría nada que identificar.
        fuga = self.salud.fuga_combustible_lph * dt / 3600.0
        if fuga > 0.0:
            self.fuel_fwd_l = max(0.0, self.fuel_fwd_l - fuga)

        consumo = self.flujo_lph * dt / 3600.0
        sel = self.ctl.selector_tanque
        if sel == TANQUE_FWD:
            self.fuel_fwd_l = max(0.0, self.fuel_fwd_l - consumo)
        elif sel == TANQUE_AFT:
            self.fuel_aft_l = max(0.0, self.fuel_aft_l - consumo)
        else:
            # de a mitades, pero si un tanque se agota el otro toma todo
            if self.fuel_fwd_l > 0.0 and self.fuel_aft_l > 0.0:
                self.fuel_fwd_l = max(0.0, self.fuel_fwd_l - consumo * 0.5)
                self.fuel_aft_l = max(0.0, self.fuel_aft_l - consumo * 0.5)
            elif self.fuel_fwd_l > 0.0:
                self.fuel_fwd_l = max(0.0, self.fuel_fwd_l - consumo)
            else:
                self.fuel_aft_l = max(0.0, self.fuel_aft_l - consumo)

    # -----------------------------------------------------------------------
    # 7. DINÁMICA DE VUELO
    # -----------------------------------------------------------------------
    def _paso_vuelo(self, dt):
        ctl = self.ctl
        s = self.salud

        # --- Empuje del rotor ------------------------------------------------
        # El empuje va con el CUADRADO de las RPM: por eso perder régimen de rotor
        # es tan grave. La escala está elegida para que el estacionario quede
        # con el mando de paso colectivo a mitad de recorrido (empuje = 1,0 a col = 0,552),
        # que es como se siente un helicóptero real.
        rel_rpm = self.n_rot_rpm / LIM["rpm_rotor_nom"]
        empuje = (rel_rpm ** 2) * (0.42 + 1.05 * ctl.colectivo)
        empuje *= (1.0 - self.alt_ft / 30000.0)
        self.empuje = empuje

        # --- Velocidad vertical ---------------------------------------------
        # Modelo cuasi-estático: el exceso de empuje define la velocidad
        # vertical de RÉGIMEN, y la aeronave la alcanza con una constante de
        # tiempo de 1,4 s. Es estable con cualquier paso de integración.
        vs_obj = limitar(self.K_VERT * (empuje - 1.0), -2400.0, 1600.0)

        # En AUTORROTACIÓN el régimen de descenso no lo fija el exceso de
        # empuje: lo fija el balance de energía. La aeronave tiene que bajar lo
        # suficiente como para que el flujo ascendente a través del disco
        # mantenga girando el rotor. Para el S-55 eso son del orden de 1500 a
        # 1800 ft/min, no los 500 que da la fórmula de empuje.
        #
        # Es un número que conviene que el alumno vea: desde 800 ft, a 1600
        # ft/min, hay treinta segundos para elegir dónde poner la máquina.
        autorrotando = ((not self.acoplado) and (not self.en_tierra)
                        and self.n_rot_rpm > 60.0
                        and self.pot_entregada < 0.08)
        if autorrotando:
            vs_auto = -(self.pot_requerida / max(self.K_AUTOROT, 0.05)) * 1800.0
            vs_obj = limitar(min(vs_obj, vs_auto), -2400.0, 0.0)

        # Contacto con el suelo: no se puede descender por debajo del terreno,
        # y estando apoyado el variómetro debe marcar CERO (si no, con el motor
        # apagado el instrumento indicaría un descenso inexistente).
        if self.alt_ft <= self.alt_terreno_ft + 0.05 and vs_obj < 0.0:
            vs_obj = 0.0
            self.vs_fpm = aproximar(self.vs_fpm, 0.0, dt, 0.5)
        else:
            self.vs_fpm = aproximar(self.vs_fpm, vs_obj, dt, 1.4)

        self.alt_ft += self.vs_fpm / 60.0 * dt
        if self.alt_ft <= self.alt_terreno_ft:
            self.alt_ft = self.alt_terreno_ft
            if self.vs_fpm < 0.0:
                self.vs_fpm = 0.0
            self.en_tierra = True
        else:
            self.en_tierra = False

        # --- Velocidad indicada ----------------------------------------------
        # El cíclico longitudinal fija una ACTITUD de cabeceo, y la actitud
        # fija la velocidad de equilibrio. Convenio de signos:
        #     ciclico_lon > 0  ->  nariz abajo (pitch negativo)  ->  acelera
        pitch_obj = -12.0 * ctl.ciclico_lon
        self.pitch_deg = aproximar(self.pitch_deg, pitch_obj, dt, 0.9)
        v_obj = limitar(-self.pitch_deg * 8.5, 0.0, 115.0)
        if self.en_tierra and empuje < 0.95:
            v_obj = 0.0
        self.ias_kt = aproximar(self.ias_kt, v_obj, dt, self.TAU_IAS)
        self.ias_kt = limitar(self.ias_kt, 0.0, 130.0)

        # --- Alabeo y viraje --------------------------------------------------
        roll_obj = 30.0 * ctl.ciclico_lat
        self.roll_deg = aproximar(self.roll_deg, roll_obj, dt, 0.8)
        if self.ias_kt > 8.0:
            # tasa de viraje = 1091 * tan(alabeo) / V   [grados/s, V en kt]
            self.turn_rate_dps = 1091.0 * _tan_grados(self.roll_deg) / max(self.ias_kt, 15.0)
        else:
            # en estacionario, el rotor de cola es el que hace guinar
            self.turn_rate_dps = 12.0 * ctl.pedal * s.rotor_cola

        # --- Pérdida de rotor de cola ------------------------------------------
        # El par del rotor principal ya no se compensa: guinada incontrolada
        # hacia la derecha (rotor que gira a izquierda visto desde arriba).
        #
        # QUÉ PAR ES EL QUE HACE GUIÑAR. Es el que la TRANSMISIÓN le entrega al
        # rotor, no el que el rotor consume del aire. Con la rueda libre
        # desacoplada -o sea, en autorrotación- el árbol no transmite par y la
        # reacción sobre el fuselaje desaparece: la guiñada se detiene sola y
        # la bola vuelve al centro. Eso es exactamente lo que hace que el
        # procedimiento ante una pérdida de rotor de cola sea ENTRAR EN
        # AUTORROTACIÓN, y es la parte que hay que poder mostrar en el tablero.
        # Usando la potencia requerida por el rotor -que en autorrotación sigue
        # siendo alta- la guiñada no paraba nunca y el procedimiento no tenía
        # ningún efecto visible.
        #
        # A velocidad de traslación el estabilizador vertical aporta además una
        # cuota de estabilidad direccional, así que la guiñada queda lenta pero
        # incontenible en vez de convertirse en un trompo. Por eso el manual
        # insiste en MANTENER VELOCIDAD.
        if s.rotor_cola < 0.95:
            par_motor = self.pot_entregada if self.acoplado else 0.0
            ayuda_deriva = 1.0 - 0.45 * limitar(self.ias_kt / 74.0, 0.0, 1.0)
            par_no_compensado = ((1.0 - s.rotor_cola) * par_motor
                                 * 26.0 * ayuda_deriva)
            self.turn_rate_dps += par_no_compensado
            self.slip = aproximar(
                self.slip,
                limitar((1.0 - s.rotor_cola) * 1.4 * limitar(par_motor / 0.45, 0.0, 1.0),
                        -1.0, 1.0),
                dt, 1.0)
        else:
            slip_obj = limitar(ctl.pedal * 0.35 - self.roll_deg * 0.006, -1.0, 1.0)
            self.slip = aproximar(self.slip, slip_obj, dt, 1.2)

        self.hdg_deg = (self.hdg_deg + self.turn_rate_dps * dt) % 360.0

        # --- Radionavegación (simplificada) -------------------------------------
        # Desviación respecto de un radial de referencia de 090 grados.
        err = ((self.hdg_deg - 90.0 + 180.0) % 360.0) - 180.0
        self.cdi = limitar(err / 12.0, -5.0, 5.0)


def _tan_grados(g):
    """Tangente para ángulos chicos, por serie, sin importar math."""
    r = g * 0.017453292519943295
    # serie de Taylor: valida y precisa hasta ~60 grados
    r2 = r * r
    return r * (1.0 + r2 / 3.0 + 2.0 * r2 * r2 / 15.0)


# ===========================================================================
# PILOTO VIRTUAL
# ===========================================================================
class PilotoVirtual:
    """
    Controlador que mueve los mandos para cumplir un objetivo de vuelo.

    Existe para que el modelo físico sea el ÚNICO que decide los valores de
    los instrumentos. La alternativa - escribir directamente "altímetro = 1500"
    - produciría un tablero incoherente en cuanto apareciera una falla.
    Acá el piloto pide, la física responde, y si la física no puede (porque el
    motor fallo) las agujas lo muestran solas.

    También permite el ejercicio didáctico inverso: DESACTIVAR el piloto
    durante una falla para mostrar qué pasa si nadie reacciona.
    """

    def __init__(self, modelo):
        self.m = modelo
        self.activo = True
        self.reacciona_a_fallas = True

        self.alt_obj_ft = 0.0
        self.ias_obj_kt = 0.0
        self.hdg_obj_deg = 90.0
        self.rpm_obj = LIM["rpm_motor_crucero"]

        self._i_alt = 0.0
        self._i_ias = 0.0
        self._i_thr = 0.5

    def objetivos(self, alt=None, ias=None, hdg=None, rpm=None):
        if alt is not None:
            self.alt_obj_ft = alt
        if ias is not None:
            self.ias_obj_kt = ias
        if hdg is not None:
            self.hdg_obj_deg = hdg
        if rpm is not None:
            self.rpm_obj = rpm

    def paso(self, dt):
        if not self.activo:
            return
        m = self.m
        ctl = m.ctl

        # ---- Detección de emergencia: motor caido en vuelo -----------------
        emergencia = (self.reacciona_a_fallas and not m.en_tierra
                      and m.pot_entregada < 0.12 and m.n_rot_rpm > 40.0)

        if emergencia:
            # AUTORROTACIÓN: bajar colectivo a fondo para conservar RPM de
            # rotor, y buscar la velocidad de mínimo régimen de descenso.
            ctl.colectivo = rampa(ctl.colectivo, 0.06, dt, 0.9)
            objetivo_v = 52.0
            ctl.ciclico_lon = rampa(ctl.ciclico_lon,
                                    limitar(objetivo_v / 8.5 / 12.0, -1.0, 1.0),
                                    dt, 0.4)
            ctl.ciclico_lat = rampa(ctl.ciclico_lat, 0.0, dt, 0.5)
            return

        # ---- Control de altitud mediante colectivo --------------------------
        # Lazo en cascada: error de altura -> velocidad vertical deseada ->
        # posición de colectivo. Es como vuela una persona: primero decide
        # cuanto quiere subir, después cuanto tira de la palanca.
        err_alt = self.alt_obj_ft - m.alt_ft
        vs_deseada = limitar(err_alt * 0.9, -700.0, 700.0)
        err_vs = vs_deseada - m.vs_fpm
        self._i_alt = limitar(self._i_alt + err_vs * dt * 0.000060, -0.35, 0.35)
        col_obj = 0.55 + err_vs * 0.00025 + self._i_alt
        # Si el rotor se está frenando, insistir con el mando de paso colectivo solo empeora
        # las cosas: más paso = más resistencia = menos RPM. Se afloja.
        if m.n_rot_rpm < LIM["rpm_rotor_min"]:
            col_obj -= 0.30
        ctl.colectivo = rampa(ctl.colectivo, limitar(col_obj, 0.0, 1.0), dt, 0.55)

        # ---- Gobernador de RPM (mariposa) ------------------------------------
        # PI puro sobre el error de RPM del motor. El término integral ES la
        # posición de reposo de la mariposa, por eso se guarda entre ciclos.
        # Un gobernador así encuentra solo el punto correcto tanto en
        # estacionario (mucha potencia) como en crucero (poca), sin necesidad
        # de tabla de correlación.
        err_rpm = self.rpm_obj - m.n_eng_rpm
        self._i_thr = limitar(self._i_thr + err_rpm * dt * 0.00018, 0.05, 1.0)
        thr_obj = limitar(self._i_thr + err_rpm * 0.00009, 0.05, 1.0)
        ctl.throttle = rampa(ctl.throttle, thr_obj, dt, 0.6)

        # ---- Control de velocidad mediante cíclico longitudinal --------------
        err_ias = self.ias_obj_kt - m.ias_kt
        self._i_ias = limitar(self._i_ias + err_ias * dt * 0.0010, -0.30, 0.30)
        lon_obj = (self.ias_obj_kt / 8.5) / 12.0 + err_ias * 0.0030 + self._i_ias
        ctl.ciclico_lon = rampa(ctl.ciclico_lon, limitar(lon_obj, -1.0, 1.0), dt, 0.35)

        # ---- Control de rumbo mediante cíclico lateral ------------------------
        # SIN ROTOR DE COLA EL PILOTO NO PERSIGUE EL RUMBO. Un helicóptero
        # girando por par no compensado no se endereza con el cíclico: el
        # cíclico inclina el disco y hace virar, que es otro eje y otro
        # fenómeno. Si el piloto virtual siguiera corrigiendo, terminaría
        # inclinando la máquina hasta anular la guiñada en el papel, y el
        # tablero mostraría un rumbo tranquilo en plena pérdida de rotor de
        # cola: exactamente lo contrario de lo que hay que enseñar. Lo que
        # hace un piloto real es dejar de pelear el rumbo, mantener velocidad
        # y entrar en autorrotación.
        if m.salud.rotor_cola < 0.95:
            ctl.ciclico_lat = rampa(ctl.ciclico_lat, 0.0, dt, 0.5)
            ctl.pedal = rampa(ctl.pedal, 0.0, dt, 0.8)
            return

        err_hdg = ((self.hdg_obj_deg - m.hdg_deg + 180.0) % 360.0) - 180.0
        lat_obj = limitar(err_hdg * 0.035, -1.0, 1.0)
        if m.ias_kt < 12.0:
            ctl.ciclico_lat = rampa(ctl.ciclico_lat, 0.0, dt, 0.5)
            ctl.pedal = rampa(ctl.pedal, limitar(err_hdg * 0.06, -1.0, 1.0), dt, 1.0)
        else:
            ctl.ciclico_lat = rampa(ctl.ciclico_lat, lat_obj, dt, 0.5)
            ctl.pedal = rampa(ctl.pedal, 0.0, dt, 0.8)
