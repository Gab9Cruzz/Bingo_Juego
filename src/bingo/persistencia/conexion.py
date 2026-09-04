"""Apertura de conexiones SQLite, PRAGMAs y transacciones explícitas.

Reglas (ver `docs/convenciones-codigo.md`):

- **Una conexión por hilo, nunca compartida.** `check_same_thread=True` se
  mantiene siempre; cada hilo trabajador abre la suya y la cierra en un
  `finally`.
- `isolation_level=None` (autocommit) más `transaccion()` explícita con
  `BEGIN IMMEDIATE`: evita el manejo implícito de transacciones de `sqlite3`,
  fuente clásica de confusión sobre cuándo hay commit. Una llamada a
  repositorio fuera de `transaccion()` hace autocommit; dentro, participa.
- **Los repositorios nunca abren transacciones ni hacen commit.** Solo los
  servicios y `__main__` abren `transaccion()`.
- Los PRAGMA se aplican fuera de cualquier transacción, en este orden exacto:
  `busy_timeout` -> `journal_mode=WAL` -> `foreign_keys=ON` -> `synchronous`.
  Entre los tres últimos el orden es cosmético; lo que no lo es: `busy_timeout`
  debe fijarse **antes** que `journal_mode=WAL`, porque pasar a WAL toma un
  bloqueo exclusivo y devuelve `SQLITE_BUSY` si otra conexión tiene la base
  abierta — sin `busy_timeout` ya en vigor, el cambio falla en el acto.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Literal

from bingo.config.ajustes import BUSY_TIMEOUT_MS
from bingo.config.rutas import asegurar_estructura, ruta_bd
from bingo.utilidades.errores import ErrorBaseCorrupta, ErrorPersistencia

Sincronizacion = Literal["FULL", "NORMAL", "OFF"]
_VALORES_SYNCHRONOUS: frozenset[str] = frozenset({"FULL", "NORMAL", "OFF"})


def abrir_conexion(
    ruta: str | Path | None = None, *, synchronous: Sincronizacion = "FULL"
) -> sqlite3.Connection:
    """Abre una conexión configurada. `ruta=None` usa `config.rutas.ruta_bd()`.

    `synchronous` es un conjunto cerrado (`FULL` | `NORMAL` | `OFF`); se valida
    la pertenencia antes de interpolarlo en el PRAGMA, nunca se acepta una
    cadena libre.
    """
    if synchronous not in _VALORES_SYNCHRONOUS:
        raise ValueError(f"synchronous inválido: {synchronous!r}")

    if ruta is None:
        asegurar_estructura()
        ruta = ruta_bd()
    ruta_texto = str(ruta)
    en_memoria = ruta_texto == ":memory:"

    try:
        con = sqlite3.connect(ruta_texto, isolation_level=None, check_same_thread=True)
    except sqlite3.Error as error:
        raise ErrorBaseCorrupta("error.base_corrupta", detalle=str(error)) from error

    con.row_factory = sqlite3.Row

    # Orden obligatorio: busy_timeout ANTES de journal_mode=WAL.
    con.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")
    if not en_memoria:
        con.execute("PRAGMA journal_mode = WAL")
    con.execute("PRAGMA foreign_keys = ON")
    con.execute(f"PRAGMA synchronous = {synchronous}")

    fila_fk = con.execute("PRAGMA foreign_keys").fetchone()
    if fila_fk is None or fila_fk[0] != 1:
        con.close()
        raise ErrorPersistencia(
            "error.persistencia", detalle="PRAGMA foreign_keys no quedó activado"
        )

    if not en_memoria:
        fila_wal = con.execute("PRAGMA journal_mode").fetchone()
        if fila_wal is None or str(fila_wal[0]).lower() != "wal":
            con.close()
            raise ErrorPersistencia(
                "error.persistencia",
                detalle=f"PRAGMA journal_mode no quedó en wal (valor: {fila_wal})",
            )

    return con


def cerrar_conexion(con: sqlite3.Connection) -> None:
    con.close()


@contextmanager
def transaccion(con: sqlite3.Connection) -> Iterator[sqlite3.Connection]:
    """`BEGIN IMMEDIATE` / `COMMIT` explícitos, con `ROLLBACK` ante excepción.

    No es reentrante: anidarla lanza `ErrorPersistencia` con un mensaje claro
    en vez de dejar que SQLite lance `OperationalError: cannot start a
    transaction within a transaction`.
    """
    if con.in_transaction:
        raise ErrorPersistencia(
            "error.persistencia", detalle="transaccion() anidada: ya hay una transacción abierta"
        )
    con.execute("BEGIN IMMEDIATE")
    try:
        yield con
    except BaseException:
        con.rollback()
        raise
    else:
        con.commit()
