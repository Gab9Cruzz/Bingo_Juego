import sqlite3

import pytest

from bingo.dominio.modelos import Organizacion
from bingo.persistencia import repo_evento, repo_organizacion
from bingo.utilidades.errores import ErrorIntegridad


def test_crear_devuelve_modelo_persistido(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="Fundación X"))
    assert org.id is not None
    assert org.creada_en


def test_obtener_existente_y_ausente(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="Fundación X"))
    assert repo_organizacion.obtener(con, org.id) == org
    assert repo_organizacion.obtener(con, 999) is None


def test_listar(con: sqlite3.Connection) -> None:
    repo_organizacion.crear(con, Organizacion(nombre="B"))
    repo_organizacion.crear(con, Organizacion(nombre="A"))
    nombres = [o.nombre for o in repo_organizacion.listar(con)]
    assert nombres == ["A", "B"]


def test_actualizar(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="Original"))
    org.nombre = "Renombrada"
    repo_organizacion.actualizar(con, org)
    assert repo_organizacion.obtener(con, org.id).nombre == "Renombrada"


def test_eliminar_bloqueado_con_eventos(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="Fundación X"))
    from bingo.dominio.modelos import Evento

    repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    with pytest.raises(ErrorIntegridad):
        repo_organizacion.eliminar(con, org.id)


def test_eliminar_bloqueado_con_patrones(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="Fundación X"))
    con.execute(
        "INSERT INTO patron (nombre, mascara, organizacion_id) VALUES ('P', 1, ?)", (org.id,)
    )
    with pytest.raises(ErrorIntegridad):
        repo_organizacion.eliminar(con, org.id)


def test_eliminar_sin_dependencias(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="Vacía"))
    repo_organizacion.eliminar(con, org.id)
    assert repo_organizacion.obtener(con, org.id) is None


def test_existe_nombre(con: sqlite3.Connection) -> None:
    org = repo_organizacion.crear(con, Organizacion(nombre="Fundación X"))
    assert repo_organizacion.existe_nombre(con, "fundación x")
    assert not repo_organizacion.existe_nombre(con, "otra")
    assert not repo_organizacion.existe_nombre(con, "Fundación X", excluir_id=org.id)
