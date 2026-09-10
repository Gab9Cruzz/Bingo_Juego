"""Máquina de nueve estados de la pantalla de transmisión (decisión DU-3,
plan de la fase 5) — el hallazgo más agudo de la revisión: el motor canta
bingo en el instante de la bola; el humano tarda entre tres y cuarenta
segundos en darse cuenta. Con `sin_reclamo="continuar"` (defecto de D8), si
nadie reclama la ronda sigue extrayendo bolas *después* de haber mostrado
"hay un cartón ganador" — para el espectador eso es incomprensible si el
estado intermedio no se llama lo que es.

Clase Python pura, sin Qt: `ui/transmision/ventana_transmision.py` la
conduce desde las señales de `PuenteSorteo`, pero la máquina en sí se
prueba sin `QApplication`.

| Estado | Disparador |
|---|---|
| `BIENVENIDA` | Antes de iniciar la primera ronda del evento |
| `EN_JUEGO` | `bola_extraida` |
| `A_UNA_BOLA_CRITICA` | `cartones_a_una_bola` con cantidad > 0 |
| `HAY_CARTON_GANADOR` | `ganadores_detectados` — sin la palabra BINGO, sin datos |
| `RECLAMO_VENCIDO` | Cuenta de reclamo agotada, `sin_reclamo="continuar"` |
| `GANADOR_CONFIRMADO` | `ganador_confirmado` — aquí y solo aquí el ¡BINGO! grande |
| `ENTRE_RONDAS` | Ronda cerrada |
| `PAUSA` | Ronda pausada |
| `CIERRE` | Evento finalizado |
"""

from __future__ import annotations

from enum import Enum


class EstadoTransmision(Enum):
    BIENVENIDA = "bienvenida"
    EN_JUEGO = "en_juego"
    A_UNA_BOLA_CRITICA = "a_una_bola_critica"
    HAY_CARTON_GANADOR = "hay_carton_ganador"
    RECLAMO_VENCIDO = "reclamo_vencido"
    GANADOR_CONFIRMADO = "ganador_confirmado"
    ENTRE_RONDAS = "entre_rondas"
    PAUSA = "pausa"
    CIERRE = "cierre"


# Estados en los que una bola nueva o un cambio de "a una bola" no debe
# interrumpir lo que se está mostrando: el hueco de reclamo (y su
# confirmación) manda sobre el juego mientras dure.
_ESTADOS_QUE_NO_SE_INTERRUMPEN_POR_UNA_BOLA = frozenset(
    {EstadoTransmision.HAY_CARTON_GANADOR, EstadoTransmision.GANADOR_CONFIRMADO}
)


class MaquinaEstadoTransmision:
    def __init__(self) -> None:
        self._estado = EstadoTransmision.BIENVENIDA
        self._a_una_bola_activo = False
        self._estado_antes_de_pausa = EstadoTransmision.EN_JUEGO

    @property
    def estado(self) -> EstadoTransmision:
        return self._estado

    def bola_extraida(self) -> None:
        if self._estado in _ESTADOS_QUE_NO_SE_INTERRUMPEN_POR_UNA_BOLA:
            return
        self._a_una_bola_activo = False
        self._estado = EstadoTransmision.EN_JUEGO

    def cartones_a_una_bola(self, cantidad: int) -> None:
        if self._estado in _ESTADOS_QUE_NO_SE_INTERRUMPEN_POR_UNA_BOLA:
            return
        self._a_una_bola_activo = cantidad > 0
        self._estado = (
            EstadoTransmision.A_UNA_BOLA_CRITICA
            if self._a_una_bola_activo
            else EstadoTransmision.EN_JUEGO
        )

    def ganadores_detectados(self) -> None:
        self._estado = EstadoTransmision.HAY_CARTON_GANADOR

    def reclamo_vencido(self) -> None:
        """`sin_reclamo="continuar"` (decisión D8): tarjeta de 4-6 s antes
        de volver al juego — `continuar_tras_reclamo_vencido()` la cierra."""
        if self._estado == EstadoTransmision.HAY_CARTON_GANADOR:
            self._estado = EstadoTransmision.RECLAMO_VENCIDO

    def continuar_tras_reclamo_vencido(self) -> None:
        if self._estado != EstadoTransmision.RECLAMO_VENCIDO:
            return
        self._estado = (
            EstadoTransmision.A_UNA_BOLA_CRITICA
            if self._a_una_bola_activo
            else EstadoTransmision.EN_JUEGO
        )

    def ganador_confirmado(self) -> None:
        self._estado = EstadoTransmision.GANADOR_CONFIRMADO

    def ronda_iniciada(self) -> None:
        self._a_una_bola_activo = False
        self._estado = EstadoTransmision.EN_JUEGO

    def ronda_cerrada(self) -> None:
        self._estado = EstadoTransmision.ENTRE_RONDAS

    def ronda_pausada(self) -> None:
        if self._estado != EstadoTransmision.PAUSA:
            self._estado_antes_de_pausa = self._estado
        self._estado = EstadoTransmision.PAUSA

    def ronda_reanudada(self) -> None:
        if self._estado == EstadoTransmision.PAUSA:
            self._estado = self._estado_antes_de_pausa

    def finalizar_evento(self) -> None:
        self._estado = EstadoTransmision.CIERRE
