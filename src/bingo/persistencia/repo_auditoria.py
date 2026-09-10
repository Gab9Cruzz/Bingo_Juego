"""Repositorio de `auditoria`. Nombre de función fijado por el contrato de la
fase; es la única excepción a la tabla de verbos de `docs/convenciones-codigo.md`.
"""

from __future__ import annotations

import sqlite3

from bingo.dominio.modelos import RegistroAuditoria
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.utilidades.fechas import ahora_iso


def _desde_fila(fila: sqlite3.Row) -> RegistroAuditoria:
    return RegistroAuditoria(
        id=fila["id"],
        evento_id=fila["evento_id"],
        momento=fila["momento"],
        accion=fila["accion"],
        detalle=fila["detalle"],
    )


def registrar(
    con: sqlite3.Connection, evento_id: int | None, accion: str, detalle: str | None = None
) -> None:
    """`evento_id=None` para acciones de nivel organización o aplicación."""
    with traducir_errores_sqlite():
        con.execute(
            "INSERT INTO auditoria (evento_id, momento, accion, detalle) VALUES (?, ?, ?, ?)",
            (evento_id, ahora_iso(), accion, detalle),
        )


def listar_por_evento(
    con: sqlite3.Connection, evento_id: int, limite: int = 200
) -> list[RegistroAuditoria]:
    filas = con.execute(
        "SELECT * FROM auditoria WHERE evento_id = ? ORDER BY momento DESC LIMIT ?",
        (evento_id, limite),
    ).fetchall()
    return [_desde_fila(f) for f in filas]


def eliminar_por_evento_y_prefijo(con: sqlite3.Connection, evento_id: int, prefijo: str) -> int:
    """Barrido selectivo de auditoría (fase 4, hallazgo A3): el borrado de
    datos personales de un comprador (`servicio_compradores.
    eliminar_todos_del_evento`) solo debe llevarse las acciones `venta.*`,
    que son las únicas que referencian datos de compradores — nunca
    `lote.creado`, `carton.cambio_estado` u otras que un panel de auditoría
    del evento sigue necesitando."""
    with traducir_errores_sqlite():
        cursor = con.execute(
            "DELETE FROM auditoria WHERE evento_id = ? AND accion LIKE ?",
            (evento_id, f"{prefijo}%"),
        )
    return cursor.rowcount
