import contextlib
import sqlite3

import pytest

from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.utilidades.errores import ErrorBaseBloqueada, ErrorBaseCorrupta, ErrorIntegridad


def test_unique(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('X', 'y')")
    org_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO evento (organizacion_id, nombre, creado_en) VALUES (?, 'E', 'y')", (org_id,)
    )
    evento_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO lote (evento_id, cantidad, semilla, generado_en) VALUES (?, 1, 's', 'y')",
        (evento_id,),
    )
    lote_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO carton (evento_id, lote_id, codigo, numeros, firma) "
        "VALUES (?, ?, 'C1', '1', 'f1')",
        (evento_id, lote_id),
    )
    with pytest.raises(ErrorIntegridad) as exc_info, traducir_errores_sqlite():
        con.execute(
            "INSERT INTO carton (evento_id, lote_id, codigo, numeros, firma) "
            "VALUES (?, ?, 'C1', '2', 'f2')",
            (evento_id, lote_id),
        )
    assert exc_info.value.tipo == "unique"
    assert exc_info.value.restriccion is not None
    assert isinstance(exc_info.value.__cause__, sqlite3.IntegrityError)


def test_foreign_key(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorIntegridad) as exc_info, traducir_errores_sqlite():
        con.execute(
            "INSERT INTO evento (organizacion_id, nombre, creado_en) VALUES (999, 'x', 'y')"
        )
    assert exc_info.value.tipo == "foreign_key"


def test_check(con: sqlite3.Connection) -> None:
    con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('X', 'y')")
    org_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    with pytest.raises(ErrorIntegridad) as exc_info, traducir_errores_sqlite():
        con.execute(
            "INSERT INTO evento (organizacion_id, nombre, estado, creado_en) "
            "VALUES (?, 'x', 'invalido', 'y')",
            (org_id,),
        )
    assert exc_info.value.tipo == "check"


def test_not_null(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorIntegridad) as exc_info, traducir_errores_sqlite():
        con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES (NULL, 'y')")
    assert exc_info.value.tipo == "not_null"


def test_base_bloqueada(bingo_home) -> None:
    from bingo.persistencia.conexion import abrir_conexion
    from bingo.persistencia.migraciones import aplicar_migraciones

    con1 = abrir_conexion(synchronous="OFF")
    aplicar_migraciones(con1)
    con1.execute("PRAGMA busy_timeout = 50")
    con2 = abrir_conexion(synchronous="OFF")
    con2.execute("PRAGMA busy_timeout = 50")
    try:
        con1.execute("BEGIN IMMEDIATE")
        con1.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('X', 'y')")
        with pytest.raises(ErrorBaseBloqueada), traducir_errores_sqlite():
            con2.execute("BEGIN IMMEDIATE")
            con2.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('Y', 'y')")
    finally:
        with contextlib.suppress(sqlite3.Error):
            con1.rollback()
        with contextlib.suppress(sqlite3.Error):
            con2.rollback()
        con1.close()
        con2.close()


def test_base_corrupta(tmp_path) -> None:
    ruta = tmp_path / "no_es_una_base.db"
    ruta.write_bytes(b"esto no es un archivo sqlite valido, tiene bytes de sobra")
    con = sqlite3.connect(ruta)
    with pytest.raises(ErrorBaseCorrupta), traducir_errores_sqlite():
        con.execute("SELECT * FROM sqlite_master").fetchall()
        con.execute("CREATE TABLE x (y INTEGER)")
    con.close()
