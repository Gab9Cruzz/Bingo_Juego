import sqlite3

import pytest
from factorias import crear_carton, crear_ganador, crear_patron, crear_ronda

from bingo.dominio.modelos import Ganador
from bingo.persistencia import repo_ganador
from bingo.utilidades.errores import ErrorIntegridad


@pytest.fixture
def ronda_y_cartones(con: sqlite3.Connection, evento_creado, lote_creado):
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento_creado.id, patron.id)
    c1 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1)
    c2 = crear_carton(con, evento_creado.id, lote_creado.id, semilla=2)
    return ronda, c1, c2


def test_crear_asigna_id(con: sqlite3.Connection, ronda_y_cartones) -> None:
    ronda, c1, _ = ronda_y_cartones
    creado = crear_ganador(con, ronda.id, c1.id, bola_numero=42)
    assert creado.id is not None
    assert creado.confirmado is False
    assert creado.decision is None
    assert creado.registrado_en != ""


def test_indice_unico_total_rechaza_mismo_carton_dos_veces(
    con: sqlite3.Connection, ronda_y_cartones
) -> None:
    """Hallazgo V1, crítico: el índice `(ronda_id, carton_id)` es total, no
    parcial — ni siquiera un ganador ya anulado libera el hueco."""
    ronda, c1, _ = ronda_y_cartones
    creado = crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    repo_ganador.anular(con, creado.id, "2026-01-01T00:00:00Z")

    with pytest.raises(ErrorIntegridad):
        repo_ganador.crear(con, Ganador(ronda_id=ronda.id, carton_id=c1.id, bola_numero=20))


def test_listar_por_ronda_ordena_por_bola(con: sqlite3.Connection, ronda_y_cartones) -> None:
    ronda, c1, c2 = ronda_y_cartones
    crear_ganador(con, ronda.id, c2.id, bola_numero=30)
    crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    ganadores = repo_ganador.listar_por_ronda(con, ronda.id)
    assert [g.bola_numero for g in ganadores] == [10, 30]


def test_listar_por_evento_une_con_ronda(
    con: sqlite3.Connection, ronda_y_cartones, evento_creado
) -> None:
    ronda, c1, _ = ronda_y_cartones
    crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    ganadores = repo_ganador.listar_por_evento(con, evento_creado.id)
    assert len(ganadores) == 1
    assert ganadores[0].carton_id == c1.id


def test_actualizar_decision(con: sqlite3.Connection, ronda_y_cartones) -> None:
    ronda, c1, _ = ronda_y_cartones
    creado = crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    repo_ganador.actualizar_decision(
        con,
        creado.id,
        confirmado=True,
        confirmado_en="2026-01-01T00:00:00Z",
        decision="unico",
        reparte_premio=True,
        nota="sin novedad",
    )
    recargado = repo_ganador.obtener(con, creado.id)
    assert recargado.confirmado is True
    assert recargado.decision == "unico"
    assert recargado.reparte_premio is True
    assert recargado.confirmado_en == "2026-01-01T00:00:00Z"
    assert recargado.nota == "sin novedad"


def test_anular_no_borra_la_fila(con: sqlite3.Connection, ronda_y_cartones) -> None:
    ronda, c1, _ = ronda_y_cartones
    creado = crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    repo_ganador.anular(con, creado.id, "2026-01-01T00:00:00Z")
    recargado = repo_ganador.obtener(con, creado.id)
    assert recargado is not None
    assert recargado.anulado_en == "2026-01-01T00:00:00Z"


def test_contar_confirmados_por_ronda(con: sqlite3.Connection, ronda_y_cartones) -> None:
    ronda, c1, c2 = ronda_y_cartones
    g1 = crear_ganador(con, ronda.id, c1.id, bola_numero=10)
    crear_ganador(con, ronda.id, c2.id, bola_numero=10)
    assert repo_ganador.contar_confirmados_por_ronda(con, ronda.id) == 0

    repo_ganador.actualizar_decision(
        con,
        g1.id,
        confirmado=True,
        confirmado_en="2026-01-01T00:00:00Z",
        decision="unico",
        reparte_premio=True,
    )
    assert repo_ganador.contar_confirmados_por_ronda(con, ronda.id) == 1
