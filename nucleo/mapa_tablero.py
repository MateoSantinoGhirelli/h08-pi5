# -*- coding: utf-8 -*-
"""
mapa_tablero.py - del valor de ingeniería al actuador físico
=============================================================

Es la frontera entre "lo que el helicóptero está haciendo" y "cuánto hay que
mover el servo del canal 7 de la placa 0". Hace cuatro cosas, en orden:

  1. CALIBRACIÓN
     Convierte el valor indicado (psi, kt, RPM, °C) en un ángulo de actuador
     con la tabla a trozos de configuracion.TABLERO. Es lo único que hay que
     tocar cuando la aguja no cae justo en la marca.

  2. DINÁMICA DE AGUJA
     Aplica inercia (tau) y límite de velocidad (slew). Una aguja real tiene
     masa: sin esto un servo saltaría de 0 a 180 grados en un ciclo, con un
     pico de corriente y un movimiento que se ve falso.

  3. BANDA MUERTA
     No escribe al hardware si el cambio es menor que un umbral. En crucero
     estabilizado la mayoría de los canales no cambian, y el tráfico por el
     bus I2C baja a una fracción.

  4. DESPACHO
     Llama al método que corresponde según el tipo de actuador (servo, luz o
     paso a paso), sin saber qué placa hay abajo.

ARRANQUE ESCALONADO
     En la primera escritura todos los canales están "sin escribir", así que
     los veintidós servos arrancarían en el mismo ciclo. Un servo pide unos
     700 mA mientras arranca: veintidós juntos superan cualquier fuente del
     tablero y los PCA9685 se reiniciarían por baja tensión. Por eso los
     canales se liberan de a tandas chicas (configuracion.ARRANQUE).
"""

from utiles import aproximar, rampa, interpolar_tabla
from configuracion import (TABLERO, LAZO, MOTOR, LED, ARRANQUE, BARRIDO,
                           factor_servo)
from senales import envolver


class Canal:
    """Un actuador físico del tablero."""

    __slots__ = ("id", "senal", "tipo", "cal", "tau", "slew", "factor",
                 "ang", "ang_escrito", "destino", "activo", "nombre", "circular")

    def __init__(self, d):
        self.id = d["id"]
        self.nombre = d["nombre"]
        self.senal = d["senal"]
        self.tipo = d["actuador"]
        self.cal = d["cal"]
        self.tau = d.get("tau", 0.4)
        self.slew = d.get("slew", 180.0)
        self.destino = d.get("canal")
        self.activo = self.destino is not None
        # De ángulo de la tabla a ángulo del actuador. La tabla de calibración
        # está escrita como si la esfera midiera 180 grados; este factor la
        # lleva al recorrido que hace el servo. Con barrido de 270 o 300 el
        # factor es 1 y el resto lo hacen los engranajes; con barrido de 120
        # el factor es 0,667 y el servo usa dos tercios de su recorrido.
        self.factor = factor_servo(self.id)
        # Giro continuo (altímetro de centenas y brújula): el ángulo vive en
        # 0..360 y los cambios se miden por el camino corto.
        self.circular = BARRIDO.get(self.id) == "CONT"
        # Se arranca en el ángulo del mínimo de escala
        self.ang = self.cal[0][1]
        self.ang_escrito = -9999.0


