from __future__ import annotations

import sqlite3

import pytest
from factorias import crear_evento, crear_lote, crear_organizacion

from bingo.persistencia import repo_lote
from bingo.utilidades.errores import ErrorIntegridad


def test_crear_devuelve_modelo_persistido(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    assert lote.id is not None
    assert lote.completado_en is None
    assert lote.generado_en


def test_obtener(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    assert repo_lote.obtener(con, lote.id).prefijo_codigo == lote.prefijo_codigo
    assert repo_lote.obtener(con, 999_999) is None


def test_listar_por_evento(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    crear_lote(con, ev.id, prefijo_codigo="A")
    crear_lote(con, ev.id, prefijo_codigo="B")
    assert len(repo_lote.listar_por_evento(con, ev.id)) == 2


def test_prefijo_repetido_en_el_mismo_evento_rechazado_por_indice(
    con: sqlite3.Connection,
) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    crear_lote(con, ev.id, prefijo_codigo="ABC")
    with pytest.raises(ErrorIntegridad) as excinfo:
        crear_lote(con, ev.id, prefijo_codigo="ABC")
    assert excinfo.value.tipo == "unique"


def test_mismo_prefijo_en_eventos_distintos_permitido(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev_a = crear_evento(con, org.id, nombre="A")
    ev_b = crear_evento(con, org.id, nombre="B")
    crear_lote(con, ev_a.id, prefijo_codigo="ABC")
    crear_lote(con, ev_b.id, prefijo_codigo="ABC")  # no debe lanzar


def test_existe_prefijo(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    crear_lote(con, ev.id, prefijo_codigo="ABC")
    assert repo_lote.existe_prefijo(con, ev.id, "ABC")
    assert not repo_lote.existe_prefijo(con, ev.id, "XYZ")


def test_marcar_completado(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    repo_lote.marcar_completado(con, lote.id)
    assert repo_lote.obtener(con, lote.id).completado_en is not None


def test_listar_huerfanos(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    huerfano = crear_lote(con, ev.id, prefijo_codigo="H")
    completo = crear_lote(con, ev.id, prefijo_codigo="C")
    repo_lote.marcar_completado(con, completo.id)

    huerfanos = repo_lote.listar_huerfanos(con)
    assert [lote.id for lote in huerfanos] == [huerfano.id]


def test_eliminar(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    ev = crear_evento(con, org.id)
    lote = crear_lote(con, ev.id)
    repo_lote.eliminar(con, lote.id)
    assert repo_lote.obtener(con, lote.id) is None
