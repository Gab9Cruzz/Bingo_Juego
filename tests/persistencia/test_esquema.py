import sqlite3

import pytest


def test_tablas_del_esquema_existen(con: sqlite3.Connection) -> None:
    tablas = {
        r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }
    esperadas = {
        "organizacion",
        "evento",
        "lote",
        "carton",
        "comprador",
        "patron",
        "ronda",
        "extraccion",
        "ganador",
        "auditoria",
    }
    assert esperadas <= tablas


def test_evento_requiere_organizacion_existente(con: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO evento (organizacion_id, nombre, creado_en) VALUES (999, 'x', 'y')"
        )


def test_evento_estado_invalido_rechazado_por_check(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('Org', 'y')")
    org_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO evento (organizacion_id, nombre, estado, creado_en) "
            "VALUES (?, 'x', 'borado', 'y')",
            (org_id,),
        )


def test_carton_estado_invalido_rechazado_por_check(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('Org', 'y')")
    org_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO evento (organizacion_id, nombre, creado_en) VALUES (?, 'e', 'y')", (org_id,)
    )
    evento_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO lote (evento_id, cantidad, semilla, generado_en) VALUES (?, 1, 's', 'y')",
        (evento_id,),
    )
    lote_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO carton (evento_id, lote_id, codigo, numeros, firma, estado) "
            "VALUES (?, ?, 'C1', '1,2,3', 'f1', 'volando')",
            (evento_id, lote_id),
        )


def test_carton_unique_codigo_y_firma(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('Org', 'y')")
    org_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO evento (organizacion_id, nombre, creado_en) VALUES (?, 'e', 'y')", (org_id,)
    )
    evento_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO lote (evento_id, cantidad, semilla, generado_en) VALUES (?, 1, 's', 'y')",
        (evento_id,),
    )
    lote_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO carton (evento_id, lote_id, codigo, numeros, firma) "
        "VALUES (?, ?, 'C1', '1,2,3', 'f1')",
        (evento_id, lote_id),
    )
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO carton (evento_id, lote_id, codigo, numeros, firma) "
            "VALUES (?, ?, 'C1', '4,5,6', 'f2')",
            (evento_id, lote_id),
        )
    with pytest.raises(sqlite3.IntegrityError):
        con.execute(
            "INSERT INTO carton (evento_id, lote_id, codigo, numeros, firma) "
            "VALUES (?, ?, 'C2', '4,5,6', 'f1')",
            (evento_id, lote_id),
        )
