import sqlite3

import pytest

from bingo.dominio.estados import (
    TRANSICIONES_CARTON,
    TRANSICIONES_EVENTO,
    TRANSICIONES_RONDA,
    puede_transicionar,
)
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


@pytest.mark.parametrize(
    ("actual", "nuevo"),
    [
        ("generado", "impreso"),
        ("generado", "anulado"),
        ("impreso", "entregado"),
        ("impreso", "anulado"),
        ("entregado", "vendido"),
        ("entregado", "anulado"),
        ("vendido", "anulado"),
    ],
)
def test_transiciones_carton_validas(actual: str, nuevo: str) -> None:
    assert puede_transicionar(TRANSICIONES_CARTON, actual, nuevo)


@pytest.mark.parametrize(
    ("actual", "nuevo"),
    [
        ("generado", "vendido"),  # salta pasos
        ("impreso", "generado"),  # hacia atrás
        ("vendido", "generado"),
        ("anulado", "generado"),
    ],
)
def test_transiciones_carton_invalidas(actual: str, nuevo: str) -> None:
    assert not puede_transicionar(TRANSICIONES_CARTON, actual, nuevo)


def test_carton_anulado_es_terminal() -> None:
    assert TRANSICIONES_CARTON["anulado"] == set()


@pytest.mark.parametrize(
    ("actual", "nuevo"),
    [
        ("pendiente", "en_curso"),
        ("en_curso", "pausada"),
        ("en_curso", "cerrada"),
        ("pausada", "en_curso"),
        ("pausada", "cerrada"),
        # cerrada -> en_curso: la reapertura (hallazgo V5, fase 5). Un bingo
        # se retoma otro día desde una ronda que se cerró por error.
        ("cerrada", "en_curso"),
    ],
)
def test_transiciones_ronda_validas(actual: str, nuevo: str) -> None:
    assert puede_transicionar(TRANSICIONES_RONDA, actual, nuevo)


@pytest.mark.parametrize(
    ("actual", "nuevo"),
    [
        ("pendiente", "pausada"),  # salta pasos: no se pausa sin haber iniciado
        ("pendiente", "cerrada"),
        ("cerrada", "pendiente"),  # hacia atrás más allá de lo permitido
        ("cerrada", "pausada"),
    ],
)
def test_transiciones_ronda_invalidas(actual: str, nuevo: str) -> None:
    assert not puede_transicionar(TRANSICIONES_RONDA, actual, nuevo)
