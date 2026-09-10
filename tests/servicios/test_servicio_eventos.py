from __future__ import annotations

import sqlite3

import pytest
from factorias import crear_evento, crear_organizacion, crear_patron, crear_ronda

from bingo.persistencia import repo_evento
from bingo.servicios import servicio_eventos
from bingo.utilidades.errores import ErrorNoEncontrado, ErrorTransicionInvalida, ErrorValidacion


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


def test_finalizar_evento_con_todas_las_rondas_cerradas(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    patron = crear_patron(con)
    crear_ronda(con, ev.id, patron.id, orden=1, estado="cerrada")
    servicio_eventos.cambiar_estado(con, ev.id, "preparado")
    servicio_eventos.cambiar_estado(con, ev.id, "en_curso")

    servicio_eventos.finalizar_evento(con, ev.id)

    assert repo_evento.obtener(con, ev.id).estado == "finalizado"


def test_finalizar_evento_con_ronda_sin_cerrar_falla(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    patron = crear_patron(con)
    crear_ronda(con, ev.id, patron.id, orden=1, estado="en_curso")
    servicio_eventos.cambiar_estado(con, ev.id, "preparado")
    servicio_eventos.cambiar_estado(con, ev.id, "en_curso")

    with pytest.raises(ErrorValidacion):
        servicio_eventos.finalizar_evento(con, ev.id)
    assert repo_evento.obtener(con, ev.id).estado == "en_curso"


def test_finalizar_evento_desde_preparado_falla(con: sqlite3.Connection) -> None:
    ev = _evento(con)
    servicio_eventos.cambiar_estado(con, ev.id, "preparado")
    with pytest.raises(ErrorTransicionInvalida):
        servicio_eventos.finalizar_evento(con, ev.id)


def test_finalizar_evento_inexistente(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorNoEncontrado):
        servicio_eventos.finalizar_evento(con, 999_999)
