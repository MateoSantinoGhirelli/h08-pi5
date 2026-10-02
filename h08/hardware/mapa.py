# -*- coding: utf-8 -*-
"""La frontera entre «qué está haciendo el helicóptero» y «cuánto mover el servo 7».

De cada valor indicado (psi, kt, RPM, °C) saca el ángulo del actuador con la tabla
cal, le da inercia y límite de velocidad para que la aguja no salte, y escribe sólo
lo que cambió más que la banda muerta. No sabe qué placa hay abajo: despacha al
método que corresponde según el tipo de actuador.
"""

from h08.util import aproximar, rampa, interpolar_tabla
from h08.config import (TABLERO, LAZO, MOTOR, LED, ARRANQUE, BARRIDO,
                        factor_servo)
from h08.simulacion.senales import envolver


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
        # de ángulo de la tabla (escrita en 0..180) al recorrido real del servo
        self.factor = factor_servo(self.id)
        # Giro continuo (brújula, centenas del altímetro): el ángulo vive en 0..360
        # y los cambios se miden por el camino corto.
        self.circular = BARRIDO.get(self.id) == "CONT"
        self.ang = self.cal[0][1]          # arranca en el mínimo de escala
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

        # La banda muerta viene en cuentas del PCA9685 y acá se pasa a grados: 4096
        # cuentas son 20 ms y un servo usa 500..2500 us, o sea 410 cuentas para 180°.
        cuentas = LAZO["banda_muerta"]
        self.banda_deg = max(0.15, 180.0 * cuentas / 410.0)

        self.arranque_grupo = ARRANQUE["canales_por_tanda"]
        self.arranque_paso = ARRANQUE["segundos_entre_tandas"]
        self._encolar_arranque()

    def _encolar_arranque(self):
        """Arma la cola del arranque escalonado: primero lo que casi no consume.

        En la primera escritura ningún canal tiene ángulo escrito y arrancarían los
        20 servos juntos, a 700 mA cada uno (ver ARRANQUE en h08/config/hardware.py).
        """
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

    def actualizar(self, bus, dt):
        """Calcula el ángulo objetivo de cada canal y lo mueve con inercia."""
        self._t += dt
        for c in self.canales:
            valor = bus.ver(c.senal, 0.0)

            if c.tipo == LED:
                # sin inercia; la prueba de lámparas manda sobre la señal
                c.ang = 1.0 if (self.test_luces or valor >= 0.5) else 0.0
                continue

            objetivo = interpolar_tabla(valor, c.cal)
            if c.circular:
                objetivo = c.ang + envolver(objetivo - c.ang, 360.0)
            suave = aproximar(c.ang, objetivo, dt, c.tau)
            c.ang = rampa(c.ang, suave, dt, c.slew)
            if c.circular:
                c.ang %= 360.0

    def escribir(self):
        """Vuelca al hardware sólo los canales que cambiaron.

        En crucero estabilizado casi ninguno cambia, y el tráfico del bus I2C baja a
        una fracción (lo mide estadisticas()).
        """
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

            # sobre el ángulo que va al actuador, no sobre el de la tabla: es la
            # escritura al actuador la que se quiere ahorrar
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
