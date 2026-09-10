from __future__ import annotations

import sqlite3
from random import Random

from factorias import crear_carton, crear_comprador, crear_patron, crear_ronda

from bingo.dominio.patron import mascara
from bingo.servicios.servicio_sorteo import MotorSorteo
from bingo.ui.sorteo.puente_sorteo import PuenteSorteo


def _preparar_ronda(con: sqlite3.Connection, evento_creado, lote_creado):
    patron = crear_patron(con, mascaras=[mascara([(0, 0)])])
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, c1.id)
    return crear_ronda(con, evento_creado.id, patron.id)


def test_extraer_emite_bola_extraida(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    ronda = _preparar_ronda(con, evento_creado, lote_creado)
    motor = MotorSorteo(rng=Random(1))
    motor.iniciar_ronda(con, ronda.id)
    puente = PuenteSorteo(motor, con)

    recibidas = []
    puente.bola_extraida.connect(recibidas.append)

    puente.extraer()

    assert len(recibidas) == 1
    assert recibidas[0].ronda_id == ronda.id


def test_ronda_cambiada_se_emite_al_pausar(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    ronda = _preparar_ronda(con, evento_creado, lote_creado)
    motor = MotorSorteo(rng=Random(1))
    motor.iniciar_ronda(con, ronda.id)
    puente = PuenteSorteo(motor, con)

    cambios = []
    puente.ronda_cambiada.connect(lambda rid, estado: cambios.append((rid, estado)))

    motor.pausar(con, ronda.id)

    assert cambios == [(ronda.id, "pausada")]


def test_modo_automatico_arma_el_temporizador(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    ronda = _preparar_ronda(con, evento_creado, lote_creado)
    motor = MotorSorteo(rng=Random(1))
    motor.iniciar_ronda(con, ronda.id)
    puente = PuenteSorteo(motor, con)

    puente.establecer_modo_automatico(True, intervalo_seg=6)
    assert puente.modo_automatico is True
    assert puente._temporizador_auto.isActive()  # noqa: SLF001 - prueba de caja blanca deliberada


def test_modo_automatico_no_se_arma_si_el_bombo_esta_agotado(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    ronda = _preparar_ronda(con, evento_creado, lote_creado)
    motor = MotorSorteo(rng=Random(1))
    motor.iniciar_ronda(con, ronda.id)
    for _ in range(75):
        motor.extraer(con)
    puente = PuenteSorteo(motor, con)

    puente.establecer_modo_automatico(True, intervalo_seg=6)
    assert not puente._temporizador_auto.isActive()  # noqa: SLF001


def test_extraer_con_ronda_agotada_no_hace_nada(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    ronda = _preparar_ronda(con, evento_creado, lote_creado)
    motor = MotorSorteo(rng=Random(1))
    motor.iniciar_ronda(con, ronda.id)
    for _ in range(75):
        motor.extraer(con)
    puente = PuenteSorteo(motor, con)

    recibidas = []
    puente.bola_extraida.connect(recibidas.append)
    puente.extraer()

    assert recibidas == []


def test_confirmar_ganador_emite_senal(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    from factorias import crear_ganador

    ronda = _preparar_ronda(con, evento_creado, lote_creado)
    from bingo.persistencia import repo_carton

    carton = repo_carton.listar_por_evento(con, evento_creado.id, estado="vendido")[0]
    ganador = crear_ganador(con, ronda.id, carton.id, bola_numero=1)

    motor = MotorSorteo(rng=Random(1))
    motor.iniciar_ronda(con, ronda.id)
    puente = PuenteSorteo(motor, con)

    confirmados = []
    puente.ganador_confirmado.connect(confirmados.append)
    puente.confirmar_ganador(ganador.id, "unico")

    assert len(confirmados) == 1
    assert confirmados[0].decision == "unico"
