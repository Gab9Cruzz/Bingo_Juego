from __future__ import annotations

import sqlite3

import pytest
from factorias import crear_evento, crear_organizacion

from bingo.persistencia import repo_evento
from bingo.servicios import servicio_eventos
from bingo.utilidades.errores import ErrorNoEncontrado


def _evento(con: sqlite3.Connection):
    org = crear_organizacion(con)
    return crear_evento(con, org.id)


def test_asegurar_clave_evento_genera_una_si_no_existe(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    assert ev.clave_evento is None

    clave = servicio_eventos.asegurar_clave_evento(con, ev.id)
    assert clave
    assert repo_evento.obtener(con, ev.id).clave_evento == clave


def test_asegurar_clave_evento_es_idempotente(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    primera = servicio_eventos.asegurar_clave_evento(con, ev.id)
    segunda = servicio_eventos.asegurar_clave_evento(con, ev.id)
    assert primera == segunda


def test_asegurar_clave_evento_inexistente(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorNoEncontrado):
        servicio_eventos.asegurar_clave_evento(con, 999_999)
