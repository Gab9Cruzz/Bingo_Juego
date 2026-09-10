from __future__ import annotations

import sqlite3
from collections.abc import Sequence

from factorias import crear_carton, crear_comprador, crear_patron, crear_ronda
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from bingo.dominio.patron import mascara
from bingo.servicios.servicio_sorteo import MotorSorteo
from bingo.ui.sorteo.puente_sorteo import PuenteSorteo
from bingo.ui.transmision.estado_transmision import EstadoTransmision
from bingo.ui.transmision.ventana_transmision import VentanaTransmision


class _RngSecuencial:
    def choice(self, secuencia: Sequence[int]) -> int:
        return secuencia[0]


def _preparar(con: sqlite3.Connection, evento_creado, lote_creado):
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)
    motor = MotorSorteo(rng=_RngSecuencial())
    puente = PuenteSorteo(motor, con)
    return motor, puente, ronda


def test_arranca_en_bienvenida(qapp, con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    _motor, puente, _ronda = _preparar(con, evento_creado, lote_creado)
    ventana = VentanaTransmision(con, evento_creado, puente)
    assert ventana.estado == EstadoTransmision.BIENVENIDA


def test_bola_extraida_actualiza_numero_y_estado(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    motor, puente, ronda = _preparar(con, evento_creado, lote_creado)
    ventana = VentanaTransmision(con, evento_creado, puente)

    motor.iniciar_ronda(con, ronda.id)
    puente.extraer()

    assert ventana.estado == EstadoTransmision.EN_JUEGO
    assert ventana._numero_actual == 1  # noqa: SLF001


def test_ronda_pausada_y_reanudada_restaura_el_estado(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    motor, puente, ronda = _preparar(con, evento_creado, lote_creado)
    ventana = VentanaTransmision(con, evento_creado, puente)

    motor.iniciar_ronda(con, ronda.id)
    puente.extraer()
    motor.pausar(con, ronda.id)
    assert ventana.estado == EstadoTransmision.PAUSA

    motor.reanudar(con, ronda.id)
    assert ventana.estado == EstadoTransmision.EN_JUEGO


def test_ronda_cerrada_pasa_a_entre_rondas(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    motor, puente, ronda = _preparar(con, evento_creado, lote_creado)
    ventana = VentanaTransmision(con, evento_creado, puente)

    motor.iniciar_ronda(con, ronda.id)
    motor.cerrar_ronda(con, ronda.id)

    assert ventana.estado == EstadoTransmision.ENTRE_RONDAS


def test_ganador_confirmado_guarda_codigo_y_nombre(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    from factorias import crear_ganador

    _motor, puente, ronda = _preparar(con, evento_creado, lote_creado)
    from bingo.persistencia import repo_carton

    carton = repo_carton.listar_por_evento(con, evento_creado.id, estado="vendido")[0]
    ganador = crear_ganador(con, ronda.id, carton.id, bola_numero=1)

    ventana = VentanaTransmision(con, evento_creado, puente)
    puente.confirmar_ganador(ganador.id, "unico")

    assert ventana.estado == EstadoTransmision.GANADOR_CONFIRMADO
    assert ventana._codigo_ganador == carton.codigo  # noqa: SLF001


def test_escape_cierra_la_ventana(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    _motor, puente, _ronda = _preparar(con, evento_creado, lote_creado)
    ventana = VentanaTransmision(con, evento_creado, puente)
    ventana.show()

    evento_tecla = QKeyEvent(
        QKeyEvent.Type.KeyPress, Qt.Key.Key_Escape, Qt.KeyboardModifier.NoModifier
    )
    ventana.keyPressEvent(evento_tecla)

    assert not ventana.isVisible()


def test_nunca_acepta_foco(qapp, con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    """Decisión DU-5: un Alt+F4 accidental en directo no puede matarla."""
    _motor, puente, _ronda = _preparar(con, evento_creado, lote_creado)
    ventana = VentanaTransmision(con, evento_creado, puente)
    assert ventana.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert bool(ventana.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus)


def test_pintar_no_lanza(qapp, con: sqlite3.Connection, evento_creado, lote_creado) -> None:
    motor, puente, ronda = _preparar(con, evento_creado, lote_creado)
    ventana = VentanaTransmision(con, evento_creado, puente)
    motor.iniciar_ronda(con, ronda.id)
    puente.extraer()
    ventana.resize(400, 225)
    ventana.grab()  # fuerza un paintEvent real sin necesitar .show()


def test_cerrar_no_lanza_tras_desconectar_senales(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    """El cierre de la ventana de transmisión no debe tocar el motor ni
    fallar si se cierra dos veces."""
    _motor, puente, _ronda = _preparar(con, evento_creado, lote_creado)
    ventana = VentanaTransmision(con, evento_creado, puente)
    ventana.close()
    ventana.close()
