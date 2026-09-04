"""Repositorio de `evento`. Toda consulta SQL de esta entidad vive aquí.

`actualizar_estado` escribe y nada más: la validación de la transición vive en
`dominio/estados.py` y la aplica `servicios/servicio_eventos.cambiar_estado`.
Meter la máquina de estados aquí sería lógica de negocio dentro de la capa de
SQL — justo la erosión que vuelve decorativa la regla del repositorio.
"""

from __future__ import annotations

import dataclasses
import json
import sqlite3

from bingo.dominio.modelos import Evento
from bingo.persistencia.errores_sqlite import traducir_errores_sqlite
from bingo.utilidades.errores import ErrorValidacion
from bingo.utilidades.fechas import ahora_iso

_COLUMNAS = (
    "organizacion_id",
    "nombre",
    "fecha",
    "hora",
    "lugar",
    "precio_tabla_centavos",
    "estado",
    "plantilla_json",
    "tema_json",
    "creado_en",
)


def _desde_fila(fila: sqlite3.Row) -> Evento:
    return Evento(
        id=fila["id"],
        organizacion_id=fila["organizacion_id"],
        nombre=fila["nombre"],
        fecha=fila["fecha"],
        hora=fila["hora"],
        lugar=fila["lugar"],
        precio_tabla_centavos=fila["precio_tabla_centavos"],
        estado=fila["estado"],
        plantilla_json=fila["plantilla_json"],
        tema_json=fila["tema_json"],
        creado_en=fila["creado_en"],
    )


def _a_parametros(evento: Evento) -> dict[str, object]:
    return {
        "organizacion_id": evento.organizacion_id,
        "nombre": evento.nombre,
        "fecha": evento.fecha,
        "hora": evento.hora,
        "lugar": evento.lugar,
        "precio_tabla_centavos": evento.precio_tabla_centavos,
        "estado": evento.estado,
        "plantilla_json": evento.plantilla_json,
        "tema_json": evento.tema_json,
        "creado_en": evento.creado_en or ahora_iso(),
    }


def crear(con: sqlite3.Connection, evento: Evento) -> Evento:
    """Inserta el evento. Devuelve la copia persistida (con `id`)."""
    parametros = _a_parametros(evento)
    columnas = ", ".join(_COLUMNAS)
    marcadores = ", ".join(f":{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        cursor = con.execute(f"INSERT INTO evento ({columnas}) VALUES ({marcadores})", parametros)
    return dataclasses.replace(evento, id=cursor.lastrowid, creado_en=parametros["creado_en"])


def obtener(con: sqlite3.Connection, evento_id: int) -> Evento | None:
    fila = con.execute("SELECT * FROM evento WHERE id = ?", (evento_id,)).fetchone()
    return _desde_fila(fila) if fila is not None else None


def listar_por_organizacion(
    con: sqlite3.Connection,
    organizacion_id: int,
    *,
    limite: int | None = None,
    desplazamiento: int = 0,
) -> list[Evento]:
    sql = (
        "SELECT * FROM evento WHERE organizacion_id = ? "
        "ORDER BY fecha DESC, estado = 'borrador' DESC, id DESC"
    )
    parametros: list[object] = [organizacion_id]
    if limite is not None:
        sql += " LIMIT ? OFFSET ?"
        parametros += [limite, desplazamiento]
    filas = con.execute(sql, parametros).fetchall()
    return [_desde_fila(f) for f in filas]


def listar_todos(
    con: sqlite3.Connection, *, limite: int | None = None, desplazamiento: int = 0
) -> list[Evento]:
    """Todos los eventos, de todas las organizaciones (pantalla de inicio, E18)."""
    sql = "SELECT * FROM evento ORDER BY fecha DESC, estado = 'borrador' DESC, id DESC"
    parametros: list[object] = []
    if limite is not None:
        sql += " LIMIT ? OFFSET ?"
        parametros += [limite, desplazamiento]
    filas = con.execute(sql, parametros).fetchall()
    return [_desde_fila(f) for f in filas]


def actualizar(con: sqlite3.Connection, evento: Evento) -> None:
    if evento.id is None:
        raise ValueError("No se puede actualizar un evento sin id")
    parametros = _a_parametros(evento)
    parametros["id"] = evento.id
    asignaciones = ", ".join(f"{c} = :{c}" for c in _COLUMNAS)
    with traducir_errores_sqlite():
        con.execute(f"UPDATE evento SET {asignaciones} WHERE id = :id", parametros)


def actualizar_estado(con: sqlite3.Connection, evento_id: int, estado: str) -> None:
    """Escribe el estado ya validado por el dominio. No valida la transición."""
    with traducir_errores_sqlite():
        con.execute("UPDATE evento SET estado = ? WHERE id = ?", (estado, evento_id))


def actualizar_plantilla(con: sqlite3.Connection, evento_id: int, plantilla_json: str) -> None:
    try:
        json.loads(plantilla_json)
    except (json.JSONDecodeError, TypeError) as error:
        raise ErrorValidacion(
            "error.integridad.check", campo="plantilla_json", detalle=str(error)
        ) from error
    with traducir_errores_sqlite():
        con.execute(
            "UPDATE evento SET plantilla_json = ? WHERE id = ?", (plantilla_json, evento_id)
        )


def actualizar_tema(con: sqlite3.Connection, evento_id: int, tema_json: str) -> None:
    try:
        json.loads(tema_json)
    except (json.JSONDecodeError, TypeError) as error:
        raise ErrorValidacion(
            "error.integridad.check", campo="tema_json", detalle=str(error)
        ) from error
    with traducir_errores_sqlite():
        con.execute("UPDATE evento SET tema_json = ? WHERE id = ?", (tema_json, evento_id))


def existe_nombre(
    con: sqlite3.Connection, organizacion_id: int, nombre: str, excluir_id: int | None = None
) -> bool:
    if excluir_id is None:
        fila = con.execute(
            "SELECT 1 FROM evento WHERE organizacion_id = ? AND nombre = ? COLLATE NOCASE",
            (organizacion_id, nombre),
        ).fetchone()
    else:
        fila = con.execute(
            "SELECT 1 FROM evento WHERE organizacion_id = ? AND nombre = ? COLLATE NOCASE "
            "AND id != ?",
            (organizacion_id, nombre, excluir_id),
        ).fetchone()
    return fila is not None
