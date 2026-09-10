"""Repositorio de `comprador`. Toda consulta SQL de esta entidad vive aquí.

`anular` es un borrado lógico (columna `anulado_en`), no un `DELETE`
(decisión A3 del plan de la fase 4): la auditoría de una venta anulada tiene
que seguir apuntando a una fila que existe. `eliminar_por_evento` sí borra
físicamente — es el mecanismo de retención de datos personales (`TODOS.md`
P1), deliberadamente distinto y con nombre distinto.

El índice único real es parcial (`idx_comprador_carton_vivo`,
`WHERE anulado_en IS NULL`): un cartón puede tener más de una fila
`comprador` a lo largo del tiempo si las anteriores están anuladas.
"""

from __future__ import annotations

import dataclasses
import sqlite3

from bingo.dominio.modelos import Comprador
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.utilidades.fechas import ahora_iso

_COLUMNAS = (
    "carton_id",
    "nombre",
    "telefono",
    "cedula",
    "correo",
    "provisional",
    "estado_carton_previo",
    "anulado_en",
    "registrado_en",
)


def _desde_fila(fila: sqlite3.Row) -> Comprador:
    return Comprador(
        id=fila["id"],
        carton_id=fila["carton_id"],
        nombre=fila["nombre"],
        telefono=fila["telefono"],
        cedula=fila["cedula"],
        correo=fila["correo"],
        provisional=bool(fila["provisional"]),
        estado_carton_previo=fila["estado_carton_previo"],
        anulado_en=fila["anulado_en"],
        registrado_en=fila["registrado_en"],
    )


def _a_parametros(comprador: Comprador) -> dict[str, object]:
    return {
        "carton_id": comprador.carton_id,
        "nombre": comprador.nombre,
        "telefono": comprador.telefono,
        "cedula": comprador.cedula,
        "correo": comprador.correo,
        "provisional": int(comprador.provisional),
        "estado_carton_previo": comprador.estado_carton_previo,
        "anulado_en": comprador.anulado_en,
        "registrado_en": comprador.registrado_en or ahora_iso(),
    }


def crear(con: sqlite3.Connection, comprador: Comprador) -> Comprador:
    parametros = _a_parametros(comprador)
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        cursor = con.execute(
            f"INSERT INTO comprador ({columnas}) VALUES ({marcadores})", parametros
        )
    return dataclasses.replace(
        comprador, id=cursor.lastrowid, registrado_en=parametros["registrado_en"]
    )


def crear_varios(con: sqlite3.Connection, compradores: list[Comprador]) -> int:
    """`executemany` para la importación masiva (fase 4, decisión D6)."""
    if not compradores:
        return 0
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    parametros = [_a_parametros(c) for c in compradores]
    with traducir_errores_sqlite():
        con.executemany(f"INSERT INTO comprador ({columnas}) VALUES ({marcadores})", parametros)
    return len(compradores)


def obtener(con: sqlite3.Connection, comprador_id: int) -> Comprador | None:
    fila = con.execute("SELECT * FROM comprador WHERE id = ?", (comprador_id,)).fetchone()
    return _desde_fila(fila) if fila is not None else None


def obtener_por_carton(
    con: sqlite3.Connection, carton_id: int, *, incluir_anulados: bool = False
) -> Comprador | None:
    """El comprador vivo de un cartón. Con `incluir_anulados=True` puede
    devolver el más reciente aunque esté anulado (historial)."""
    if incluir_anulados:
        fila = con.execute(
            "SELECT * FROM comprador WHERE carton_id = ? ORDER BY id DESC LIMIT 1",
            (carton_id,),
        ).fetchone()
    else:
        fila = con.execute(
            "SELECT * FROM comprador WHERE carton_id = ? AND anulado_en IS NULL",
            (carton_id,),
        ).fetchone()
    return _desde_fila(fila) if fila is not None else None


