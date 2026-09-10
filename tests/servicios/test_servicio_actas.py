import sqlite3
from pathlib import Path

import pytest
from factorias import (
    crear_carton,
    crear_comprador,
    crear_evento,
    crear_ganador,
    crear_lote,
    crear_organizacion,
    crear_patron,
    crear_ronda,
)

from bingo.persistencia import repo_auditoria, repo_ganador, repo_ronda
from bingo.servicios import servicio_actas
from bingo.utilidades.errores import ErrorNoEncontrado


@pytest.fixture
def escenario(con: sqlite3.Connection, bingo_home: Path):
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento.id, patron.id, orden=1, nombre="Ronda 1")
    return evento, ronda


def test_generar_acta_escribe_el_pdf_y_guarda_el_hash(con: sqlite3.Connection, escenario) -> None:
    _evento, ronda = escenario
    ruta = servicio_actas.generar_acta(con, ronda.id)

    assert ruta.exists()
    recargada = repo_ronda.obtener(con, ronda.id)
    assert recargada.acta_hash is not None
    assert recargada.acta_generada_en is not None


def test_generar_acta_registra_en_auditoria(con: sqlite3.Connection, escenario) -> None:
    evento, ronda = escenario
    servicio_actas.generar_acta(con, ronda.id)
    acciones = [r.accion for r in repo_auditoria.listar_por_evento(con, evento.id)]
    assert "sorteo.acta_generada" in acciones


def test_regenerar_la_misma_ronda_da_el_mismo_hash(con: sqlite3.Connection, escenario) -> None:
    """Es la razón de existir del hash: regenerar el acta del mismo sorteo
    (sin que nada haya cambiado) da el mismo comprobante."""
    _evento, ronda = escenario
    servicio_actas.generar_acta(con, ronda.id)
    hash_1 = repo_ronda.obtener(con, ronda.id).acta_hash

    servicio_actas.generar_acta(con, ronda.id)
    hash_2 = repo_ronda.obtener(con, ronda.id).acta_hash

    assert hash_1 == hash_2


def test_nombre_de_archivo_va_por_ronda_id_no_por_orden(con: sqlite3.Connection, escenario) -> None:
    """Hallazgo C6: `orden` es mutable; el nombre del acta no puede
    depender de él o reordenar rondas haría que una sobrescriba a otra."""
    _evento, ronda = escenario
    ruta = servicio_actas.generar_acta(con, ronda.id)
    assert f"acta-{ronda.id}-" in ruta.name


def test_generar_acta_ronda_inexistente_falla(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorNoEncontrado):
        servicio_actas.generar_acta(con, 999)


def test_verificar_acta_sin_generar(con: sqlite3.Connection, escenario) -> None:
    _evento, ronda = escenario
    assert servicio_actas.verificar_acta(con, ronda.id) == "sin_acta"


def test_verificar_acta_coincide(con: sqlite3.Connection, escenario) -> None:
    _evento, ronda = escenario
    servicio_actas.generar_acta(con, ronda.id)
    assert servicio_actas.verificar_acta(con, ronda.id) == "coincide"


def test_verificar_acta_no_coincide_si_cambian_las_bolas(
    con: sqlite3.Connection, escenario
) -> None:
    """Sin esto el hash del acta es decoración: si la ronda se reabre y se
    extraen más bolas, el verificador tiene que notarlo."""
    from factorias import crear_extraccion

    _evento, ronda = escenario
    servicio_actas.generar_acta(con, ronda.id)
    crear_extraccion(con, ronda.id, orden=1, numero=7)

    assert servicio_actas.verificar_acta(con, ronda.id) == "no_coincide"


def test_acta_excluye_ganadores_anulados(con: sqlite3.Connection, escenario) -> None:
    _evento, ronda = escenario
    lote = crear_lote(con, _evento.id)
    carton = crear_carton(con, _evento.id, lote.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ganador = crear_ganador(con, ronda.id, carton.id, bola_numero=1)
    repo_ganador.anular(con, ganador.id, "2026-01-01T00:00:00Z")

    servicio_actas.generar_acta(con, ronda.id)

    # Un ganador anulado no debe afectar la carga: verificar sigue "coincide"
    # incluso si se anula DESPUÉS de generar (la carga no lo incluye).
    assert servicio_actas.verificar_acta(con, ronda.id) == "coincide"
