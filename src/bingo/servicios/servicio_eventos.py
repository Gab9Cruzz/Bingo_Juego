"""Casos de uso de `evento`. Aquí vive la validación que no le corresponde al
repositorio (regla de negocio) ni a la vista (persistencia, transacciones).
"""

from __future__ import annotations

import sqlite3

from bingo.dominio.estados import TRANSICIONES_EVENTO, puede_transicionar
from bingo.dominio.modelos import Evento
from bingo.persistencia import repo_auditoria, repo_evento
from bingo.persistencia.conexion import transaccion
from bingo.utilidades.errores import ErrorNoEncontrado, ErrorTransicionInvalida, ErrorValidacion


def crear_evento(con: sqlite3.Connection, evento: Evento) -> Evento:
    if not evento.nombre.strip():
        raise ErrorValidacion("eventos.error.nombre_vacio", campo="nombre")
    if evento.precio_tabla_centavos < 0:
        raise ErrorValidacion("eventos.error.precio_negativo", campo="precio_tabla_centavos")

    with transaccion(con):
        creado = repo_evento.crear(con, evento)
        repo_auditoria.registrar(con, creado.id, "evento.creado", detalle=creado.nombre)
    return creado


def cambiar_estado(con: sqlite3.Connection, evento_id: int, nuevo: str) -> None:
    """Valida la transición contra `dominio.estados` y solo entonces escribe.

    La tabla de transiciones vive en el dominio; este servicio la aplica; el
    repositorio se limita a escribir el estado ya validado.
    """
    actual = repo_evento.obtener(con, evento_id)
    if actual is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": evento_id})

    if not puede_transicionar(TRANSICIONES_EVENTO, actual.estado, nuevo):
        raise ErrorTransicionInvalida(
            "error.transicion_invalida", parametros={"actual": actual.estado, "nuevo": nuevo}
        )

    with transaccion(con):
        repo_evento.actualizar_estado(con, evento_id, nuevo)
        repo_auditoria.registrar(
            con, evento_id, "evento.cambio_estado", detalle=f"{actual.estado} -> {nuevo}"
        )
