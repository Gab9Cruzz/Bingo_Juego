"""Repositorio de `organizacion`. Toda consulta SQL de esta entidad vive aquí.

No abre transacciones ni hace commit (ver `docs/convenciones-codigo.md`): eso
es responsabilidad de los servicios y de `__main__`.
"""

from __future__ import annotations

import dataclasses
import sqlite3

from bingo.dominio.modelos import Organizacion
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.utilidades.fechas import ahora_iso

_COLUMNAS = (
    "nombre",
    "logo_path",
    "logo_secundario",
    "color_primario",
    "color_secundario",
    "color_texto",
    "tipografia",
    "contacto",
    "eslogan",
    "pie_pagina",
    "condiciones",
    "aviso_legal",
    "creada_en",
)


def _desde_fila(fila: sqlite3.Row) -> Organizacion:
    return Organizacion(
        id=fila["id"],
        nombre=fila["nombre"],
        logo_path=fila["logo_path"],
        logo_secundario=fila["logo_secundario"],
        color_primario=fila["color_primario"],
        color_secundario=fila["color_secundario"],
        color_texto=fila["color_texto"],
        tipografia=fila["tipografia"],
        contacto=fila["contacto"],
        eslogan=fila["eslogan"],
        pie_pagina=fila["pie_pagina"],
        condiciones=fila["condiciones"],
        aviso_legal=fila["aviso_legal"],
        creada_en=fila["creada_en"],
    )


def _a_parametros(org: Organizacion) -> dict[str, object]:
    return {
        "nombre": org.nombre,
        "logo_path": org.logo_path,
        "logo_secundario": org.logo_secundario,
        "color_primario": org.color_primario,
        "color_secundario": org.color_secundario,
        "color_texto": org.color_texto,
        "tipografia": org.tipografia,
        "contacto": org.contacto,
        "eslogan": org.eslogan,
        "pie_pagina": org.pie_pagina,
        "condiciones": org.condiciones,
        "aviso_legal": org.aviso_legal,
        "creada_en": org.creada_en or ahora_iso(),
    }


def crear(con: sqlite3.Connection, org: Organizacion) -> Organizacion:
    """Inserta la organización. Devuelve la copia persistida (con `id`), no un `int` suelto."""
    parametros = _a_parametros(org)
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        cursor = con.execute(
            f"INSERT INTO organizacion ({columnas}) VALUES ({marcadores})", parametros
        )
    return dataclasses.replace(org, id=cursor.lastrowid, creada_en=parametros["creada_en"])


def obtener(con: sqlite3.Connection, organizacion_id: int) -> Organizacion | None:
    fila = con.execute(
        "SELECT * FROM organizacion WHERE id = ?", (organizacion_id,)
    ).fetchone()
    return _desde_fila(fila) if fila is not None else None


def listar(con: sqlite3.Connection) -> list[Organizacion]:
    filas = con.execute("SELECT * FROM organizacion ORDER BY nombre COLLATE NOCASE").fetchall()
    return [_desde_fila(f) for f in filas]


def actualizar(con: sqlite3.Connection, org: Organizacion) -> None:
    if org.id is None:
        raise ValueError("No se puede actualizar una organización sin id")
    parametros = _a_parametros(org)
    parametros["id"] = org.id
    asignaciones = ", ".join(f"{c} = :{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        con.execute(f"UPDATE organizacion SET {asignaciones} WHERE id = :id", parametros)


def contar_eventos(con: sqlite3.Connection, organizacion_id: int) -> int:
    fila = con.execute(
        "SELECT COUNT(*) AS n FROM evento WHERE organizacion_id = ?", (organizacion_id,)
    ).fetchone()
    return fila["n"]


def _contar_patrones_propios(con: sqlite3.Connection, organizacion_id: int) -> int:
    fila = con.execute(
        "SELECT COUNT(*) AS n FROM patron WHERE organizacion_id = ?", (organizacion_id,)
    ).fetchone()
    return fila["n"]


def eliminar(con: sqlite3.Connection, organizacion_id: int) -> None:
    """Elimina la organización. Falla si tiene eventos o patrones propios asociados.

    El contrato de la fase solo menciona eventos, pero `patron.organizacion_id`
    también apunta a esta tabla: dos claves foráneas entrantes, dos
    comprobaciones.
    """
    from bingo.utilidades.errores import ErrorIntegridad

    if contar_eventos(con, organizacion_id) > 0:
        raise ErrorIntegridad(
            "organizaciones.eliminar.bloqueado", tipo="foreign_key", restriccion="evento"
        )
    if _contar_patrones_propios(con, organizacion_id) > 0:
        raise ErrorIntegridad(
            "organizaciones.eliminar.bloqueado", tipo="foreign_key", restriccion="patron"
        )
    with traducir_errores_sqlite():
        con.execute("DELETE FROM organizacion WHERE id = ?", (organizacion_id,))


def existe_nombre(con: sqlite3.Connection, nombre: str, excluir_id: int | None = None) -> bool:
    if excluir_id is None:
        fila = con.execute(
            "SELECT 1 FROM organizacion WHERE nombre = ? COLLATE NOCASE", (nombre,)
        ).fetchone()
    else:
        fila = con.execute(
            "SELECT 1 FROM organizacion WHERE nombre = ? COLLATE NOCASE AND id != ?",
            (nombre, excluir_id),
        ).fetchone()
    return fila is not None
