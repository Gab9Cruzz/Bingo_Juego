"""Repositorio de `ronda`. Toda consulta SQL de esta entidad vive aquí.

`desplazar_ordenes_a_negativo` + `actualizar_orden` es el mecanismo de
reordenado en dos pasadas (decisión D5, corregido por el hallazgo C1 del
plan de la fase 4): `UNIQUE(evento_id, orden)` se comprueba por sentencia en
SQLite, no al final de la transacción, así que un intercambio directo
colisiona a mitad de camino. El SQL vive aquí — `servicio_rondas.reordenar`
solo orquesta las dos llamadas dentro de una `transaccion()`, nunca ejecuta
SQL propio (`tests/arquitectura/test_arquitectura.py` lo prohibiría).
"""

from __future__ import annotations

import dataclasses
import sqlite3

from bingo.dominio.modelos import Ronda
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite

_COLUMNAS = (
    "evento_id",
    "orden",
    "nombre",
    "patron_id",
    "premio_nombre",
    "premio_tipo",
    "premio_valor_centavos",
    "premio_descripcion",
    "premio_imagen",
    "estado",
)


def _desde_fila(fila: sqlite3.Row) -> Ronda:
    return Ronda(
        id=fila["id"],
        evento_id=fila["evento_id"],
        orden=fila["orden"],
        nombre=fila["nombre"],
        patron_id=fila["patron_id"],
        premio_nombre=fila["premio_nombre"],
        premio_tipo=fila["premio_tipo"],
        premio_valor_centavos=fila["premio_valor_centavos"],
        premio_descripcion=fila["premio_descripcion"],
        premio_imagen=fila["premio_imagen"],
        estado=fila["estado"],
    )


def _a_parametros(ronda: Ronda) -> dict[str, object]:
    return {
        "evento_id": ronda.evento_id,
        "orden": ronda.orden,
        "nombre": ronda.nombre,
        "patron_id": ronda.patron_id,
        "premio_nombre": ronda.premio_nombre,
        "premio_tipo": ronda.premio_tipo,
        "premio_valor_centavos": ronda.premio_valor_centavos,
        "premio_descripcion": ronda.premio_descripcion,
        "premio_imagen": ronda.premio_imagen,
        "estado": ronda.estado,
    }


def crear(con: sqlite3.Connection, ronda: Ronda) -> Ronda:
    parametros = _a_parametros(ronda)
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        cursor = con.execute(f"INSERT INTO ronda ({columnas}) VALUES ({marcadores})", parametros)
    return dataclasses.replace(ronda, id=cursor.lastrowid)


def obtener(con: sqlite3.Connection, ronda_id: int) -> Ronda | None:
    fila = con.execute("SELECT * FROM ronda WHERE id = ?", (ronda_id,)).fetchone()
    return _desde_fila(fila) if fila is not None else None


def listar_por_evento(con: sqlite3.Connection, evento_id: int) -> list[Ronda]:
    filas = con.execute(
        "SELECT * FROM ronda WHERE evento_id = ? ORDER BY orden", (evento_id,)
    ).fetchall()
    return [_desde_fila(f) for f in filas]


def orden_maximo(con: sqlite3.Connection, evento_id: int) -> int:
    """`MAX(orden)` del evento, 0 si no tiene rondas. `servicio_rondas.
    crear_ronda` suma 1. Deliberadamente no es `contar_por_evento` (hallazgo
    M2): un evento con rondas borradas puede tener huecos en `orden`, y
    `COUNT + 1` reutilizaría un valor ya usado."""
    fila = con.execute(
        "SELECT MAX(orden) AS maximo FROM ronda WHERE evento_id = ?", (evento_id,)
    ).fetchone()
    return fila["maximo"] if fila and fila["maximo"] is not None else 0


def actualizar(con: sqlite3.Connection, ronda: Ronda) -> None:
    if ronda.id is None:
        raise ValueError("No se puede actualizar una ronda sin id")
    parametros = _a_parametros(ronda)
    parametros["id"] = ronda.id
    asignaciones = ", ".join(f"{c} = :{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        con.execute(f"UPDATE ronda SET {asignaciones} WHERE id = :id", parametros)


def actualizar_orden(con: sqlite3.Connection, ronda_id: int, orden: int) -> None:
    with traducir_errores_sqlite():
        con.execute("UPDATE ronda SET orden = ? WHERE id = ?", (orden, ronda_id))


def desplazar_ordenes_a_negativo(con: sqlite3.Connection, evento_id: int) -> int:
    """Primera pasada del reordenado (decisión D5 + hallazgo C1): saca todas
    las filas del rango positivo de `orden` sin colisionar entre sí, para
    que la segunda pasada (`actualizar_orden` por fila, 1..N) nunca choque
    con `UNIQUE(evento_id, orden)`. `-(orden + 1)` evita el punto fijo
    `orden = 0` y garantiza que ninguna fila quede en el rango positivo
    entre las dos pasadas."""
    with traducir_errores_sqlite():
        cursor = con.execute(
            "UPDATE ronda SET orden = -(orden + 1) WHERE evento_id = ?", (evento_id,)
        )
    return cursor.rowcount


def eliminar(con: sqlite3.Connection, ronda_id: int) -> None:
    with traducir_errores_sqlite():
        con.execute("DELETE FROM ronda WHERE id = ?", (ronda_id,))


def contar_por_patron(con: sqlite3.Connection, patron_id: int) -> int:
    fila = con.execute(
        "SELECT COUNT(*) AS n FROM ronda WHERE patron_id = ?", (patron_id,)
    ).fetchone()
    return fila["n"] if fila else 0


def contar_por_patron_en_eventos_no_borrador(con: sqlite3.Connection, patron_id: int) -> int:
    """Usado por `servicio_patrones.asegurar_patrones_sistema` (decisión
    DS16): no actualiza en silencio la definición de un patrón del sistema
    si ya lo usa una ronda de un evento que salió de `borrador` — cambiaría
    quién gana un premio en un evento que puede estar en curso."""
    fila = con.execute(
        "SELECT COUNT(*) AS n FROM ronda "
        "JOIN evento ON evento.id = ronda.evento_id "
        "WHERE ronda.patron_id = ? AND evento.estado != 'borrador'",
        (patron_id,),
    ).fetchone()
    return fila["n"] if fila else 0
