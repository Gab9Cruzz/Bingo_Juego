"""Único punto de traducción de excepciones de `sqlite3` a `ErrorBingo`.

Se aplica en la frontera de cada repositorio, envolviendo la llamada a
`execute`/`executemany`. Distingue por `sqlite3.Error.sqlite_errorname` y por
el texto del mensaje, y **conserva qué restricción falló** (`tipo` y
`restriccion`) porque la fase 2 depende de eso para decidir si reintenta la
generación de un cartón (firma duplicada) o si el fallo es otra cosa. El error
original de `sqlite3` se conserva siempre como `__cause__`.
"""

from __future__ import annotations

import re
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from bingo.utilidades.errores import (
    ErrorBaseBloqueada,
    ErrorBaseCorrupta,
    ErrorIntegridad,
    ErrorPersistencia,
    TipoRestriccion,
)

_PATRON_RESTRICCION = re.compile(r"constraint failed:\s*(.+)$", re.IGNORECASE)


def _restriccion_desde_mensaje(mensaje: str) -> str | None:
    coincidencia = _PATRON_RESTRICCION.search(mensaje)
    if coincidencia:
        return coincidencia.group(1).strip()
    return None


def _tipo_integridad(error: sqlite3.IntegrityError) -> TipoRestriccion:
    nombre = getattr(error, "sqlite_errorname", "") or ""
    mensaje = str(error).upper()
    if "UNIQUE" in nombre or "UNIQUE" in mensaje:
        return "unique"
    if "FOREIGNKEY" in nombre or "FOREIGN KEY" in mensaje:
        return "foreign_key"
    if "CHECK" in nombre or "CHECK" in mensaje:
        return "check"
    if "NOTNULL" in nombre or "NOT NULL" in mensaje:
        return "not_null"
    return "check"  # el conjunto está cerrado; caso no visto se trata como check


@contextmanager
def traducir_errores_sqlite() -> Iterator[None]:
    try:
        yield
    except sqlite3.IntegrityError as error:
        tipo = _tipo_integridad(error)
        restriccion = _restriccion_desde_mensaje(str(error))
        raise ErrorIntegridad(
            f"error.integridad.{tipo}",
            tipo=tipo,
            restriccion=restriccion,
            detalle=str(error),
        ) from error
    except sqlite3.OperationalError as error:
        nombre = getattr(error, "sqlite_errorname", "") or ""
        mensaje = str(error).lower()
        if "SQLITE_BUSY" in nombre or "SQLITE_LOCKED" in nombre or "database is locked" in mensaje:
            raise ErrorBaseBloqueada("error.base_bloqueada", detalle=str(error)) from error
        if "readonly" in mensaje or "SQLITE_READONLY" in nombre:
            raise ErrorPersistencia("error.sin_permisos", detalle=str(error)) from error
        if "disk" in mensaje and "full" in mensaje or "SQLITE_FULL" in nombre:
            raise ErrorPersistencia("error.disco_lleno", detalle=str(error)) from error
        if "SQLITE_IOERR" in nombre or "disk i/o error" in mensaje:
            raise ErrorPersistencia("error.persistencia", detalle=str(error)) from error
        raise ErrorPersistencia("error.persistencia", detalle=str(error)) from error
    except sqlite3.DatabaseError as error:
        nombre = getattr(error, "sqlite_errorname", "") or ""
        mensaje = str(error).lower()
        if "SQLITE_CORRUPT" in nombre or "SQLITE_NOTADB" in nombre or "not a database" in mensaje:
            raise ErrorBaseCorrupta("error.base_corrupta", detalle=str(error)) from error
        raise ErrorPersistencia("error.persistencia", detalle=str(error)) from error
