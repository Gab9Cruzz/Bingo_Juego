"""G16: la propiedad de WAL de la que depende §1.8.1 — un escritor y N lectores
conviven — verificada de verdad, no solo asumida."""

import sqlite3

import pytest

from bingo.persistencia.conexion import abrir_conexion
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.persistencia.migraciones import aplicar_migraciones
from bingo.utilidades.errores import ErrorBaseBloqueada


def test_lector_no_bloqueado_durante_escritura(bingo_home) -> None:
    escritor = abrir_conexion(synchronous="OFF")
    aplicar_migraciones(escritor)
    escritor.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('X', 'y')")

    lector = abrir_conexion(synchronous="OFF")
    try:
        escritor.execute("BEGIN IMMEDIATE")
        escritor.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('Y', 'y')")
        # Bajo WAL, un lector sigue leyendo la última versión confirmada sin bloquearse.
        filas = lector.execute("SELECT COUNT(*) FROM organizacion").fetchone()[0]
        assert filas == 1  # todavía no ve la fila sin confirmar
        escritor.commit()
    finally:
        lector.close()
        escritor.close()


def test_segundo_escritor_agota_busy_timeout(bingo_home) -> None:
    con1 = abrir_conexion(synchronous="OFF")
    aplicar_migraciones(con1)
    con1.execute("PRAGMA busy_timeout = 100")

    con2 = abrir_conexion(synchronous="OFF")
    con2.execute("PRAGMA busy_timeout = 100")

    try:
        con1.execute("BEGIN IMMEDIATE")
        con1.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('X', 'y')")

        with pytest.raises(ErrorBaseBloqueada), traducir_errores_sqlite():
            con2.execute("BEGIN IMMEDIATE")
            con2.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('Y', 'y')")

        con1.commit()
    finally:
        import contextlib

        with contextlib.suppress(sqlite3.Error):
            con2.rollback()
        con1.close()
        con2.close()
