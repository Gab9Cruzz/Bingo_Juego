"""Repositorio de `carton`. Toda consulta SQL de esta entidad vive aquí.

`crear_varios` es la única función de este repo que no sigue la firma
`(con, modelo)` de la tabla de verbos: recibe una lista y usa `executemany`,
tal como `docs/convenciones-codigo.md` documenta para ese verbo.
`actualizar_estado` escribe y nada más — la validación de la transición vive
en `dominio/estados.py` y la aplica el servicio, igual que `repo_evento.py`.
"""

from __future__ import annotations

import sqlite3

from bingo.dominio.modelos import Carton
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite

_COLUMNAS = ("evento_id", "lote_id", "codigo", "numeros", "firma", "estado")


def _desde_fila(fila: sqlite3.Row) -> Carton:
    return Carton(
        id=fila["id"],
        evento_id=fila["evento_id"],
        lote_id=fila["lote_id"],
        codigo=fila["codigo"],
        numeros=fila["numeros"],
        firma=fila["firma"],
        estado=fila["estado"],
    )


def _a_parametros(carton: Carton) -> dict[str, object]:
    return {
        "evento_id": carton.evento_id,
        "lote_id": carton.lote_id,
        "codigo": carton.codigo,
        "numeros": carton.numeros,
        "firma": carton.firma,
        "estado": carton.estado,
    }


def crear_varios(con: sqlite3.Connection, cartones: list[Carton]) -> int:
    """Inserta un bloque de cartones con `executemany`. Devuelve cuántos se insertaron.

    No participa de la unicidad de firma en memoria (eso lo resuelve el
    servicio antes de llamar aquí): si de todos modos llega un duplicado real
    (bug futuro, no camino esperado), el `UNIQUE(evento_id, firma)` de la base
    lo rechaza con `ErrorIntegridad`, que se propaga sin reintento silencioso.
    """
    if not cartones:
        return 0
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    parametros = [_a_parametros(c) for c in cartones]
    with traducir_errores_sqlite():
        con.executemany(f"INSERT INTO carton ({columnas}) VALUES ({marcadores})", parametros)
    return len(cartones)


def obtener(con: sqlite3.Connection, carton_id: int) -> Carton | None:
    fila = con.execute("SELECT * FROM carton WHERE id = ?", (carton_id,)).fetchone()
    return _desde_fila(fila) if fila is not None else None


def obtener_por_codigo(con: sqlite3.Connection, evento_id: int, codigo: str) -> Carton | None:
    fila = con.execute(
        "SELECT * FROM carton WHERE evento_id = ? AND codigo = ?", (evento_id, codigo)
    ).fetchone()
    return _desde_fila(fila) if fila is not None else None


def listar_por_evento(
    con: sqlite3.Connection,
    evento_id: int,
    *,
    estado: str | None = None,
    texto_busqueda: str | None = None,
    limite: int | None = None,
    desplazamiento: int = 0,
) -> list[Carton]:
    condiciones = ["evento_id = ?"]
    parametros: list[object] = [evento_id]
    if estado is not None:
        condiciones.append("estado = ?")
        parametros.append(estado)
    if texto_busqueda:
        condiciones.append("codigo LIKE ? ESCAPE '\\'")
        comodin = texto_busqueda.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        parametros.append(f"%{comodin}%")

    sql = f"SELECT * FROM carton WHERE {' AND '.join(condiciones)} ORDER BY codigo"
    if limite is not None:
        sql += " LIMIT ? OFFSET ?"
        parametros += [limite, desplazamiento]
    filas = con.execute(sql, parametros).fetchall()
    return [_desde_fila(f) for f in filas]


def listar_por_lote(
    con: sqlite3.Connection,
    lote_id: int,
    *,
    limite: int | None = None,
    desplazamiento: int = 0,
) -> list[Carton]:
    """Todos los cartones de un lote, en orden de código (fase 3: la fuente
    de `servicio_impresion.generar_pdf_lote`, que necesita imprimirlos en un
    orden estable y reproducible, no el de `id`)."""
    sql = "SELECT * FROM carton WHERE lote_id = ? ORDER BY codigo"
    parametros: list[object] = [lote_id]
    if limite is not None:
        sql += " LIMIT ? OFFSET ?"
        parametros += [limite, desplazamiento]
    filas = con.execute(sql, parametros).fetchall()
    return [_desde_fila(f) for f in filas]


def contar_por_lote(con: sqlite3.Connection, lote_id: int) -> int:
    fila = con.execute("SELECT COUNT(*) AS n FROM carton WHERE lote_id = ?", (lote_id,)).fetchone()
    return fila["n"] if fila else 0


def contar_por_estado(con: sqlite3.Connection, evento_id: int) -> dict[str, int]:
    filas = con.execute(
        "SELECT estado, COUNT(*) AS n FROM carton WHERE evento_id = ? GROUP BY estado",
        (evento_id,),
    ).fetchall()
    return {f["estado"]: f["n"] for f in filas}


def listar_firmas_por_evento(con: sqlite3.Connection, evento_id: int) -> set[str]:
    """Todas las firmas ya usadas en el evento, en una sola consulta.

    El servicio de generación precarga esto una vez por lote y mantiene el
    control de unicidad en memoria durante toda la generación — evitar una
    consulta por cartón es la diferencia entre generar 10.000 cartones en
    segundos o en minutos.
    """
    filas = con.execute("SELECT firma FROM carton WHERE evento_id = ?", (evento_id,)).fetchall()
    return {f["firma"] for f in filas}


def actualizar_estado(con: sqlite3.Connection, carton_id: int, estado: str) -> None:
    """Escribe el estado ya validado por el dominio. No valida la transición."""
    with traducir_errores_sqlite():
        con.execute("UPDATE carton SET estado = ? WHERE id = ?", (estado, carton_id))


def actualizar_estado_por_lote(
    con: sqlite3.Connection, lote_id: int, estado_actual: str, estado_nuevo: str
) -> int:
    """Cambia a `estado_nuevo` solo los cartones del lote que están en
    `estado_actual`. Devuelve cuántos cambió.

    Filtrar por `estado_actual` es obligatorio (fase 3, primer llamador real
    de esta función — ver `docs/Fase_3/Plan_Implementacion_Fase3.md` §0):
    "marcar el lote como impreso" no debe reescribir un cartón que ya esté
    `vendido` o `anulado` solo porque comparte `lote_id`.
    """
    with traducir_errores_sqlite():
        cursor = con.execute(
            "UPDATE carton SET estado = ? WHERE lote_id = ? AND estado = ?",
            (estado_nuevo, lote_id, estado_actual),
        )
    return cursor.rowcount


def eliminar_por_lote(con: sqlite3.Connection, lote_id: int) -> int:
    """Usado por la cancelación y por el barrido de lotes huérfanos. Devuelve cuántos borró."""
    with traducir_errores_sqlite():
        cursor = con.execute("DELETE FROM carton WHERE lote_id = ?", (lote_id,))
    return cursor.rowcount
