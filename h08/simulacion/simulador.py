# -*- coding: utf-8 -*-
"""El único módulo que conoce a todos los demás: los tres modos y el lazo de 50 ms.

Corre el modo activo (vuelo normal por fases, escenario de emergencia o una falla
puntual), traduce el estado físico a señales del bus -incluida la lógica de las luces
de alerta, que es de aviso y no física- y publica la telemetría de la página.

El lazo es de tiempo fijo: se mira cuánto tiempo real pasó y se dan tantos pasos de
duración fija como haga falta, con un tope para que una demora del sistema operativo
no dispare una avalancha. Así la física es reproducible, no se acelera en una máquina
rápida ni se frena en una lenta, y las tres tasas (física, salida al hardware y
telemetría) quedan desacopladas.
"""

from h08.util import ticks_ms, ticks_diff, limitar
from h08.config import (LIM, LAZO, TABLERO, AERONAVE, ANUNCIADOR,
                        PANEL_VIRTUAL, PANEL_LIENZO, PANEL_ZONAS,
                        PANEL_CONMUTADORES, PANEL_PLACAS, BARRIDO,
                        CENTRO_ESCALA)
from h08.simulacion.senales import BusSenales
from h08.simulacion.modelo import ModeloVuelo, PilotoVirtual, MAG_OFF
from h08.simulacion.fallas import MotorFallas, CATALOGO, CATALOGO_POR_ID
from h08.simulacion.escenarios import PERFIL_NORMAL, ESCENARIOS, ESCENARIOS_POR_ID
from h08.hardware.mapa import MapaTablero

# Modos
MODO_NORMAL = 1
MODO_ESCENARIO = 2
MODO_FALLA = 3
MODO_DETENIDO = 0

NOMBRES_MODO = {
    0: "Detenido",
    1: "Vuelo normal controlado",
    2: "Escenario de emergencia",
    3: "Falla de sistema puntual",
}


