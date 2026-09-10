"""Puente Qt del motor de sorteo (contrato §6.4; decisión D1, plan de la
fase 5). `servicios/servicio_sorteo.MotorSorteo` es Python puro y no puede
importar PySide6 (`tests/arquitectura/test_arquitectura.py` lo prohíbe).
Este `QObject` lo envuelve con `MotorSorteo.conectar()` y emite exactamente
las señales de la tabla del contrato. Las vistas se suscriben siempre aquí,
nunca al motor directamente — así el motor entero se prueba sin `QApplication`.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, QTimer, Signal

from bingo.servicios import servicio_ganadores
from bingo.servicios.servicio_sorteo import MotorSorteo
from bingo.utilidades.errores import ErrorBingo


class PuenteSorteo(QObject):
    bola_extraida = Signal(object)  # Extraccion
    cartones_a_una_bola = Signal(list)  # list[CartonEnJuego]
    ganadores_detectados = Signal(list)  # list[CartonEnJuego]
    ganador_confirmado = Signal(object)  # Ganador
    ronda_cambiada = Signal(int, str)  # ronda_id, estado nuevo
    fallo = Signal(object)  # ErrorBingo — la vista decide franja o modal
    fallo_log = Signal(str)  # aviso de una sola vez por ronda (enmienda S5-6)

    def __init__(self, motor: MotorSorteo, con: Any, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._motor = motor
        self._con = con
        self._automatico = False
        self._intervalo_ms = 6000

        motor.conectar(
            al_extraer=self.bola_extraida.emit,
            al_detectar_a_una_bola=self.cartones_a_una_bola.emit,
            al_detectar_ganadores=self.ganadores_detectados.emit,
            al_cambiar_ronda=self._al_cambiar_ronda,
            al_fallo_log=self.fallo_log.emit,
        )

        # Hallazgo E-14: de un solo disparo, rearmado al TERMINAR cada
        # extracción — nunca un intervalo fijo que encole disparos mientras
        # la extracción anterior sigue en curso (disco lento). Solo
        # `extraer()` decide si se rearma, nunca el propio timeout.
        self._temporizador_auto = QTimer(self)
        self._temporizador_auto.setSingleShot(True)
        self._temporizador_auto.timeout.connect(self.extraer)

    @property
    def motor(self) -> MotorSorteo:
        return self._motor

    def _al_cambiar_ronda(self, ronda_id: int, estado: str) -> None:
        if estado != "en_curso":
            self._temporizador_auto.stop()
        self.ronda_cambiada.emit(ronda_id, estado)

    # -- modo automático -----------------------------------------------------

    def establecer_modo_automatico(self, activo: bool, intervalo_seg: int | None = None) -> None:
        self._automatico = activo
        if intervalo_seg is not None and intervalo_seg > 0:
            self._intervalo_ms = intervalo_seg * 1000
        if not activo:
            self._temporizador_auto.stop()
        elif self._puede_seguir_extrayendo() and not self._temporizador_auto.isActive():
            self._temporizador_auto.start(self._intervalo_ms)

    @property
    def modo_automatico(self) -> bool:
        return self._automatico

    def _puede_seguir_extrayendo(self) -> bool:
        return self._motor.hay_ronda_en_juego and not (
            self._motor.bombo is not None and self._motor.bombo.agotado
        )

    # -- acciones --------------------------------------------------------------

    def extraer(self) -> None:
        if not self._puede_seguir_extrayendo():
            return
        try:
            self._motor.extraer(self._con)
        except ErrorBingo as error:
            # Un fallo detiene el automático: no se reintenta en bucle
            # delante del público (D2/hallazgo B1: la bola sigue en el
            # bombo, nada se perdió).
            self._automatico = False
            self.fallo.emit(error)
            return
        if self._automatico and self._puede_seguir_extrayendo():
            self._temporizador_auto.start(self._intervalo_ms)

    def confirmar_ganador(self, ganador_id: int, decision: str, nota: str | None = None) -> None:
        try:
            servicio_ganadores.confirmar(self._con, ganador_id, decision, nota)
        except ErrorBingo as error:
            self.fallo.emit(error)
            return
        from bingo.persistencia import repo_ganador

        actualizado = repo_ganador.obtener(self._con, ganador_id)
        if actualizado is not None:
            self.ganador_confirmado.emit(actualizado)