def listar_por_evento(
    con: sqlite3.Connection,
    evento_id: int,
    *,
    texto_busqueda: str | None = None,
    provisional: bool | None = None,
    limite: int | None = None,
    desplazamiento: int = 0,
) -> list[Comprador]:
    """Compradores vivos de un evento, con JOIN a `carton` para poder buscar
    por código o por nombre (contrato §4.1)."""
    condiciones = ["carton.evento_id = ?", "comprador.anulado_en IS NULL"]
    parametros: list[object] = [evento_id]
    if provisional is not None:
        condiciones.append("comprador.provisional = ?")
        parametros.append(int(provisional))
    if texto_busqueda:
        condiciones.append(
            "(carton.codigo LIKE ? ESCAPE '\\' OR comprador.nombre LIKE ? ESCAPE '\\')"
        )
        comodin = texto_busqueda.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        parametros += [f"%{comodin}%", f"%{comodin}%"]

    sql = (
        "SELECT comprador.* FROM comprador "
        "JOIN carton ON carton.id = comprador.carton_id "
        f"WHERE {' AND '.join(condiciones)} ORDER BY carton.codigo"
    )
    if limite is not None:
        sql += " LIMIT ? OFFSET ?"
        parametros += [limite, desplazamiento]
    filas = con.execute(sql, parametros).fetchall()
    return [_desde_fila(f) for f in filas]


def mapa_por_evento(con: sqlite3.Connection, evento_id: int) -> dict[int, Comprador]:
    """`{carton_id: Comprador}` de todos los compradores vivos del evento en
    una sola consulta (hallazgo A10 del plan de la fase 4): la validación en
    seco de la importación no puede pagar un `SELECT` por fila del Excel.
    """
    filas = con.execute(
        "SELECT comprador.* FROM comprador "
        "JOIN carton ON carton.id = comprador.carton_id "
        "WHERE carton.evento_id = ? AND comprador.anulado_en IS NULL",
        (evento_id,),
    ).fetchall()
    return {f["carton_id"]: _desde_fila(f) for f in filas}


def contar_por_evento(
    con: sqlite3.Connection, evento_id: int, *, provisional: bool | None = None
) -> int:
    condiciones = ["carton.evento_id = ?", "comprador.anulado_en IS NULL"]
    parametros: list[object] = [evento_id]
    if provisional is not None:
        condiciones.append("comprador.provisional = ?")
        parametros.append(int(provisional))
    fila = con.execute(
        "SELECT COUNT(*) AS n FROM comprador "
        "JOIN carton ON carton.id = comprador.carton_id "
        f"WHERE {' AND '.join(condiciones)}",
        parametros,
    ).fetchone()
    return fila["n"] if fila else 0


def actualizar(con: sqlite3.Connection, comprador: Comprador) -> None:
    if comprador.id is None:
        raise ValueError("No se puede actualizar un comprador sin id")
    parametros = _a_parametros(comprador)
    parametros["id"] = comprador.id
    asignaciones = ", ".join(f"{c} = :{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        con.execute(f"UPDATE comprador SET {asignaciones} WHERE id = :id", parametros)


def anular(con: sqlite3.Connection, comprador_id: int) -> None:
    """Borrado lógico: fija `anulado_en`. No toca el estado del cartón — eso
    lo hace el servicio, junto con el registro de auditoría, en la misma
    transacción."""
    with traducir_errores_sqlite():
        con.execute("UPDATE comprador SET anulado_en = ? WHERE id = ?", (ahora_iso(), comprador_id))


def eliminar_por_evento(con: sqlite3.Connection, evento_id: int) -> int:
    """Borrado físico de todos los compradores (vivos y anulados) de un
    evento — el mecanismo real de retención LOPDP (`TODOS.md` P1), distinto
    a `anular`."""
    with traducir_errores_sqlite():
        cursor = con.execute(
            "DELETE FROM comprador WHERE carton_id IN (SELECT id FROM carton WHERE evento_id = ?)",
            (evento_id,),
        )
    return cursor.rowcount
