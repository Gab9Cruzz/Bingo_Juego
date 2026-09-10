import sqlite3

import pytest
from factorias import crear_patron

from bingo.dominio.modelos import Organizacion, Patron
from bingo.persistencia import repo_patron
from bingo.utilidades.errores import ErrorIntegridad


def test_crear_y_obtener(con: sqlite3.Connection) -> None:
    creado = crear_patron(con, mascaras=[1, 2, 3])
    obtenido = repo_patron.obtener(con, creado.id)
    assert obtenido is not None
    assert obtenido.mascaras == [1, 2, 3]
    assert obtenido.usa_libre is True
    assert obtenido.es_sistema is False


def test_obtener_por_clave_i18n(con: sqlite3.Connection) -> None:
    crear_patron(con, nombre="Sistema", clave_i18n="patron.sistema.x", es_sistema=True)
    assert repo_patron.obtener_por_clave_i18n(con, "patron.sistema.x") is not None
    assert repo_patron.obtener_por_clave_i18n(con, "no.existe") is None


def test_no_se_puede_crear_sin_mascaras(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorIntegridad):
        repo_patron.crear(con, Patron(nombre="Vacío", mascaras=[]))


def test_desde_fila_lanza_si_mascaras_corrupta(con: sqlite3.Connection) -> None:
    creado = crear_patron(con)
    con.execute("UPDATE patron SET mascaras = '[]' WHERE id = ?", (creado.id,))
    with pytest.raises(ErrorIntegridad):
        repo_patron.obtener(con, creado.id)


def test_listar_incluye_sistema_y_propios_de_la_organizacion(con: sqlite3.Connection) -> None:
    from bingo.persistencia import repo_organizacion

    org = repo_organizacion.crear(con, Organizacion(nombre="Org"))
    crear_patron(con, nombre="Del sistema", es_sistema=True, organizacion_id=None)
    crear_patron(con, nombre="Propio", organizacion_id=org.id)

    visibles = repo_patron.listar(con, organizacion_id=org.id)
    nombres = {p.nombre for p in visibles}
    assert nombres == {"Del sistema", "Propio"}


def test_existe_nombre_distingue_organizacion(con: sqlite3.Connection) -> None:
    from bingo.persistencia import repo_organizacion

    org1 = repo_organizacion.crear(con, Organizacion(nombre="Org1"))
    org2 = repo_organizacion.crear(con, Organizacion(nombre="Org2"))
    crear_patron(con, nombre="Mío", organizacion_id=org1.id)

    assert repo_patron.existe_nombre(con, org1.id, "Mío") is True
    assert repo_patron.existe_nombre(con, org2.id, "Mío") is False


def test_existe_nombre_excluye_id(con: sqlite3.Connection) -> None:
    creado = crear_patron(con, nombre="Único", organizacion_id=None)
    assert repo_patron.existe_nombre(con, None, "Único", excluir_id=creado.id) is False


def test_actualizar(con: sqlite3.Connection) -> None:
    creado = crear_patron(con, mascaras=[1])
    import dataclasses

    repo_patron.actualizar(con, dataclasses.replace(creado, mascaras=[1, 2], nombre="Cambiado"))
    obtenido = repo_patron.obtener(con, creado.id)
    assert obtenido.mascaras == [1, 2]
    assert obtenido.nombre == "Cambiado"


def test_eliminar(con: sqlite3.Connection) -> None:
    creado = crear_patron(con)
    repo_patron.eliminar(con, creado.id)
    assert repo_patron.obtener(con, creado.id) is None


def test_contar_por_es_sistema(con: sqlite3.Connection) -> None:
    assert repo_patron.contar_por_es_sistema(con) == 0
    crear_patron(con, es_sistema=True, clave_i18n="a")
    crear_patron(con, es_sistema=True, clave_i18n="b")
    crear_patron(con, es_sistema=False)
    assert repo_patron.contar_por_es_sistema(con) == 2


def test_clave_i18n_es_unica_entre_sistema(con: sqlite3.Connection) -> None:
    crear_patron(con, clave_i18n="dup", es_sistema=True)
    with pytest.raises(ErrorIntegridad):
        crear_patron(con, clave_i18n="dup", es_sistema=True)


def test_clave_i18n_nula_no_participa_de_la_unicidad(con: sqlite3.Connection) -> None:
    crear_patron(con, clave_i18n=None, organizacion_id=None)
    crear_patron(con, clave_i18n=None, organizacion_id=None)  # no lanza
