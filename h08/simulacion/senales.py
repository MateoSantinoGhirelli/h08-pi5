# -*- coding: utf-8 -*-
"""Lo que pasa de verdad y lo que marca la aguja, con el sensor en el medio.

Son dos cosas distintas: una falla de sistema cambia el valor real y una falla de
indicación cambia sólo lo que se ve. Distinguirlas es lo que se le enseña a un
técnico: antes de cortar el motor, ver si falló el motor o el instrumento. Entre
las dos está el modelo de sensor, con su retardo, su ruido y las anomalías que
inyectan las fallas (docs/modelo_vuelo.md).
"""

from h08.util import aproximar, limitar, RNG

# Modelo de sensor por señal:  (tau_segundos, amplitud_ruido_en_unidades)
# El ruido se calibró a ojo: un R-1340 es un radial de 9 cilindros, vibra
# mucho, y las agujas de presión tiemblan visiblemente.
SENSORES = {
    "ias_kt":        (0.30, 0.6),
    "alt_ind_ft":    (0.40, 4.0),
    "alt_centenas":  (0.40, 4.0),
    "vs_ind_fpm":    (1.80, 25.0),    # el VSI real tiene un retardo enorme
    "hdg_ind_deg":   (0.50, 0.4),
    "pitch_ind_deg": (0.15, 0.20),
    "roll_ind_deg":  (0.15, 0.25),
    "turn_rate_dps": (0.35, 0.06),
    "slip":          (0.30, 0.02),
    "n_eng_rpm":     (0.20, 12.0),    # vibración del radial
    "n_rot_rpm":     (0.25, 1.2),
    "map_inhg":      (0.20, 0.35),
    "oil_p_psi":     (0.30, 1.5),
    "oil_t_c":       (2.50, 0.4),
    "cht_c":         (2.00, 2.0),
    "cat_c":         (1.50, 0.5),
    "fuel_p_psi":    (0.30, 0.4),
    "fuel_fwd_l":    (2.00, 2.5),     # aforadores de flotante: lentos y sucios
    "fuel_aft_l":    (2.00, 2.5),
    "xmsn_p_psi":    (0.40, 1.0),
    "xmsn_t_c":      (3.00, 0.5),
    "bus_v":         (0.30, 0.10),
    "amp_a":         (0.50, 2.5),
    "cdi":           (0.80, 0.05),
}

# Señales CIRCULARES y su período. El rumbo pasa de 359 a 0 grados y la
# aguja de centenas del altímetro de 999 a 0 pies: para el filtro esos saltos
# no existen, la diferencia se mide por el camino corto. Si no, al cruzar el
# norte la rosa desandaría una vuelta entera hacia atrás.
CIRCULARES = {
    "hdg_ind_deg": 360.0,
    "alt_centenas": 1000.0,
}


def envolver(d, periodo):
    """Diferencia llevada a [-periodo/2, +periodo/2)."""
    return (d + periodo / 2.0) % periodo - periodo / 2.0


# Tipos de anomalía de INDICACIÓN que puede sufrir una señal
IND_CONGELADO = "congelado"   # la aguja se traba en el último valor
IND_FIJO = "fijo"             # la aguja va a un valor fijo (ej: 0 = transductor cortado)
IND_RUIDO = "ruido"           # aguja errática (mal contacto)
IND_OSCILA = "oscila"         # oscilación sinusoidal


