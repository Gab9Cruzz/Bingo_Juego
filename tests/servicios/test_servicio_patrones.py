from __future__ import annotations

import sqlite3

import pytest
from factorias import crear_evento, crear_organizacion, crear_ronda

from bingo.dominio.patron import PATRONES_SISTEMA
from bingo.persistencia import repo_patron
from bingo.servicios import servicio_patrones
from bingo.utilidades.errores import ErrorDominio, ErrorValidacion


def test_asegurar_patrones_sistema_crea_todos(con: sqlite3.Connection) -> None:
    creados = servicio_patrones.asegurar_patrones_sistema(con)
    assert creados == len(PATRONES_SISTEMA)
    assert repo_patron.contar_por_es_sistema(con) == len(PATRONES_SISTEMA)


def test_asegurar_patrones_sistema_es_idempotente(con: sqlite3.Connection) -> None:
    servicio_patrones.asegurar_patrones_sistema(con)
    afectados = servicio_patrones.asegurar_patrones_sistema(con)
    assert afectados == 0
    assert repo_patron.contar_por_es_sistema(con) == len(PATRONES_SISTEMA)


def test_crear_patron_propio(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    from bingo.dominio.modelos import Patron

    creado = servicio_patrones.crear_patron(
        con, Patron(nombre="Mi patrón", mascaras=[1], organizacion_id=org.id)
    )
    assert creado.id is not None
    assert creado.es_sistema is False


def test_crear_patron_rechaza_nombre_repetido(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    from bingo.dominio.modelos import Patron

    servicio_patrones.crear_patron(con, Patron(nombre="X", mascaras=[1], organizacion_id=org.id))
    with pytest.raises(ErrorValidacion):
        servicio_patrones.crear_patron(
            con, Patron(nombre="X", mascaras=[2], organizacion_id=org.id)
        )


def test_crear_patron_rechaza_libre_incoherente(con: sqlite3.Connection) -> None:
    from bingo.dominio.carton import BIT_LIBRE
    from bingo.dominio.modelos import Patron

    org = crear_organizacion(con)
    with pytest.raises(ErrorValidacion):
        servicio_patrones.crear_patron(
            con,
            Patron(
                nombre="Malo",
                mascaras=[1 << BIT_LIBRE],
                usa_libre=False,
                organizacion_id=org.id,
            ),
        )


def test_duplicar_patron_del_sistema(con: sqlite3.Connection) -> None:
    servicio_patrones.asegurar_patrones_sistema(con)
    org = crear_organizacion(con)
    original = repo_patron.listar(con, organizacion_id=org.id)[0]
    copia = servicio_patrones.duplicar_patron(con, original.id, "Mi copia", org.id)
    assert copia.es_sistema is False
    assert copia.clave_i18n is None
    assert copia.mascaras == original.mascaras


def test_eliminar_patron_del_sistema_falla(con: sqlite3.Connection) -> None:
    servicio_patrones.asegurar_patrones_sistema(con)
    sistema = repo_patron.listar(con)[0]
    with pytest.raises(ErrorDominio):
        servicio_patrones.eliminar_patron(con, sistema.id)


def test_eliminar_patron_en_uso_falla(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    from bingo.dominio.modelos import Patron

    patron = servicio_patrones.crear_patron(
        con, Patron(nombre="Usado", mascaras=[1], organizacion_id=org.id)
    )
    crear_ronda(con, evento.id, patron.id, orden=1)
    with pytest.raises(ErrorDominio):
        servicio_patrones.eliminar_patron(con, patron.id)


def test_eliminar_patron_propio_sin_uso(con: sqlite3.Connection) -> None:
    org = crear_organizacion(con)
    from bingo.dominio.modelos import Patron

    patron = servicio_patrones.crear_patron(
        con, Patron(nombre="Libre", mascaras=[1], organizacion_id=org.id)
    )
    servicio_patrones.eliminar_patron(con, patron.id)
    assert repo_patron.obtener(con, patron.id) is None


def test_asegurar_no_actualiza_patron_en_uso_por_evento_activo(con: sqlite3.Connection) -> None:
    """Decisión DS16 del plan de la fase 4."""
    servicio_patrones.asegurar_patrones_sistema(con)
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    sistema = repo_patron.listar(con)[0]
    crear_ronda(con, evento.id, sistema.id, orden=1)

    from bingo.persistencia import repo_evento

    repo_evento.actualizar_estado(con, evento.id, "preparado")

    # forzar una versión_semilla vieja para que el servicio intente actualizar
    import dataclasses

    repo_patron.actualizar(con, dataclasses.replace(sistema, version_semilla=0))
    afectados = servicio_patrones.asegurar_patrones_sistema(con)
    assert afectados == 0
    assert repo_patron.obtener(con, sistema.id).version_semilla == 0
