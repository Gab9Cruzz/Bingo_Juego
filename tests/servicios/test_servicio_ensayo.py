import sqlite3

from bingo.persistencia import (
    repo_carton,
    repo_comprador,
    repo_evento,
    repo_organizacion,
    repo_ronda,
)
from bingo.servicios import servicio_ensayo


def test_ejecutar_crea_organizacion_evento_cartones_y_rondas(con: sqlite3.Connection) -> None:
    evento = servicio_ensayo.ejecutar(con)

    assert evento.nombre == servicio_ensayo.NOMBRE_EVENTO
    organizacion = repo_organizacion.obtener(con, evento.organizacion_id)
    assert organizacion is not None
    assert organizacion.nombre == servicio_ensayo.NOMBRE_ORGANIZACION

    cartones = repo_carton.listar_por_evento(con, evento.id, limite=None)
    assert len(cartones) == servicio_ensayo.CANTIDAD_CARTONES
    assert all(c.estado == "vendido" for c in cartones)
    assert repo_comprador.contar_por_evento(con, evento.id) == servicio_ensayo.CANTIDAD_CARTONES

    rondas = repo_ronda.listar_por_evento(con, evento.id)
    assert len(rondas) == servicio_ensayo.CANTIDAD_RONDAS
    # Tres patrones distintos, no el mismo repetido tres veces.
    assert len({r.patron_id for r in rondas}) == servicio_ensayo.CANTIDAD_RONDAS


def test_ejecutar_dos_veces_deja_exactamente_un_evento(con: sqlite3.Connection) -> None:
    """Criterio de aceptación explícito del plan (tarea 4.17)."""
    primero = servicio_ensayo.ejecutar(con)
    segundo = servicio_ensayo.ejecutar(con)

    assert primero.id == segundo.id
    eventos = repo_evento.listar_por_organizacion(con, primero.organizacion_id)
    coincidencias = [e for e in eventos if e.nombre == servicio_ensayo.NOMBRE_EVENTO]
    assert len(coincidencias) == 1

    organizaciones = [
        o for o in repo_organizacion.listar(con) if o.nombre == servicio_ensayo.NOMBRE_ORGANIZACION
    ]
    assert len(organizaciones) == 1

    cartones = repo_carton.listar_por_evento(con, primero.id, limite=None)
    assert len(cartones) == servicio_ensayo.CANTIDAD_CARTONES  # no se duplicó el lote
