import sqlite3

import pytest

from bingo.dominio.modelos import Evento, Organizacion
from bingo.persistencia import repo_evento, repo_organizacion
from bingo.utilidades.errores import ErrorValidacion


def _crear_org(con: sqlite3.Connection) -> Organizacion:
    return repo_organizacion.crear(con, Organizacion(nombre="Fundación X"))


def test_crear_devuelve_modelo_persistido(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo 2026"))
    assert ev.id is not None
    assert ev.estado == "borrador"


def test_precio_en_centavos_sin_perdida(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(
        con, Evento(organizacion_id=org.id, nombre="Bingo", precio_tabla_centavos=1999)
    )
    recuperado = repo_evento.obtener(con, ev.id)
    assert recuperado.precio_tabla_centavos == 1999


def test_listar_por_organizacion(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    otra_org = repo_organizacion.crear(con, Organizacion(nombre="Otra"))
    repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="A"))
    repo_evento.crear(con, Evento(organizacion_id=otra_org.id, nombre="B"))
    resultado = repo_evento.listar_por_organizacion(con, org.id)
    assert len(resultado) == 1
    assert resultado[0].nombre == "A"


def test_listar_todos(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="A"))
    repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="B"))
    assert len(repo_evento.listar_todos(con)) == 2


def test_actualizar_estado_solo_escribe(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    repo_evento.actualizar_estado(con, ev.id, "preparado")
    assert repo_evento.obtener(con, ev.id).estado == "preparado"


def test_actualizar_plantilla_json_invalido_rechazado(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    with pytest.raises(ErrorValidacion):
        repo_evento.actualizar_plantilla(con, ev.id, "{no es json}")


def test_actualizar_plantilla_json_valido(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    ev = repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo"))
    repo_evento.actualizar_plantilla(con, ev.id, '{"color": "#fff"}')
    assert repo_evento.obtener(con, ev.id).plantilla_json == '{"color": "#fff"}'


def test_existe_nombre_por_organizacion(con: sqlite3.Connection) -> None:
    org = _crear_org(con)
    repo_evento.crear(con, Evento(organizacion_id=org.id, nombre="Bingo Anual"))
    assert repo_evento.existe_nombre(con, org.id, "bingo anual")
    assert not repo_evento.existe_nombre(con, org.id, "otro")
