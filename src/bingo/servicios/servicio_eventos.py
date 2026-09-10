"""Casos de uso de `evento`. Aquí vive la validación que no le corresponde al
repositorio (regla de negocio) ni a la vista (persistencia, transacciones).
"""

from __future__ import annotations

import sqlite3

from bingo.dominio import firma as dominio_firma
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


def marcar_preparado(con: sqlite3.Connection, evento_id: int) -> None:
    """`borrador -> preparado` con guarda (ANEXO A, hallazgo R9 del plan de
    la fase 4): sin rondas con patrón y premio, "preparado" no significa
    nada. Import perezoso de `servicio_rondas` para no crear un ciclo de
    módulo (`servicio_rondas` no importa `servicio_eventos`).
    """
    from bingo.servicios import servicio_rondas

    pendientes = [p for p in servicio_rondas.validar_evento_listo(con, evento_id) if p.bloqueante]
    if pendientes:
        raise ErrorValidacion(
            "eventos.error.no_listo_para_preparar", parametros={"cantidad": len(pendientes)}
        )
    cambiar_estado(con, evento_id, "preparado")


def asegurar_clave_evento(con: sqlite3.Connection, evento_id: int) -> str:
    """Devuelve `evento.clave_evento`, generándola y persistiéndola la primera
    vez que se pide (fase 3, dominio/firma.py). Idempotente: si ya existe, la
    devuelve tal cual, sin caso especial para quien la llama.

    Es el único punto que decide *cuándo* nace la clave —
    `repo_evento.actualizar_clave` solo escribe. `servicio_impresion` la llama
    antes de renderizar el primer PDF de un evento.
    """
    actual = repo_evento.obtener(con, evento_id)
    if actual is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": evento_id})
    if actual.clave_evento:
        return actual.clave_evento

    clave = dominio_firma.generar_clave_evento()
    with transaccion(con):
        repo_evento.actualizar_clave(con, evento_id, clave)
        repo_auditoria.registrar(con, evento_id, "evento.clave_generada")
    return clave


def finalizar_evento(con: sqlite3.Connection, evento_id: int) -> None:
    """`en_curso -> finalizado` (contrato §5.9, tarea 4.13): un evento no
    se termina con una ronda a medias — exige que **todas** las rondas
    estén `cerrada`. La vista, tras esto, ofrece generar el reporte del
    evento y el respaldo (tareas 4.11/4.12); este servicio solo valida y
    hace la transición."""
    from bingo.persistencia import repo_ronda

    actual = repo_evento.obtener(con, evento_id)
    if actual is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": evento_id})
    sin_cerrar = [r for r in repo_ronda.listar_por_evento(con, evento_id) if r.estado != "cerrada"]
    if sin_cerrar:
        raise ErrorValidacion(
            "eventos.error.rondas_sin_cerrar", parametros={"cantidad": len(sin_cerrar)}
        )
    cambiar_estado(con, evento_id, "finalizado")