class MapaTablero:
    """Conjunto de canales + lógica de actualización y escritura."""

    def __init__(self, actuadores):
        self.actuadores = actuadores
        self.canales = []
        self.por_id = {}
        self.test_luces = False        # prueba de lámparas
        self._t = 0.0
        self._escrituras = 0
        self._omitidas = 0

        for d in TABLERO:
            c = Canal(d)
            self.canales.append(c)
            self.por_id[c.id] = c

        # Banda muerta en grados, a partir de la resolución del PCA9685:
        # 4096 cuentas son 20 ms, y un servo usa 500..2500 us, o sea unas 410
        # cuentas para 180 grados.
        cuentas = LAZO["banda_muerta"]
        self.banda_deg = max(0.15, 180.0 * cuentas / 410.0)

        self.arranque_grupo = ARRANQUE["canales_por_tanda"]
        self.arranque_paso = ARRANQUE["segundos_entre_tandas"]
        self._encolar_arranque()

    # -- arranque escalonado --------------------------------------------------
    def _encolar_arranque(self):
        """Arma la cola del arranque: primero lo que casi no consume."""
        def peso(c):
            # luces y paso a paso primero (miliamperes), servos después
            return (0 if c.tipo in (LED, MOTOR) else 1,
                    self.canales.index(c))
        self._cola = sorted([c for c in self.canales if c.activo], key=peso)
        self._sueltos = set()
        self._prox_tanda = 0.0

    def _soltar_tanda(self):
        """Libera los canales a los que ya les toca escribir."""
        while self._cola and self._t >= self._prox_tanda:
            for _ in range(self.arranque_grupo):
                if not self._cola:
                    break
                self._sueltos.add(id(self._cola.pop(0)))
            self._prox_tanda = self._t + self.arranque_paso

    # =======================================================================
    def actualizar(self, bus, dt):
        """Calcula el ángulo objetivo de cada canal y lo mueve con inercia."""
        self._t += dt
        for c in self.canales:
            valor = bus.ver(c.senal, 0.0)

            if c.tipo == LED:
                # Las luces no tienen inercia. La prueba de lámparas las
                # enciende todas: es una función real de cabina y sirve para
                # verificar el cableado antes de una clase.
                c.ang = 1.0 if (self.test_luces or valor >= 0.5) else 0.0
                continue

            # Instrumentos de aguja: calibración + inercia + límite de velocidad
            objetivo = interpolar_tabla(valor, c.cal)
            if c.circular:
                objetivo = c.ang + envolver(objetivo - c.ang, 360.0)
            suave = aproximar(c.ang, objetivo, dt, c.tau)
            c.ang = rampa(c.ang, suave, dt, c.slew)
            if c.circular:
                c.ang %= 360.0

    # =======================================================================
    def escribir(self):
        """Vuelca al hardware sólo los canales que cambiaron."""
        actuadores = self.actuadores
        self._soltar_tanda()
        for c in self.canales:
            if not c.activo:
                continue
            if self._cola and id(c) not in self._sueltos:
                continue                       # todavía no le toca

            if c.tipo == LED:
                if c.ang != c.ang_escrito:
                    actuadores.escribir_led(c.destino, c.ang >= 0.5)
                    c.ang_escrito = c.ang
                    self._escrituras += 1
                else:
                    self._omitidas += 1
                continue

            # La banda muerta se mide sobre el ángulo que va al actuador, no
            # sobre el de la tabla: es el actuador el que se quiere ahorrar.
            objetivo = c.ang * c.factor
            cambio = objetivo - c.ang_escrito
            if c.circular and c.ang_escrito > -1000.0:
                cambio = envolver(cambio, 360.0)
            if abs(cambio) >= self.banda_deg * c.factor:
                if c.tipo == MOTOR:
                    actuadores.escribir_motor(c.destino, objetivo)
                else:
                    actuadores.escribir_servo(c.destino, objetivo)
                c.ang_escrito = objetivo
                self._escrituras += 1
            else:
                self._omitidas += 1

        actuadores.refrescar()

    # =======================================================================
    def estadisticas(self):
        total = self._escrituras + self._omitidas
        ahorro = 0.0 if total == 0 else 100.0 * self._omitidas / total
        return {"escrituras": self._escrituras,
                "omitidas": self._omitidas,
                "ahorro_pct": round(ahorro, 1)}

    def angulos(self):
        """Diccionario id -> ángulo actual, para la página web."""
        d = {}
        for c in self.canales:
            d[c.id] = round(c.ang, 2)
        return d

    def apagar(self):
        """Apaga las luces y fuerza la reescritura completa al reanudar."""
        for c in self.canales:
            if not c.activo:
                continue
            if c.tipo == LED:
                self.actuadores.escribir_led(c.destino, False)
            c.ang_escrito = -9999.0
        self._encolar_arranque()       # al reanudar también se escalona
        self.actuadores.refrescar()
