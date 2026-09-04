import sqlite3
import threading

import pytest

from bingo.persistencia.conexion import abrir_conexion, transaccion
from bingo.utilidades.errores import ErrorPersistencia


def test_pragmas_por_defecto(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert con.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        con.close()


def test_synchronous_full_por_defecto(bingo_home) -> None:
    con = abrir_conexion()
    try:
        # FULL = 2 en SQLite
        assert con.execute("PRAGMA synchronous").fetchone()[0] == 2
    finally:
        con.close()


def test_synchronous_parametro_cambia_valor_efectivo(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        assert con.execute("PRAGMA synchronous").fetchone()[0] == 0
    finally:
        con.close()


def test_synchronous_invalido_rechazado(bingo_home) -> None:
    with pytest.raises(ValueError):
        abrir_conexion(synchronous="RARO")  # type: ignore[arg-type]


def test_busy_timeout_fijado(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        assert con.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    finally:
        con.close()


def test_memoria_se_acepta_y_salta_comprobacion_wal() -> None:
    con = abrir_conexion(":memory:", synchronous="OFF")
    try:
        assert con.execute("PRAGMA foreign_keys").fetchone()[0] == 1
    finally:
        con.close()


def test_transaccion_hace_commit(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        con.execute("CREATE TABLE t (x INTEGER)")
        with transaccion(con):
            con.execute("INSERT INTO t (x) VALUES (1)")
        assert con.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
    finally:
        con.close()


def test_transaccion_hace_rollback_ante_error(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        con.execute("CREATE TABLE t (x INTEGER)")
        with pytest.raises(RuntimeError), transaccion(con):
            con.execute("INSERT INTO t (x) VALUES (1)")
            raise RuntimeError("boom")
        assert con.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 0
    finally:
        con.close()


def test_transaccion_anidada_lanza_error_persistencia(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        with transaccion(con), pytest.raises(ErrorPersistencia), transaccion(con):
            pass
    finally:
        con.close()


def test_llamada_fuera_de_transaccion_hace_autocommit(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    try:
        con.execute("CREATE TABLE t (x INTEGER)")
        con.execute("INSERT INTO t (x) VALUES (1)")
        otra = abrir_conexion(synchronous="OFF")
        try:
            assert otra.execute("SELECT COUNT(*) FROM t").fetchone()[0] == 1
        finally:
            otra.close()
    finally:
        con.close()


def test_conexion_usada_desde_otro_hilo_lanza(bingo_home) -> None:
    con = abrir_conexion(synchronous="OFF")
    errores = []

    def usar():
        try:
            con.execute("SELECT 1")
        except sqlite3.ProgrammingError as error:
            errores.append(error)

    hilo = threading.Thread(target=usar)
    hilo.start()
    hilo.join()
    con.close()
    assert len(errores) == 1
