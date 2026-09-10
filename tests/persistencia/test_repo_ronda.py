import dataclasses
import sqlite3

from factorias import crear_patron, crear_ronda

from bingo.persistencia import repo_ronda


def test_crear_asigna_id(con: sqlite3.Connection, evento_creado) -> None:
    patron = crear_patron(con)
    creada = crear_ronda(con, evento_creado.id, patron.id, orden=1)
    assert creada.id is not None


def test_listar_por_evento_ordena_por_orden(con: sqlite3.Connection, evento_creado) -> None:
    patron = crear_patron(con)
    crear_ronda(con, evento_creado.id, patron.id, nombre="B", orden=2)
    crear_ronda(con, evento_creado.id, patron.id, nombre="A", orden=1)
    rondas = repo_ronda.listar_por_evento(con, evento_creado.id)
    assert [r.nombre for r in rondas] == ["A", "B"]


def test_orden_maximo(con: sqlite3.Connection, evento_creado) -> None:
    patron = crear_patron(con)
    assert repo_ronda.orden_maximo(con, evento_creado.id) == 0
    crear_ronda(con, evento_creado.id, patron.id, orden=3)
    assert repo_ronda.orden_maximo(con, evento_creado.id) == 3


def test_actualizar(con: sqlite3.Connection, evento_creado) -> None:
    patron = crear_patron(con)
    creada = crear_ronda(con, evento_creado.id, patron.id, orden=1, nombre="Antes")
    repo_ronda.actualizar(con, dataclasses.replace(creada, nombre="Después"))
    assert repo_ronda.obtener(con, creada.id).nombre == "Después"


def test_eliminar(con: sqlite3.Connection, evento_creado) -> None:
    patron = crear_patron(con)
    creada = crear_ronda(con, evento_creado.id, patron.id, orden=1)
    repo_ronda.eliminar(con, creada.id)
    assert repo_ronda.obtener(con, creada.id) is None


def test_contar_por_patron(con: sqlite3.Connection, evento_creado) -> None:
    patron = crear_patron(con)
    assert repo_ronda.contar_por_patron(con, patron.id) == 0
    crear_ronda(con, evento_creado.id, patron.id, orden=1)
    assert repo_ronda.contar_por_patron(con, patron.id) == 1


def test_desplazar_ordenes_a_negativo_y_reasignar(con: sqlite3.Connection, evento_creado) -> None:
    """El mecanismo de dos pasadas (decisión D5, hallazgo C1): una
    permutación completa (invertir 3 rondas) no debe chocar con
    `UNIQUE(evento_id, orden)`."""
    patron = crear_patron(con)
    r1 = crear_ronda(con, evento_creado.id, patron.id, orden=1, nombre="R1")
    r2 = crear_ronda(con, evento_creado.id, patron.id, orden=2, nombre="R2")
    r3 = crear_ronda(con, evento_creado.id, patron.id, orden=3, nombre="R3")

    repo_ronda.desplazar_ordenes_a_negativo(con, evento_creado.id)
    for ronda_id, orden in ((r3.id, 1), (r2.id, 2), (r1.id, 3)):
        repo_ronda.actualizar_orden(con, ronda_id, orden)

    rondas = repo_ronda.listar_por_evento(con, evento_creado.id)
    assert [r.nombre for r in rondas] == ["R3", "R2", "R1"]


def test_contar_por_patron_en_eventos_no_borrador(con: sqlite3.Connection, evento_creado) -> None:
    from bingo.persistencia import repo_evento

    patron = crear_patron(con)
    crear_ronda(con, evento_creado.id, patron.id, orden=1)
    assert repo_ronda.contar_por_patron_en_eventos_no_borrador(con, patron.id) == 0

    repo_evento.actualizar_estado(con, evento_creado.id, "preparado")
    assert repo_ronda.contar_por_patron_en_eventos_no_borrador(con, patron.id) == 1