class Simulador:

    def __init__(self, actuadores, semilla=None):
        self.modelo = ModeloVuelo()
        self.piloto = PilotoVirtual(self.modelo)
        self.bus = BusSenales()
        self.fallas = MotorFallas(self.modelo, self.bus)
        self.mapa = MapaTablero(actuadores)
        self.actuadores = actuadores

        self.dt = 1.0 / LAZO["hz_fisica"]
        self.modo = MODO_DETENIDO
        self.pausado = False
        self.velocidad = 1.0          # factor de tiempo (0.5 = cámara lenta)

        self.fase_idx = 0
        self.fase_t = 0.0
        self.ciclar = True            # el vuelo normal se repite en bucle

        self.escenario = None
        self.escenario_t = 0.0
        self.escenario_paso = 0

        self.mensajes = []            # últimos avisos didácticos
        self.t_sim = 0.0

        if semilla is not None:
            from h08.util import RNG
            RNG.sembrar(semilla)

        self._t_ultimo = ticks_ms()
        self._acum_ms = 0
        self._t_salida = 0.0
        self.per_salida = 1.0 / LAZO["hz_salida"]

    # Control de modos
    # Fases a las que no se puede llegar con la aeronave fría: si el docente
    # salta directamente a una de ellas desde la página, se deja el motor en
    # marcha y el rotor girando. Si no, el tablero quedaría en cero mostrando
    # el nombre de una fase de vuelo.
    FASES_CON_MOTOR = ("RALENTI", "EMBRAGUE", "RUNUP", "MAG_L", "MAG_BOTH", "MAG_R",
                       "DESPEGUE", "ASCENSO", "CRUCERO", "VIRAJE", "DESCENSO",
                       "APROXIMACION", "ESTACIONARIO", "ATERRIZAJE",
                       "ENFRIAMIENTO", "CORTE")

    def modo_normal(self, desde_fase=None):
        """MODO 1: vuelo completo, de aeronave fría a aeronave fría."""
        self.modo = MODO_NORMAL
        self.fallas.limpiar()
        self.modelo.reiniciar(en_frio=True)
        self.piloto.activo = False
        self.piloto.reacciona_a_fallas = True
        self.fase_idx = 0
        self.fase_t = 0.0
        self.mensajes = []

        if desde_fase is not None:
            for i in range(len(PERFIL_NORMAL)):
                if PERFIL_NORMAL[i]["id"] == desde_fase:
                    self.fase_idx = i
                    break
            self._condiciones_iniciales_de_fase(PERFIL_NORMAL[self.fase_idx])

        self._entrar_fase()
        self._msg("MODO 1 - Vuelo normal: " + PERFIL_NORMAL[self.fase_idx]["nombre"])

    def _condiciones_iniciales_de_fase(self, f):
        """Deja la aeronave en un estado coherente con la fase elegida."""
        if f["id"] not in self.FASES_CON_MOTOR:
            return

        m = self.modelo
        m.reiniciar(en_frio=False)
        obj = f.get("obj")

        if f.get("piloto") and obj:
            # Fase de vuelo: se entra ya volando en el punto de la fase
            m.alt_ft = obj.get("alt", 800.0)
            m.ias_kt = obj.get("ias", 74.0)
            m.hdg_deg = obj.get("hdg", 90.0)
            m.en_tierra = m.alt_ft < 5.0
            self.piloto.objetivos(alt=m.alt_ft, ias=m.ias_kt, hdg=m.hdg_deg,
                                  rpm=obj.get("rpm", LIM["rpm_motor_crucero"]))
            self.piloto._i_thr = 0.50
        else:
            # Fase de tierra con motor en marcha
            m.alt_ft = 0.0
            m.ias_kt = 0.0
            m.vs_fpm = 0.0
            m.en_tierra = True
            m.ctl.colectivo = 0.0
            if f["id"] in ("RALENTI",):
                m.n_eng_rpm = LIM["rpm_motor_ralenti"]
                m.n_rot_rpm = 0.0
                m.acoplado = False
                m.ctl.embrague = False
            m.cht_c = LIM["cht_nom"] * 0.6
            m.oil_t_c = 45.0

        self.piloto._i_alt = 0.0
        self.piloto._i_ias = 0.0

    def modo_escenario(self, id_escenario):
        """MODO 2: guion de emergencia, arrancando en crucero estabilizado."""
        esc = ESCENARIOS_POR_ID.get(id_escenario)
        if esc is None:
            return False
        self.modo = MODO_ESCENARIO
        self.escenario = esc
        self.escenario_t = 0.0
        self.escenario_paso = 0
        self.mensajes = []
        self.fallas.limpiar()
        self._preparar_crucero()
        self._msg("MODO 2 - " + esc["nombre"])
        return True

    def modo_falla(self, id_falla):
        """MODO 3: crucero estable + UNA falla concreta a estudiar."""
        d = CATALOGO_POR_ID.get(id_falla)
        if d is None:
            return False
        self.modo = MODO_FALLA
        self.mensajes = []
        self.fallas.limpiar()
        self._preparar_crucero()
        self.fallas.activar(id_falla)
        self._msg("MODO 3 - " + d["nombre"] + " (" + d["sistema"] + ")")
        for s in d.get("sintomas", []):
            self._msg("Síntoma: " + s)
        self._msg("Procedimiento: " + d.get("proc", ""))
        return True

    def detener(self):
        self.modo = MODO_DETENIDO
        self.fallas.limpiar()
        self.modelo.reiniciar(en_frio=True)
        self._msg("Simulación detenida. Tablero a cero.")

    def _preparar_crucero(self):
        """Deja la aeronave volando estable a 1500 ft y 74 kt."""
        self.modelo.reiniciar(en_frio=False)
        self.modelo.alt_ft = 1500.0
        self.modelo.ias_kt = 74.0
        self.modelo.hdg_deg = 90.0
        self.piloto.activo = True
        self.piloto.reacciona_a_fallas = True
        self.piloto.objetivos(alt=1500.0, ias=74.0, hdg=90.0,
                              rpm=LIM["rpm_motor_crucero"])
        # Se precarga el integrador del gobernador en el valor de crucero para
        # que la aeronave arranque estabilizada y no haya un transitorio de
        # 20 segundos antes de que empiece el escenario.
        self.piloto._i_thr = 0.45
        self.piloto._i_alt = 0.0
        self.piloto._i_ias = 0.0
        self.modelo.ctl.luces_tablero = 0.7

    # Acciones manuales desde la página
    def activar_falla(self, id_falla):
        return self.fallas.activar(id_falla)

    def quitar_falla(self, id_falla):
        return self.fallas.desactivar(id_falla)

    def prueba_luces(self, encendido):
        self.mapa.test_luces = bool(encendido)

    def fijar_piloto_reactivo(self, valor):
        """Permite mostrar qué pasa si NADIE reacciona a la falla."""
        self.piloto.reacciona_a_fallas = bool(valor)

    # Lazo principal
    def servicio(self):
        """
        Llamar lo más seguido posible. Ejecuta los pasos de física que
        correspondan al tiempo real transcurrido y refresca salidas.
        Devuelve True si hubo al menos un paso.
        """
        ahora = ticks_ms()
        transcurrido = ticks_diff(ahora, self._t_ultimo)
        self._t_ultimo = ahora
        if transcurrido < 0:
            transcurrido = 0
        # Sin truncar: cada vuelta dura unos 5 ms y a 0,5x int() perdía medio
        # milisegundo por vuelta, así que la cámara lenta iba 10 a 20 % más lenta.
        self._acum_ms += transcurrido * self.velocidad

        paso_ms = int(self.dt * 1000)
        max_pasos = 5                 # tope anti-avalancha
        n = 0
        while self._acum_ms >= paso_ms and n < max_pasos:
            self._acum_ms -= paso_ms
            if not self.pausado:
                self.paso(self.dt)
            n += 1
        if self._acum_ms > paso_ms * max_pasos:
            self._acum_ms = 0         # se descarta el atraso acumulado

        if n == 0:
            return False

        # Salida al hardware
        self._t_salida += n * self.dt
        if self._t_salida >= self.per_salida:
            self._t_salida = 0.0
            self.mapa.escribir()
        return True

    def paso(self, dt):
        """Un paso de simulación de duración fija."""
        self.t_sim += dt

        # 1. Modo -> mandos y fallas
        if self.modo == MODO_NORMAL:
            self._paso_fases(dt)
        elif self.modo == MODO_ESCENARIO:
            self._paso_escenario(dt)

        # 2. Fallas (restablece salud y reaplica lo activo)
        self.fallas.paso(dt)

        # 3. Piloto virtual
        self.piloto.paso(dt)

        # 4. Física
        self.modelo.paso(dt)

        # 5. Física -> bus de señales
        self._publicar_senales()

        # 6. Señales reales -> indicadas (retardos, ruido, fallas de indicación)
        #    La vibración del radial de 9 cilindros escala el ruido de todas
        #    las agujas: con el motor detenido el tablero queda quieto.
        vibracion = limitar(self.modelo.n_eng_rpm / 2200.0, 0.0, 1.2)
        # Los instrumentos eléctricos no se apagan de golpe: siguen a la barra.
        # Con 24 V indican bien, con 18 V -la barra durante el arrastre del
        # arrancador- indican de menos, y por debajo de 12 V ya no indican.
        factor_e = limitar((self.modelo.bus_v - 12.0) /
                           (LIM["bus_min_util"] - 12.0), 0.0, 1.0)
        self.bus.actualizar_indicaciones(dt, factor_e, vibracion)

        # 7. Indicadas -> ángulos de actuador
        self.mapa.actualizar(self.bus, dt)

    # Modo 1: máquina de estados de fases
    def _entrar_fase(self):
        f = PERFIL_NORMAL[self.fase_idx]
        ctl = self.modelo.ctl
        for k in f.get("ctl", {}):
            setattr(ctl, k, f["ctl"][k])
        activo_antes = self.piloto.activo
        self.piloto.activo = bool(f.get("piloto"))
        if self.piloto.activo and not activo_antes:
            # Al tomar el mando, el gobernador arranca desde la posición actual
            # de mariposa. Sin esto habría un salto brusco de RPM al pasar del
            # control manual de la fase al piloto virtual.
            self.piloto._i_thr = self.modelo.ctl.throttle
            self.piloto._i_alt = 0.0
            self.piloto._i_ias = 0.0
        obj = f.get("obj")
        if obj:
            self.piloto.objetivos(alt=obj.get("alt"), ias=obj.get("ias"),
                                  hdg=obj.get("hdg"), rpm=obj.get("rpm"))
        self.fase_t = 0.0
        self._msg("[FASE] " + f["nombre"])

    def _paso_fases(self, dt):
        self.fase_t += dt
        f = PERFIL_NORMAL[self.fase_idx]

        salir = self.fase_t >= f["dur"]
        cond = f.get("hasta")
        if (not salir) and cond:
            var, op, val = cond
            actual = getattr(self.modelo, var, 0.0)
            if op == ">" and actual > val:
                salir = True
            elif op == "<" and actual < val:
                salir = True
            elif op == ">=" and actual >= val:
                salir = True
            elif op == "<=" and actual <= val:
                salir = True

        if salir:
            self.fase_idx += 1
            if self.fase_idx >= len(PERFIL_NORMAL):
                if self.ciclar:
                    self.fase_idx = 0
                    self.modelo.reiniciar(en_frio=True)
                else:
                    self.fase_idx = len(PERFIL_NORMAL) - 1
                    self.modo = MODO_DETENIDO
                    return
            self._entrar_fase()

    # Modo 2: guion de escenario
    def _paso_escenario(self, dt):
        self.escenario_t += dt
        guion = self.escenario["guion"]
        while self.escenario_paso < len(guion):
            t_evt, accion = guion[self.escenario_paso]
            if self.escenario_t < t_evt:
                break
            self.escenario_paso += 1
            self._ejecutar_accion(accion)

    def _ejecutar_accion(self, a):
        if "falla" in a:
            self.fallas.activar(a["falla"])
        if "quitar" in a:
            self.fallas.desactivar(a["quitar"])
        if "amb" in a:
            for k in a["amb"]:
                setattr(self.modelo, k, a["amb"][k])
        if "ctl" in a:
            for k in a["ctl"]:
                setattr(self.modelo.ctl, k, a["ctl"][k])
        if "obj" in a:
            # Un escenario puede mandar al piloto virtual a otra altura o a
            # otra velocidad. Hace falta para las fallas que solo se dan en
            # una fase concreta del vuelo: el engelamiento de carburador, por
            # ejemplo, es un fenómeno de DESCENSO -mariposa cerrada, depresión
            # máxima en el venturi- y montarlo en crucero lo vuelve invisible,
            # porque el gobernador tiene margen de sobra para compensarlo.
            o = a["obj"]
            self.piloto.objetivos(alt=o.get("alt"), ias=o.get("ias"),
                                  hdg=o.get("hdg"), rpm=o.get("rpm"))
        if "piloto" in a:
            self.piloto.reacciona_a_fallas = bool(a["piloto"])
        if "msg" in a:
            self._msg(a["msg"])
        if a.get("fin"):
            self._msg("--- Escenario finalizado ---")
            self.modo = MODO_DETENIDO

    # Física -> bus de señales (incluye la lógica de luces de alerta)
    def _publicar_senales(self):
        m = self.modelo
        p = self.bus.poner

        # Vuelo
        # Lo que muestra el velocímetro no es la velocidad real: es la que
        # deduce el instrumento de la diferencia pitot-estática. Con la toma
        # estática tapada las dos dejan de coincidir.
        p("ias_kt", m.ias_ind_kt)
        # Corrección barométrica: 1 hPa = 27 ft
        alt_ind = m.alt_ft + (m.qnh_hpa - LIM["qnh_hpa"]) * 27.0
        p("alt_ind_ft", alt_ind)
        p("alt_centenas", alt_ind % 1000.0)
        p("vs_ind_fpm", m.vs_fpm)
        # Lo que muestran los instrumentos giroscópicos no es la actitud real:
        # es la actitud filtrada por el régimen del giróscopo. Con el giro
        # cayendo, el horizonte se queda atrás y la brújula giroscópica deriva.
        p("hdg_ind_deg", m.hdg_giro_deg)
        p("pitch_ind_deg", m.pitch_ind_deg)
        p("roll_ind_deg", m.roll_ind_deg)
        p("turn_rate_dps", m.turn_rate_dps)
        p("slip", m.slip)
        p("cdi", m.cdi)

        # Motor y rotor
        p("n_eng_rpm", m.n_eng_rpm)
        p("n_rot_rpm", m.n_rot_rpm)
        p("map_inhg", m.map_inhg)
        p("oil_p_psi", m.oil_p_psi)
        p("oil_t_c", m.oil_t_c)
        p("cht_c", m.cht_c)
        p("cat_c", m.cat_c)
        p("fuel_p_psi", m.fuel_p_psi)

        # Combustible y transmisión
        p("fuel_fwd_l", m.fuel_fwd_l)
        p("fuel_aft_l", m.fuel_aft_l)
        p("xmsn_p_psi", m.xmsn_p_psi)
        p("xmsn_t_c", m.xmsn_t_c)

        # Eléctrico
        p("bus_v", m.bus_v)
        p("amp_a", m.amp_a)

        # Las luces son lógica de aviso con sus umbrales, no física. Y son
        # eléctricas: con la barra por debajo de 20 V se apagan todas, aunque la
        # condición de alarma siga.
        vivo = 1.0 if m.energia_ok else 0.0

        p("lt_fuel_fwd", vivo if m.fuel_fwd_l < LIM["aviso_fuel_l"] else 0.0)
        p("lt_fuel_aft", vivo if m.fuel_aft_l < LIM["aviso_fuel_l"] else 0.0)

        alarma_xmsn = (m.xmsn_p_psi < LIM["xmsn_p_min"] and m.n_rot_rpm > 60.0)
        p("lt_xmsn", vivo if alarma_xmsn else 0.0)

        alarma_gen = (m.ctl.bateria and not m.gen_en_linea)
        p("lt_gen", vivo if alarma_gen else 0.0)

        alarma_rotor = (40.0 < m.n_rot_rpm < LIM["rpm_rotor_min"])
        p("lt_low_rotor", vivo if alarma_rotor else 0.0)

        p("lt_starter", vivo if m.ctl.magnetos != MAG_OFF else 0.0)

    # Telemetría para la página web
    def _msg(self, texto):
        self.mensajes.append({"t": round(self.t_sim, 1), "texto": texto})
        if len(self.mensajes) > 40:
            del self.mensajes[0]

    def estado(self, con_instrumentos=True):
        """Diccionario serializable a JSON con todo lo que necesita la página."""
        m = self.modelo
        d = {
            "t": round(self.t_sim, 1),
            "modo": self.modo,
            "modo_nombre": NOMBRES_MODO.get(self.modo, "?"),
            "pausado": self.pausado,
            "velocidad": self.velocidad,
            "fase": None,
            "fase_texto": None,
            "escenario": None,
            "fallas": self.fallas.lista_activas(),
            "mensajes": self.mensajes[-12:],
            "energia_ok": m.energia_ok,
            "acoplado": m.acoplado,
            "en_tierra": m.en_tierra,
            "motor_vivo": bool(getattr(m, "motor_vivo", False)),
            "hielo_carb": round(m.hielo_carb, 2),
            "mandos": {
                "colectivo": round(m.ctl.colectivo, 3),
                "throttle": round(m.ctl.throttle, 3),
                "calefaccion_carb": round(m.ctl.calefaccion_carb, 2),
                "magnetos": m.ctl.magnetos,
                "generador": m.ctl.generador,
                "bateria": m.ctl.bateria,
                "embrague": m.ctl.embrague,
                "tanque": m.ctl.selector_tanque,
                # La página dibuja las llaves del panel de conmutadores y
                # las mueve con estos campos: muestra qué está haciendo el
                # piloto virtual en cada fase.
                "arrancador": m.ctl.arrancador,
                "bomba": m.ctl.bomba_combustible,
                "luces": round(m.ctl.luces_tablero, 2),
                "mezcla": round(m.ctl.mezcla, 2),
                "gen_en_linea": bool(m.gen_en_linea),
            },
            "stats": self.mapa.estadisticas(),
        }

        if self.modo == MODO_NORMAL:
            f = PERFIL_NORMAL[self.fase_idx]
            d["fase"] = f["nombre"]
            d["fase_texto"] = f["texto"]
            d["fase_id"] = f["id"]
            d["fase_progreso"] = round(min(self.fase_t / f["dur"], 1.0), 2)
        elif self.modo == MODO_ESCENARIO and self.escenario:
            d["escenario"] = self.escenario["nombre"]
            d["escenario_id"] = self.escenario["id"]
            d["fase_texto"] = self.escenario["resumen"]
            d["fase_progreso"] = round(
                min(self.escenario_t / self.escenario["duracion"], 1.0), 2)

        if con_instrumentos:
            inst = {}
            angulos = self.mapa.angulos()
            for it in TABLERO:
                iid = it["id"]
                inst[iid] = {
                    "v": round(self.bus.ver(it["senal"], 0.0), 2),
                    "real": round(self.bus.obtener(it["senal"], 0.0), 2),
                    "ang": angulos.get(iid, 0.0),
                    "anom": self.bus.tiene_anomalia(it["senal"]),
                }
            d["instrumentos"] = inst
        return d

    # Descripción estática (se envía una sola vez a la página)
    def catalogo_estatico(self):
        instrumentos = []
        # El reloj es mecánico: no tiene canal ni actuador, pero ocupa un
        # agujero del tablero y se dibuja.
        for it in list(TABLERO) + list(PANEL_VIRTUAL):
            instrumentos.append({
                "id": it["id"], "n": it["n"], "nombre": it["nombre"],
                "en": it["en"], "unidad": it["unidad"],
                "min": it["escala"][0], "max": it["escala"][1],
                "arcos": it.get("arcos", []),
                "tipo": it["actuador"], "color": it.get("color", ""),
                "canal": it.get("canal"),
                # Datos para el panel visual de cabina
                "desc": it.get("desc", ""),
                "zona": it.get("zona", ""),
                "dial": it.get("dial", ""),
                "pos": it.get("pos"),
                "tam": it.get("tam", 104),
                "leyenda": it.get("leyenda", ""),
                # La tabla de calibración viaja a la página para que dibuje
                # las esferas con la misma no linealidad que el instrumento
                # físico.
                "cal": it.get("cal", []),
                # Cuánto barre la aguja y dónde va el medio de la escala: con
                # esto la página pone la aguja sobre la carátula impresa en el
                # mismo ángulo que la pone el servo (la cuenta, en docs/mecanica.md).
                "barrido": BARRIDO.get(it["id"]),
                "centro": CENTRO_ESCALA.get(it["id"], 90.0),
            })
        fallas = []
        # Ordenadas por sistema, para que la página las agrupe.
        orden_sis = ("MOTOR", "LUBRICACION", "COMBUSTIBLE", "TRANSMISION",
                     "ROTORES", "ELECTRICO", "INSTRUMENTOS")
        catalogo_ordenado = sorted(
            CATALOGO,
            key=lambda f: (orden_sis.index(f["sistema"])
                           if f["sistema"] in orden_sis else 99))
        for f in catalogo_ordenado:
            fallas.append({
                "id": f["id"], "nombre": f["nombre"], "sistema": f["sistema"],
                "sev": f["sev"], "desarrollo": f.get("desarrollo", 0),
                "instr": f.get("instr", []), "sintomas": f.get("sintomas", []),
                "proc": f.get("proc", ""),
            })
        escenarios = []
        for e in ESCENARIOS:
            escenarios.append({
                "id": e["id"], "nombre": e["nombre"], "sistema": e["sistema"],
                "duracion": e["duracion"], "resumen": e["resumen"],
            })
        fases = []
        for f in PERFIL_NORMAL:
            fases.append({"id": f["id"], "nombre": f["nombre"],
                          "dur": f["dur"], "texto": f["texto"]})
        return {"aeronave": AERONAVE, "instrumentos": instrumentos,
                "fallas": fallas, "escenarios": escenarios, "fases": fases,
                "anunciador": ANUNCIADOR,
                # Geometría del tablero: viaja en el catálogo para que la
                # página no repita ningún número. Se edita en h08/config/panel.py.
                "lienzo": PANEL_LIENZO,
                "zonas": PANEL_ZONAS,
                "conmutadores": PANEL_CONMUTADORES,
                "placas": PANEL_PLACAS,
                "actuadores": self.actuadores.descripcion()}