class BusSenales:
    """
    Contenedor de las magnitudes del simulador.

    real[]     : lo que pasa físicamente (lo escribe el modelo de vuelo)
    indicado[] : lo que muestra el tablero (lo lee la capa de actuadores)
    """

    def __init__(self):
        self.real = {}
        self.indicado = {}        # lo que se ve: filtrado + ruido instantáneo
        self._filtrado = {}       # estado interno del filtro, SIN ruido
        self._anomalias = {}      # señal -> lista de dicts de anomalía
        self._fase_osc = 0.0
        self._inicializado = False

    # Ciclo de vida
    def poner(self, nombre, valor):
        self.real[nombre] = valor

    def obtener(self, nombre, por_defecto=0.0):
        return self.real.get(nombre, por_defecto)

    def ver(self, nombre, por_defecto=0.0):
        """Valor INDICADO (el que ve el piloto)."""
        return self.indicado.get(nombre, por_defecto)

    # Anomalías de indicación
    def limpiar_anomalias(self):
        self._anomalias = {}

    def agregar_anomalia(self, senal, tipo, valor=0.0):
        lst = self._anomalias.get(senal)
        if lst is None:
            lst = []
            self._anomalias[senal] = lst
        lst.append({"tipo": tipo, "valor": valor})

    def tiene_anomalia(self, senal):
        return senal in self._anomalias

    # Actualización
    def actualizar_indicaciones(self, dt, energia=1.0, vibracion=0.0):
        """
        Convierte real[] -> indicado[] aplicando:
          1. retardo de sensor (filtro de primer orden)
          2. ruido de vibración, PROPORCIONAL AL RÉGIMEN DEL MOTOR
          3. anomalías de indicación inyectadas por el motor de fallas
          4. pérdida de alimentación de los instrumentos eléctricos

        Se llama una vez por paso de simulación.

        El ruido se suma DESPUÉS del filtro y no se realimenta. Si entrara al
        filtro, la señal haría un paseo aleatorio con una desviación varias
        veces mayor que la del ruido declarado. Por eso se guardan dos
        estados: el filtrado limpio y el mostrado con ruido.

        El parámetro 'vibracion' (0..1.2) escala todo el ruido con las RPM del
        motor: un radial de 9 cilindros detenido no hace temblar ninguna aguja.
        """
        self._fase_osc += dt

        # 'energia' puede venir como 0..1 o como booleano. Un instrumento
        # eléctrico no se apaga de golpe al bajar la barra: indica cada vez
        # más bajo. Durante el arrastre del arrancador, con la barra en 18 V,
        # los aforadores marcan de menos y después se recuperan.
        if energia is True:
            factor_e = 1.0
        elif energia is False:
            factor_e = 0.0
        else:
            factor_e = limitar(float(energia), 0.0, 1.0)

        # Primera pasada: el indicado copia al real, para que las agujas no
        # salgan disparadas desde cero en el primer ciclo.
        if not self._inicializado:
            for k in self.real:
                self._filtrado[k] = self.real[k]
                self.indicado[k] = self.real[k]
            self._inicializado = True

        for nombre in self.real:
            valor = self.real[nombre]
            tau, ruido = SENSORES.get(nombre, (0.0, 0.0))
            previo = self._filtrado.get(nombre, valor)

            anomalias = self._anomalias.get(nombre)
            congelado = False
            extra_ruido = 0.0

            if anomalias:
                for a in anomalias:
                    t = a["tipo"]
                    if t == IND_CONGELADO:
                        congelado = True
                    elif t == IND_FIJO:
                        valor = a["valor"]
                        tau = 0.35          # la aguja igual tarda en llegar
                        ruido = 0.0
                    elif t == IND_RUIDO:
                        # el ruido de falla NO depende de la vibración del motor
                        extra_ruido += a["valor"]
                    elif t == IND_OSCILA:
                        # oscilación de ~0.8 Hz, típica de una aguja inestable
                        valor = valor + a["valor"] * _sin_aprox(self._fase_osc * 5.0)

            if congelado:
                # Se mantiene el último valor: pitot obstruido, estática
                # tapada, aguja mecánicamente trabada.
                self.indicado[nombre] = previo
                continue

            # Instrumentos alimentados eléctricamente: siguen a la barra.
            if factor_e < 1.0 and nombre in _SENALES_ELECTRICAS:
                valor = valor * factor_e
                tau = tau if tau > 1.2 else 1.2

            periodo = CIRCULARES.get(nombre)
            if periodo:
                valor = previo + envolver(valor - previo, periodo)
            filtrado = aproximar(previo, valor, dt, tau)
            if periodo:
                filtrado %= periodo
            self._filtrado[nombre] = filtrado

            amplitud = ruido * vibracion + extra_ruido
            if amplitud > 0.0:
                mostrado = filtrado + RNG.simetrico() * amplitud
            else:
                mostrado = filtrado
            self.indicado[nombre] = mostrado % periodo if periodo else mostrado


# Las señales que se caen con la barra. Las que no están acá siguen indicando sin
# energía porque son neumáticas, mecánicas o fabrican su propia corriente, y saber
# cuáles son es lo que permite volar con una falla eléctrica total: la lista con el
# instrumento de cada una está en docs/modelo_vuelo.md.
_SENALES_ELECTRICAS = (
    "oil_t_c", "cat_c",
    "fuel_fwd_l", "fuel_aft_l", "xmsn_p_psi", "xmsn_t_c",
    "cdi",
)


def _sin_aprox(x):
    """Seno aproximado de Bhaskara (error < 0,2 %), para la aguja que oscila."""
    # reducir a [-pi, pi]
    TWO_PI = 6.283185307179586
    PI = 3.141592653589793
    x = x % TWO_PI
    if x > PI:
        x -= TWO_PI
    neg = False
    if x < 0.0:
        x = -x
        neg = True
    y = (16.0 * x * (PI - x)) / (5.0 * PI * PI - 4.0 * x * (PI - x))
    return -y if neg else y
