"""Repositorio de `patron`. Toda consulta SQL de esta entidad vive aquí.

`mascaras` se serializa a JSON al escribir y se valida al leer: una fila con
`mascaras` nula o vacía significaría "nadie gana nunca" propagado en
silencio por `dominio.patron.es_ganador` (`any([])` es `False`) — se trata
como corrupción de datos, no como un patrón válido sin variantes.
"""

from __future__ import annotations

import dataclasses
import json
import sqlite3

from bingo.dominio.modelos import Patron
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.utilidades.errores import ErrorIntegridad

_COLUMNAS = (
    "nombre",
    "clave_i18n",
    "mascaras",
    "descripcion",
    "usa_libre",
    "es_sistema",
    "version_semilla",
    "organizacion_id",
)


def _desde_fila(fila: sqlite3.Row) -> Patron:
    try:
        mascaras = json.loads(fila["mascaras"])
        if not isinstance(mascaras, list) or not mascaras:
            raise ValueError("mascaras vacía o con forma inesperada")
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        raise ErrorIntegridad(
            "error.integridad.check",
            tipo="check",
            restriccion="patron.mascaras",
            detalle=f"patron.id={fila['id']}: {error}",
        ) from error
    return Patron(
        id=fila["id"],
        nombre=fila["nombre"],
        mascaras=[int(m) for m in mascaras],
        clave_i18n=fila["clave_i18n"],
        descripcion=fila["descripcion"],
        usa_libre=bool(fila["usa_libre"]),
        es_sistema=bool(fila["es_sistema"]),
        version_semilla=fila["version_semilla"],
        organizacion_id=fila["organizacion_id"],
    )


def _a_parametros(patron: Patron) -> dict[str, object]:
    if not patron.mascaras:
        raise ErrorIntegridad(
            "error.integridad.check",
            tipo="check",
            restriccion="patron.mascaras",
            detalle="No se puede escribir un patrón sin máscaras",
        )
    return {
        "nombre": patron.nombre,
        "clave_i18n": patron.clave_i18n,
        "mascaras": json.dumps(patron.mascaras),
        "descripcion": patron.descripcion,
        "usa_libre": int(patron.usa_libre),
        "es_sistema": int(patron.es_sistema),
        "version_semilla": patron.version_semilla,
        "organizacion_id": patron.organizacion_id,
    }


def crear(con: sqlite3.Connection, patron: Patron) -> Patron:
    parametros = _a_parametros(patron)
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        cursor = con.execute(f"INSERT INTO patron ({columnas}) VALUES ({marcadores})", parametros)
    return dataclasses.replace(patron, id=cursor.lastrowid)


def obtener(con: sqlite3.Connection, patron_id: int) -> Patron | None:
    fila = con.execute("SELECT * FROM patron WHERE id = ?", (patron_id,)).fetchone()
    return _desde_fila(fila) if fila is not None else None


def obtener_por_clave_i18n(con: sqlite3.Connection, clave_i18n: str) -> Patron | None:
    fila = con.execute("SELECT * FROM patron WHERE clave_i18n = ?", (clave_i18n,)).fetchone()
    return _desde_fila(fila) if fila is not None else None


def listar(
    con: sqlite3.Connection,
    *,
    organizacion_id: int | None = None,
    incluir_sistema: bool = True,
    limite: int | None = None,
    desplazamiento: int = 0,
) -> list[Patron]:
    """Patrones visibles para una organización: los del sistema
    (`organizacion_id IS NULL`) más los propios de `organizacion_id`, si se
    da. `incluir_sistema=False` limita a los propios de la organización
    (usado por el selector cuando ya se pintan los del sistema aparte)."""
    condiciones: list[str] = []
    parametros: list[object] = []
    if organizacion_id is not None and incluir_sistema:
        condiciones.append("(organizacion_id = ? OR organizacion_id IS NULL)")
        parametros.append(organizacion_id)
    elif organizacion_id is not None:
        condiciones.append("organizacion_id = ?")
        parametros.append(organizacion_id)
    elif not incluir_sistema:
        condiciones.append("organizacion_id IS NOT NULL")

    sql = "SELECT * FROM patron"
    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)
    sql += " ORDER BY es_sistema DESC, nombre"
    if limite is not None:
        sql += " LIMIT ? OFFSET ?"
        parametros += [limite, desplazamiento]
    filas = con.execute(sql, parametros).fetchall()
    return [_desde_fila(f) for f in filas]


def existe_nombre(
    con: sqlite3.Connection,
    organizacion_id: int | None,
    nombre: str,
    excluir_id: int | None = None,
) -> bool:
    condiciones = ["nombre = ? COLLATE NOCASE"]
    parametros: list[object] = [nombre]
    if organizacion_id is None:
        condiciones.append("organizacion_id IS NULL")
    else:
        condiciones.append("organizacion_id = ?")
        parametros.append(organizacion_id)
    if excluir_id is not None:
        condiciones.append("id != ?")
        parametros.append(excluir_id)
    fila = con.execute(
        f"SELECT 1 FROM patron WHERE {' AND '.join(condiciones)}", parametros
    ).fetchone()
    return fila is not None


def actualizar(con: sqlite3.Connection, patron: Patron) -> None:
    if patron.id is None:
        raise ValueError("No se puede actualizar un patrón sin id")
    parametros = _a_parametros(patron)
    parametros["id"] = patron.id
    asignaciones = ", ".join(f"{c} = :{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        con.execute(f"UPDATE patron SET {asignaciones} WHERE id = :id", parametros)


def eliminar(con: sqlite3.Connection, patron_id: int) -> None:
    with traducir_errores_sqlite():
        con.execute("DELETE FROM patron WHERE id = ?", (patron_id,))


def contar_por_es_sistema(con: sqlite3.Connection) -> int:
    fila = con.execute("SELECT COUNT(*) AS n FROM patron WHERE es_sistema = 1").fetchone()
    return fila["n"] if fila else 0
