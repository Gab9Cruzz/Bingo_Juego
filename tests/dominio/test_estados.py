import sqlite3

import pytest

from bingo.dominio.estados import TRANSICIONES_EVENTO, puede_transicionar
from bingo.dominio.modelos import Evento, Organizacion
from bingo.persistencia import repo_evento, repo_organizacion
from bingo.servicios import servicio_eventos
from bingo.utilidades.errores import ErrorTransicionInvalida


def test_transicion_valida() -> None:
    assert puede_transicionar(TRANSICIONES_EVENTO, "borrador", "preparado")


def test_transicion_invalida() -> None:
    assert not puede_transicionar(TRANSICIONES_EVENTO, "borrador", "en_curso")


def test_transicion_hacia_atras_rechazada() -> None:
    assert not puede_transicionar(TRANSICIONES_EVENTO, "preparado", "borrador")


def test_estado_terminal_sin_salida() -> None:
    assert TRANSICIONES_EVENTO["finalizado"] == set()


def test_servicio_cambiar_estado_lanza_en_transicion_invalida(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="X"))
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    with pytest.raises(ErrorTransicionInvalida):
        servicio_eventos.cambiar_estado(con, ev.id, "en_curso")


def test_servicio_cambiar_estado_valida_aplica(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="X"))
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    servicio_eventos.cambiar_estado(con, ev.id, "preparado")
    assert repo_evento.obtener(con, ev.id).estado == "preparado"
