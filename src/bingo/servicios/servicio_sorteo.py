"""Motor de sorteo: máquina de estados de una ronda en juego (contrato §5.3,
§5.7). Python puro, sin PySide6 (decisión D1, plan de la fase 5): publica sus
eventos por *callbacks*, mismo convenio que `al_progresar`/`debe_cancelar` de
`ui/tarea.py`. `ui/sorteo/puente_sorteo.py` envuelve un `MotorSorteo` en un
`QObject` que emite las señales de la tabla §6.4; las vistas se suscriben
siempre al puente, nunca a este módulo.

**Dueño del motor (hallazgo S5-3):** la instancia vive en
`ui/espacio_evento.py::EspacioEvento`, no en la vista de la sección Sorteo —
cambiar de sección del riel a mitad de ronda no puede destruir la partida.

**La extracción se persiste en el hilo de la interfaz (decisión D2), no en
un `QThread`.** `extraer()` abre una única `transaccion()` corta; nada de
esta fase corre en un trabajador salvo el respaldo y el reporte de evento
(tareas 4.11/4.12).
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from random import Random

from bingo.config.rutas import dir_logs_evento
from bingo.dominio.bombo import Bombo
from bingo.dominio.carton import carton_desde_orden_canonico, numeros_por_bit
from bingo.dominio.estados import TRANSICIONES_RONDA, puede_transicionar
from bingo.dominio.modelos import Extraccion, Ganador
from bingo.dominio.partida import CartonEnJuego, EstadoPartida, es_ganador
from bingo.persistencia import (
    repo_auditoria,
    repo_carton,
    repo_comprador,
    repo_extraccion,
    repo_ganador,
    repo_patron,
    repo_ronda,
)
from bingo.persistencia.conexion import transaccion
from bingo.utilidades.errores import (
    ErrorNoEncontrado,
    ErrorReanudacion,
    ErrorTransicionInvalida,
    ErrorValidacion,
)
from bingo.utilidades.fechas import ahora_iso
from bingo.utilidades.log_partida import LogPartida

logger = logging.getLogger("bingo.servicios.servicio_sorteo")

CallbackExtraer = Callable[[Extraccion], None]
CallbackAUnaBola = Callable[[list[CartonEnJuego]], None]
CallbackGanadores = Callable[[list[CartonEnJuego]], None]
CallbackConfirmarGanador = Callable[[Ganador], None]
CallbackCambiarRonda = Callable[[int, str], None]
CallbackFalloLog = Callable[[str], None]


@dataclass(slots=True)
class ResultadoReanudacion:
    """`persistidos` incluye anulados y rechazados (hallazgo C2): es
    exactamente lo que el motor necesita en memoria para no volver a
    notificar un ganador que el operador ya descartó. `detectados` es lo que
    la reproducción por bits considera vigente *después* de excluir esos
    mismos anulados/rechazados — es el lado que de verdad se compara contra
    `persistidos` filtrado para decidir `coherente` (decisión D13)."""

    coherente: bool
    detectados: frozenset[int]
    persistidos: frozenset[int]
    detalle: str = ""


def _cargar_cartones_elegibles(con: sqlite3.Connection, evento_id: int) -> list[CartonEnJuego]:
    """Solo `vendido` con comprador vivo (elegibilidad estricta, fase 4,
    decisión UC-1). Se llama tanto al iniciar como al reanudar una ronda —
    idéntica consulta, ninguna razón para dos rutas distintas."""
    vendidos = repo_carton.listar_por_evento(con, evento_id, estado="vendido")
    compradores = repo_comprador.mapa_por_evento(con, evento_id)
    return [
        CartonEnJuego(
            carton_id=carton.id,
            codigo=carton.codigo,
            numeros_por_bit=numeros_por_bit(carton_desde_orden_canonico(carton.numeros)),
        )
        for carton in vendidos
        if carton.id in compradores
    ]


class MotorSorteo:
    """`al_confirmar_ganador` no está entre los parámetros del constructor
    aunque exista en la tabla de señales del §6.4: la confirmación de un
    ganador la ejecuta `servicios/servicio_ganadores.confirmar`, una llamada
    directa de la vista, no un evento que el motor dispare por su cuenta.
    `ui/sorteo/puente_sorteo.py` emite `ganador_confirmado` él mismo después
    de llamar a ese servicio.
    """

    def __init__(
        self,
        *,
        rng: Random,
        al_extraer: CallbackExtraer | None = None,
        al_detectar_a_una_bola: CallbackAUnaBola | None = None,
        al_detectar_ganadores: CallbackGanadores | None = None,
        al_cambiar_ronda: CallbackCambiarRonda | None = None,
        al_fallo_log: CallbackFalloLog | None = None,
    ) -> None:
        self._rng = rng
        self._al_extraer = al_extraer
        self._al_detectar_a_una_bola = al_detectar_a_una_bola
        self._al_detectar_ganadores = al_detectar_ganadores
        self._al_cambiar_ronda = al_cambiar_ronda
        self._al_fallo_log = al_fallo_log

        self._ronda_id: int | None = None
        self._evento_id: int | None = None
        self._mascaras: list[int] = []
        self._bombo: Bombo | None = None
        self._estado_partida: EstadoPartida | None = None
        self._log: LogPartida | None = None
        self._aviso_fallo_log_emitido = False
        # D8: el `extraccion.orden` de la primera bola que produjo ganador.
        # `None` mientras nadie ha ganado todavía.
        self._orden_ganador: int | None = None
        # Hallazgo C2: TODOS los carton_id ya persistidos en `ganador` para
        # esta ronda, anulados y rechazados incluidos.
        self._ya_detectados: set[int] = set()

    def conectar(
        self,
        *,
        al_extraer: CallbackExtraer | None = None,
        al_detectar_a_una_bola: CallbackAUnaBola | None = None,
        al_detectar_ganadores: CallbackGanadores | None = None,
        al_cambiar_ronda: CallbackCambiarRonda | None = None,
        al_fallo_log: CallbackFalloLog | None = None,
    ) -> None:
        """Reemplaza los callbacks después de construir el motor. Existe
        para que `EspacioEvento` (dueño del motor, hallazgo S5-3) pueda
        crearlo antes de que exista `ui/sorteo/puente_sorteo.py`, y el
        puente se conecte después sin construir una segunda instancia."""
        self._al_extraer = al_extraer
        self._al_detectar_a_una_bola = al_detectar_a_una_bola
        self._al_detectar_ganadores = al_detectar_ganadores
        self._al_cambiar_ronda = al_cambiar_ronda
        self._al_fallo_log = al_fallo_log

    # -- consultas ---------------------------------------------------------

    @property
    def ronda_id(self) -> int | None:
        return self._ronda_id

    @property
    def hay_ronda_en_juego(self) -> bool:
        return self._ronda_id is not None

    @property
    def bombo(self) -> Bombo | None:
        return self._bombo

    @property
    def a_una_bola(self) -> list[CartonEnJuego]:
        return self._estado_partida.a_una_bola if self._estado_partida else []

    @property
    def cartones(self) -> list[CartonEnJuego]:
        """Los cartones en juego con su `marcado` actual. Sobre todo para
        pruebas y para el monitor de confianza (DU-8): reconstruir una
        ronda (`reanudar_ronda`) debe dejar cada cartón con el mismo
        `marcado` que tenía antes de morir el proceso."""
        return self._estado_partida.cartones if self._estado_partida else []

    # -- ciclo de vida de la ronda ------------------------------------------

    def iniciar_ronda(self, con: sqlite3.Connection, ronda_id: int) -> None:
        """Solo el primer arranque (`pendiente -> en_curso`): construye un
        `EstadoPartida` en blanco. **No** vale para reabrir una ronda
        `cerrada` que ya tiene extracciones — eso olvidaría en memoria las
        marcas ya hechas y el `Bombo` nuevo podría volver a elegir un
        número que `extraccion` ya tiene (`UNIQUE(ronda_id, numero)`
        saltaría a mitad de un evento en vivo). Reabrir pasa por
        `servicio_rondas.reabrir_ronda` seguido de `reanudar_ronda()`, que sí
        reproduce la historia existente (decisión D13). Por eso este método
        no usa `puede_transicionar` en general: `TRANSICIONES_RONDA` también
        permite `cerrada -> en_curso` (hallazgo V5), pero no por esta vía.
        """
        ronda = repo_ronda.obtener(con, ronda_id)
        if ronda is None:
            raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})
        if ronda.estado != "pendiente":
            raise ErrorTransicionInvalida(
                "error.transicion_invalida",
                parametros={"actual": ronda.estado, "nuevo": "en_curso"},
            )
        patron = repo_patron.obtener(con, ronda.patron_id)
        if patron is None:
            raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda.patron_id})

        cartones_en_juego = _cargar_cartones_elegibles(con, ronda.evento_id)
        if not cartones_en_juego:
            # Hallazgo C4 (tarea 4.23): arrancar un sorteo donde nadie puede
            # ganar no es un caso de uso, a diferencia de "sin vendidos"
            # (aviso no bloqueante de `validar_evento_listo` — se vende en
            # la puerta).
            raise ErrorValidacion("sorteo.error.sin_cartones_elegibles")

        momento = ahora_iso()
        with transaccion(con):
            repo_ronda.actualizar_inicio(con, ronda_id, estado="en_curso", iniciada_en=momento)

        self._ronda_id = ronda_id
        self._evento_id = ronda.evento_id
        self._mascaras = list(patron.mascaras)
        self._bombo = Bombo(self._rng)
        self._estado_partida = EstadoPartida(cartones_en_juego)
        self._orden_ganador = None
        self._ya_detectados = set()
        self._aviso_fallo_log_emitido = False
        self._log = LogPartida(dir_logs_evento(ronda.evento_id) / f"ronda-{ronda_id}.log")
        self._log.abrir()

        if self._al_cambiar_ronda:
            self._al_cambiar_ronda(ronda_id, "en_curso")

    def _exigir_ronda_id(self, ronda_id: int) -> None:
        if self._ronda_id != ronda_id:
            raise ValueError(
                f"La ronda {ronda_id} no es la que este motor tiene en memoria "
                f"({self._ronda_id!r}); no se puede operar sobre ella sin reanudar_ronda()"
            )

    def pausar(self, con: sqlite3.Connection, ronda_id: int) -> None:
        self._exigir_ronda_id(ronda_id)
        ronda = repo_ronda.obtener(con, ronda_id)
        if ronda is None:
            raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})
        if not puede_transicionar(TRANSICIONES_RONDA, ronda.estado, "pausada"):
            raise ErrorTransicionInvalida(
                "error.transicion_invalida",
                parametros={"actual": ronda.estado, "nuevo": "pausada"},
            )
        with transaccion(con):
            repo_ronda.actualizar_estado(con, ronda_id, "pausada")
        if self._al_cambiar_ronda:
            self._al_cambiar_ronda(ronda_id, "pausada")

    def reanudar(self, con: sqlite3.Connection, ronda_id: int) -> None:
        """`pausada -> en_curso` con el motor todavía vivo en memoria (el
        proceso no se reinició). Distinto de `reanudar_ronda()`, que
        reconstruye desde cero tras un reinicio (decisión D13)."""
        self._exigir_ronda_id(ronda_id)
        ronda = repo_ronda.obtener(con, ronda_id)
        if ronda is None:
            raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})
        if not puede_transicionar(TRANSICIONES_RONDA, ronda.estado, "en_curso"):
            raise ErrorTransicionInvalida(
                "error.transicion_invalida",
                parametros={"actual": ronda.estado, "nuevo": "en_curso"},
            )
        with transaccion(con):
            repo_ronda.actualizar_estado(con, ronda_id, "en_curso")
        if self._al_cambiar_ronda:
            self._al_cambiar_ronda(ronda_id, "en_curso")

    def cerrar_ronda(self, con: sqlite3.Connection, ronda_id: int) -> None:
        ronda = repo_ronda.obtener(con, ronda_id)
        if ronda is None:
            raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})
        if not puede_transicionar(TRANSICIONES_RONDA, ronda.estado, "cerrada"):
            raise ErrorTransicionInvalida(
                "error.transicion_invalida",
                parametros={"actual": ronda.estado, "nuevo": "cerrada"},
            )
        momento = ahora_iso()
        with transaccion(con):
            repo_ronda.actualizar_cierre(con, ronda_id, estado="cerrada", cerrada_en=momento)

        if self._ronda_id == ronda_id:
            if self._log is not None:
                self._log.cerrar()
            self._ronda_id = None
            self._evento_id = None
            self._mascaras = []
            self._bombo = None
            self._estado_partida = None
            self._log = None
            self._orden_ganador = None
            self._ya_detectados = set()

        if self._al_cambiar_ronda:
            self._al_cambiar_ronda(ronda_id, "cerrada")

    # -- extracción ----------------------------------------------------------

    def extraer(self, con: sqlite3.Connection) -> Extraccion:
        if self._ronda_id is None or self._bombo is None or self._estado_partida is None:
            raise ValueError("No hay ninguna ronda en juego: llama a iniciar_ronda() primero")

        numero = self._bombo.siguiente()
        orden = len(self._bombo.extraidas) + 1

        ganadores_para_notificar: list[CartonEnJuego] = []
        with transaccion(con):
            extraccion_creada = repo_extraccion.crear(
                con, Extraccion(ronda_id=self._ronda_id, orden=orden, numero=numero)
            )
            tocados = self._estado_partida.aplicar(numero, self._mascaras)

            # D8: solo se registra y notifica la primera bola que produce
            # ganador. Las siguientes pueden seguir marcando cartones que
            # seguirían el patrón (empate por bola posterior, V2), pero esos
            # no cuentan: la ronda sigue jugándose ("continuar") sin volver
            # a disparar el reclamo.
            if self._orden_ganador is None:
                candidatos = [c for c in tocados if es_ganador(c.marcado, self._mascaras)]
                if candidatos:
                    self._orden_ganador = orden
                    for carton in candidatos:
                        repo_ganador.crear(
                            con,
                            Ganador(
                                ronda_id=self._ronda_id,
                                carton_id=carton.carton_id,
                                bola_numero=numero,
                            ),
                        )
                        self._ya_detectados.add(carton.carton_id)
                    ganadores_para_notificar = candidatos

        # Después del commit (hallazgo B1): el bombo solo se confirma una
        # vez que la fila de esta bola es un hecho en la base.
        self._bombo.confirmar(numero)

        # Después del commit también (enmienda S5-6): un fallo de disco al
        # escribir el log no debe poder tumbar la transacción que ya tuvo
        # éxito.
        if self._log is not None:
            try:
                self._log.linea(f"{orden}\t{numero}\t{self._evento_id}")
            except OSError as error:
                logger.warning("No se pudo escribir el log de partida: %s", error)
                if not self._aviso_fallo_log_emitido:
                    self._aviso_fallo_log_emitido = True
                    if self._al_fallo_log:
                        self._al_fallo_log(str(error))

        if self._al_extraer:
            self._al_extraer(extraccion_creada)
        if self._al_detectar_a_una_bola:
            self._al_detectar_a_una_bola(self._estado_partida.a_una_bola)
        if ganadores_para_notificar and self._al_detectar_ganadores:
            self._al_detectar_ganadores(ganadores_para_notificar)

        return extraccion_creada

    # -- reanudación (decisión D13) -----------------------------------------

    def reanudar_ronda(
        self, con: sqlite3.Connection, ronda_id: int, *, forzar: bool = False
    ) -> ResultadoReanudacion:
        """Reproduce la ronda **solo lectura** (nunca escribe `extraccion` ni
        `ganador`) y verifica que lo reproducido coincide con lo persistido.

        Si no coincide, lanza `ErrorReanudacion` (modal terminal, DU-12) —
        salvo que `forzar=True`, en cuyo caso registra
        `sorteo.reanudacion_incoherente` en auditoría con el detalle y
        adopta el estado igual. Vuelve a llamarse con `forzar=True` desde la
        opción "reanudar de todos modos" del modal.
        """
        ronda = repo_ronda.obtener(con, ronda_id)
        if ronda is None:
            raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})
        if ronda.estado not in ("en_curso", "pausada"):
            raise ErrorValidacion(
                "sorteo.error.ronda_no_reanudable", parametros={"estado": ronda.estado}
            )
        patron = repo_patron.obtener(con, ronda.patron_id)
        if patron is None:
            raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda.patron_id})
        mascaras = list(patron.mascaras)

        cartones_en_juego = _cargar_cartones_elegibles(con, ronda.evento_id)
        estado_partida = EstadoPartida(cartones_en_juego)

        numeros = repo_extraccion.numeros_por_ronda(con, ronda_id)
        bombo = Bombo(self._rng, ya_extraidas=numeros)

        filas_ganador = repo_ganador.listar_por_ronda(con, ronda_id)
        ya_conocidos = {g.carton_id for g in filas_ganador}
        persistidos_vigentes = {
            g.carton_id for g in filas_ganador if g.anulado_en is None and g.decision != "rechazado"
        }
        anulados_o_rechazados_conocidos = ya_conocidos - persistidos_vigentes

        orden_ganador: int | None = None
        detectados_crudo: set[int] = set()
        for orden_actual, numero in enumerate(numeros, start=1):
            tocados = estado_partida.aplicar(numero, mascaras)
            if orden_ganador is None:
                candidatos = {c.carton_id for c in tocados if es_ganador(c.marcado, mascaras)}
                if candidatos:
                    orden_ganador = orden_actual
                    detectados_crudo = candidatos

        # Se excluyen del lado "detectado" los que el operador ya anuló o
        # rechazó (hallazgo C2/V1): la reproducción por bits es ciega a esa
        # decisión humana, y sin excluirla aquí un ganador legítimamente
        # anulado se marcaría como incoherencia cada vez que se reanude.
        detectados = detectados_crudo - anulados_o_rechazados_conocidos
        coherente = detectados == persistidos_vigentes

        detalle = (
            f"detectados={sorted(detectados)} persistidos_vigentes={sorted(persistidos_vigentes)}"
        )
        resultado = ResultadoReanudacion(
            coherente=coherente,
            detectados=frozenset(detectados),
            persistidos=frozenset(ya_conocidos),
            detalle=detalle,
        )

        if not coherente:
            if not forzar:
                raise ErrorReanudacion(
                    "sorteo.error.reanudacion_incoherente", detalle=resultado.detalle
                )
            repo_auditoria.registrar(
                con, ronda.evento_id, "sorteo.reanudacion_incoherente", detalle=resultado.detalle
            )

        self._ronda_id = ronda_id
        self._evento_id = ronda.evento_id
        self._mascaras = mascaras
        self._bombo = bombo
        self._estado_partida = estado_partida
        self._orden_ganador = orden_ganador
        self._ya_detectados = ya_conocidos
        self._aviso_fallo_log_emitido = False
        self._log = LogPartida(dir_logs_evento(ronda.evento_id) / f"ronda-{ronda_id}.log")
        self._log.abrir()

        return resultado
