"""Repositorio de `extraccion`. Toda consulta SQL de esta entidad vive aquí.

Una fila por bola salida de una ronda. `UNIQUE(ronda_id, orden)` y
`UNIQUE(ronda_id, numero)` (001) garantizan también en la base que el bombo
no repite — `crear()` deja que una violación de esas restricciones llegue
como `ErrorIntegridad` normal, nunca la comprueba por adelantado.
"""

from __future__ import annotations

import dataclasses
import sqlite3

from bingo.dominio.modelos import Extraccion
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.utilidades.fechas import ahora_iso

_COLUMNAS = ("ronda_id", "orden", "numero", "extraida_en")


def _desde_fila(fila: sqlite3.Row) -> Extraccion:
    return Extraccion(
        id=fila["id"],
        ronda_id=fila["ronda_id"],
        orden=fila["orden"],
        numero=fila["numero"],
        extraida_en=fila["extraida_en"],
    )


def _a_parametros(extraccion: Extraccion) -> dict[str, object]:
    return {
        "ronda_id": extraccion.ronda_id,
        "orden": extraccion.orden,
        "numero": extraccion.numero,
        "extraida_en": extraccion.extraida_en or ahora_iso(),
    }


def crear(con: sqlite3.Connection, extraccion: Extraccion) -> Extraccion:
    parametros = _a_parametros(extraccion)
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        cursor = con.execute(
            f"INSERT INTO extraccion ({columnas}) VALUES ({marcadores})", parametros
        )
    return dataclasses.replace(
        extraccion, id=cursor.lastrowid, extraida_en=parametros["extraida_en"]
    )


def listar_por_ronda(con: sqlite3.Connection, ronda_id: int) -> list[Extraccion]:
    filas = con.execute(
        "SELECT * FROM extraccion WHERE ronda_id = ? ORDER BY orden", (ronda_id,)
    ).fetchall()
    return [_desde_fila(f) for f in filas]


def contar_por_ronda(con: sqlite3.Connection, ronda_id: int) -> int:
    fila = con.execute(
        "SELECT COUNT(*) AS n FROM extraccion WHERE ronda_id = ?", (ronda_id,)
    ).fetchone()
    return fila["n"] if fila else 0


def numeros_por_ronda(con: sqlite3.Connection, ronda_id: int) -> list[int]:
    """Solo los números, en orden de salida — lo que `MotorSorteo.
    reanudar_ronda` necesita para reproducir el bombo y el `marcado` de cada
    cartón sin cargar filas completas que no va a usar."""
    filas = con.execute(
        "SELECT numero FROM extraccion WHERE ronda_id = ? ORDER BY orden", (ronda_id,)
    ).fetchall()
    return [f["numero"] for f in filas]


def eliminar_por_ronda(con: sqlite3.Connection, ronda_id: int) -> None:
    with traducir_errores_sqlite():
        con.execute("DELETE FROM extraccion WHERE ronda_id = ?", (ronda_id,))
