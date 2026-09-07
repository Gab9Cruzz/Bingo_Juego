"""Repositorio de `lote`. Toda consulta SQL de esta entidad vive aquí.

`completado_en` es la columna que decide si un lote quedó huérfano (proceso
muerto a mitad de `generar_lote`): se fija dentro de la misma transacción que
cierra el lote con éxito, nunca se infiere de `auditoria` (ver la revisión de
ingeniería de la fase 2 — inferir el estado del texto de auditoría resultó ser
una condición lógicamente imposible de construir).
"""

from __future__ import annotations

import dataclasses
import sqlite3

from bingo.dominio.modelos import Lote
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.utilidades.fechas import ahora_iso

_COLUMNAS = ("evento_id", "cantidad", "prefijo_codigo", "semilla", "generado_en", "completado_en")


def _desde_fila(fila: sqlite3.Row) -> Lote:
    return Lote(
        id=fila["id"],
        evento_id=fila["evento_id"],
        cantidad=fila["cantidad"],
        prefijo_codigo=fila["prefijo_codigo"],
        semilla=fila["semilla"],
        generado_en=fila["generado_en"],
        completado_en=fila["completado_en"],
    )


def _a_parametros(lote: Lote) -> dict[str, object]:
    return {
        "evento_id": lote.evento_id,
        "cantidad": lote.cantidad,
        "prefijo_codigo": lote.prefijo_codigo,
        "semilla": lote.semilla,
        "generado_en": lote.generado_en or ahora_iso(),
        "completado_en": lote.completado_en,
    }


def crear(con: sqlite3.Connection, lote: Lote) -> Lote:
    """Inserta el lote. Devuelve la copia persistida (con `id`)."""
    parametros = _a_parametros(lote)
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        cursor = con.execute(f"INSERT INTO lote ({columnas}) VALUES ({marcadores})", parametros)
    return dataclasses.replace(lote, id=cursor.lastrowid, generado_en=parametros["generado_en"])


def obtener(con: sqlite3.Connection, lote_id: int) -> Lote | None:
    fila = con.execute("SELECT * FROM lote WHERE id = ?", (lote_id,)).fetchone()
    return _desde_fila(fila) if fila is not None else None


def listar_por_evento(con: sqlite3.Connection, evento_id: int) -> list[Lote]:
    filas = con.execute(
        "SELECT * FROM lote WHERE evento_id = ? ORDER BY generado_en DESC", (evento_id,)
    ).fetchall()
    return [_desde_fila(f) for f in filas]


def existe_prefijo(con: sqlite3.Connection, evento_id: int, prefijo_codigo: str) -> bool:
    fila = con.execute(
        "SELECT 1 FROM lote WHERE evento_id = ? AND prefijo_codigo = ?",
        (evento_id, prefijo_codigo),
    ).fetchone()
    return fila is not None


def marcar_completado(con: sqlite3.Connection, lote_id: int) -> None:
    with traducir_errores_sqlite():
        con.execute("UPDATE lote SET completado_en = ? WHERE id = ?", (ahora_iso(), lote_id))


def listar_huerfanos(con: sqlite3.Connection) -> list[Lote]:
    """Lotes sin `completado_en`: proceso muerto a mitad de generación.

    No distingue "recién creado, todavía generando" de "huérfano de verdad"
    porque no hay forma de distinguirlos desde una conexión nueva al arrancar
    la app — si el proceso anterior murió, esta lista es exactamente la que
    hay que limpiar; si por algún motivo se llama mientras otra generación
    está en curso en el mismo proceso, el llamante es responsable de no
    invocar el barrido en ese momento (en la práctica: solo se llama una vez,
    al arrancar, antes de que exista ninguna `Tarea`).
    """
    filas = con.execute("SELECT * FROM lote WHERE completado_en IS NULL").fetchall()
    return [_desde_fila(f) for f in filas]


def eliminar(con: sqlite3.Connection, lote_id: int) -> None:
    with traducir_errores_sqlite():
        con.execute("DELETE FROM lote WHERE id = ?", (lote_id,))
