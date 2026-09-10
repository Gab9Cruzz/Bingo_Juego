import sqlite3

import pytest
from factorias import crear_extraccion, crear_patron, crear_ronda

from bingo.dominio.modelos import Extraccion
from bingo.persistencia import repo_extraccion
from bingo.utilidades.errores import ErrorIntegridad


@pytest.fixture
def ronda_creada(con: sqlite3.Connection, evento_creado):
    patron = crear_patron(con)
    return crear_ronda(con, evento_creado.id, patron.id)


def test_crear_asigna_id(con: sqlite3.Connection, ronda_creada) -> None:
    creada = crear_extraccion(con, ronda_creada.id, orden=1, numero=7)
    assert creada.id is not None
    assert creada.extraida_en != ""


def test_listar_por_ronda_ordena_por_orden(con: sqlite3.Connection, ronda_creada) -> None:
    crear_extraccion(con, ronda_creada.id, orden=2, numero=20)
    crear_extraccion(con, ronda_creada.id, orden=1, numero=10)
    extracciones = repo_extraccion.listar_por_ronda(con, ronda_creada.id)
    assert [e.numero for e in extracciones] == [10, 20]


def test_contar_por_ronda(con: sqlite3.Connection, ronda_creada) -> None:
    assert repo_extraccion.contar_por_ronda(con, ronda_creada.id) == 0
    crear_extraccion(con, ronda_creada.id, orden=1, numero=1)
    assert repo_extraccion.contar_por_ronda(con, ronda_creada.id) == 1


def test_numeros_por_ronda(con: sqlite3.Connection, ronda_creada) -> None:
    crear_extraccion(con, ronda_creada.id, orden=1, numero=5)
    crear_extraccion(con, ronda_creada.id, orden=2, numero=42)
    assert repo_extraccion.numeros_por_ronda(con, ronda_creada.id) == [5, 42]


def test_eliminar_por_ronda(con: sqlite3.Connection, ronda_creada) -> None:
    crear_extraccion(con, ronda_creada.id, orden=1, numero=1)
    repo_extraccion.eliminar_por_ronda(con, ronda_creada.id)
    assert repo_extraccion.listar_por_ronda(con, ronda_creada.id) == []


def test_no_permite_repetir_orden_dentro_de_la_ronda(con: sqlite3.Connection, ronda_creada) -> None:
    crear_extraccion(con, ronda_creada.id, orden=1, numero=1)
    with pytest.raises(ErrorIntegridad):
        repo_extraccion.crear(con, Extraccion(ronda_id=ronda_creada.id, orden=1, numero=2))


def test_no_permite_repetir_numero_dentro_de_la_ronda(
    con: sqlite3.Connection, ronda_creada
) -> None:
    crear_extraccion(con, ronda_creada.id, orden=1, numero=1)
    with pytest.raises(ErrorIntegridad):
        repo_extraccion.crear(con, Extraccion(ronda_id=ronda_creada.id, orden=2, numero=1))
