"""Casos de uso de validación y registro de ganadores (contrato §5.6).

`validar_reclamo` es una consulta pura: no escribe nada, ni siquiera cuando
el cartón no cumple. Solo `confirmar` y `resolver_empate` escriben, y las
dos van siempre a `repo_auditoria` — la decisión sobre quién se lleva un
premio es exactamente lo que una disputa posterior necesita poder
reconstruir.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from bingo.dominio.carton import BIT_LIBRE, carton_desde_orden_canonico, numeros_por_bit
from bingo.dominio.firma import verificar_qr
from bingo.dominio.modelos import Carton, Comprador
from bingo.dominio.partida import es_ganador
from bingo.persistencia import (
    repo_auditoria,
    repo_carton,
    repo_comprador,
    repo_evento,
    repo_extraccion,
    repo_ganador,
    repo_patron,
    repo_ronda,
)
from bingo.persistencia.conexion import transaccion
from bingo.utilidades.errores import ErrorNoEncontrado, ErrorValidacion
from bingo.utilidades.fechas import ahora_iso

DECISIONES_VALIDAS = ("unico", "reparto", "desempate_externo", "no_reclamado", "rechazado")
_DECISIONES_CON_PREMIO = frozenset({"unico", "reparto", "desempate_externo"})


@dataclass(slots=True, frozen=True)
class Reclamo:
    """Resultado de validar un código o QR contra el estado actual de la
    ronda. `carton`/`comprador` son `None` cuando el motivo de rechazo es
    "no existe" — no hay nada más que mostrar."""

    carton: Carton | None
    comprador: Comprador | None
    marcado: int
    cumple: bool
    motivo_rechazo: str | None


def _reclamo_rechazado(motivo: str, *, carton: Carton | None = None) -> Reclamo:
    return Reclamo(carton=carton, comprador=None, marcado=0, cumple=False, motivo_rechazo=motivo)


def validar_reclamo(con: sqlite3.Connection, ronda_id: int, texto: str) -> Reclamo:
    """Acepta un código tecleado o el contenido de un QR firmado (hallazgo
    V4): `dominio/firma.py::verificar_qr` existe desde la fase 3 para esto.

    **La regla de desempate es por el separador `|`, no por el resultado
    (hallazgo S1, alto).** `verificar_qr` devuelve `None` tanto para "no
    tiene formato de QR" como para "la firma es inválida" — si el texto
    **contiene** `|`, una firma inválida es un rechazo duro con motivo
    propio, nunca una degradación a código tecleado (eso dejaría
    `"A-0142|00000000"` pasar usando la parte anterior al `|`, sin que el
    HMAC validara nada). Solo si el texto no contiene `|` se trata como
    código tecleado.
    """
    ronda = repo_ronda.obtener(con, ronda_id)
    if ronda is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda_id})

    if "|" in texto:
        evento = repo_evento.obtener(con, ronda.evento_id)
        codigo_validado = (
            verificar_qr(evento.clave_evento, texto)
            if evento is not None and evento.clave_evento
            else None
        )
        if codigo_validado is None:
            return _reclamo_rechazado("ganador.error.qr_invalido")
        codigo = codigo_validado
    else:
        codigo = texto

    carton = repo_carton.obtener_por_codigo(con, ronda.evento_id, codigo)
    if carton is None:
        return _reclamo_rechazado("ganador.error.codigo_inexistente")
    if carton.estado != "vendido":
        return _reclamo_rechazado("ganador.error.no_vendido", carton=carton)
    comprador = repo_comprador.obtener_por_carton(con, carton.id)
    if comprador is None:
        return _reclamo_rechazado("ganador.error.sin_comprador", carton=carton)

    patron = repo_patron.obtener(con, ronda.patron_id)
    if patron is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ronda.patron_id})

    numeros_por_bit_carton = numeros_por_bit(carton_desde_orden_canonico(carton.numeros))
    marcado = 1 << BIT_LIBRE
    for numero in repo_extraccion.numeros_por_ronda(con, ronda_id):
        bit = numeros_por_bit_carton.get(numero)
        if bit is not None:
            marcado |= 1 << bit

    cumple = es_ganador(marcado, patron.mascaras)
    motivo = None if cumple else "ganador.error.patron_no_cumplido"
    return Reclamo(
        carton=carton, comprador=comprador, marcado=marcado, cumple=cumple, motivo_rechazo=motivo
    )


def confirmar(
    con: sqlite3.Connection, ganador_id: int, decision: str, nota: str | None = None
) -> None:
    """`unico | reparto | desempate_externo | no_reclamado | rechazado`.
    Escribe `confirmado=True` siempre (la decisión, cualquiera que sea, ya
    está tomada) y `reparte_premio` solo para las tres primeras."""
    if decision not in DECISIONES_VALIDAS:
        raise ErrorValidacion(
            "ganador.error.decision_invalida", campo="decision", parametros={"valor": decision}
        )
    ganador = repo_ganador.obtener(con, ganador_id)
    if ganador is None:
        raise ErrorNoEncontrado("error.no_encontrado", parametros={"id": ganador_id})
    ronda = repo_ronda.obtener(con, ganador.ronda_id)

    momento = ahora_iso()
    with transaccion(con):
        repo_ganador.actualizar_decision(
            con,
            ganador_id,
            confirmado=True,
            confirmado_en=momento,
            decision=decision,
            reparte_premio=decision in _DECISIONES_CON_PREMIO,
            nota=nota,
        )
        repo_auditoria.registrar(
            con,
            ronda.evento_id if ronda else None,
            "ganador.confirmado",
            detalle=f"ganador_id={ganador_id} decision={decision}",
        )


def resolver_empate(
    con: sqlite3.Connection,
    ronda_id: int,
    *,
    ids_reparto: list[int] | None = None,
    id_unico: int | None = None,
    permitir_bolas_distintas: bool = False,
) -> None:
    """Resuelve el conjunto de detectados de una ronda de una vez: todos
    quedan con `decision` explícita, ninguno en limbo. Exactamente uno de
    `ids_reparto` (reparto entre varios) o `id_unico` (uno solo, los demás
    quedan `rechazado`).

    **Empate := misma `extraccion.orden` (hallazgo V2).** Por la decisión D8
    todas las filas de `ganador` de una ronda comparten `bola_numero` — el
    motor solo registra las detecciones de la primera bola que produjo
    ganador — así que en el flujo normal esta comprobación nunca dispara.
    Se deja explícita de todos modos como defensa: si alguna vez apareciera
    una fila de otra bola (una migración vieja, un dato importado a mano),
    repartir entre bolas distintas exige `permitir_bolas_distintas=True`.
    """
    detectados = [g for g in repo_ganador.listar_por_ronda(con, ronda_id) if g.anulado_en is None]
    if not detectados:
        raise ErrorValidacion("ganador.error.sin_detectados", parametros={"ronda_id": ronda_id})

    bolas = {g.bola_numero for g in detectados}
    if len(bolas) > 1 and not permitir_bolas_distintas:
        raise ErrorValidacion(
            "ganador.error.empate_bolas_distintas", parametros={"bolas": sorted(bolas)}
        )

    if (ids_reparto is None) == (id_unico is None):
        raise ErrorValidacion("ganador.error.resolucion_ambigua")

    ganadores_ids = {g.id for g in detectados}
    momento = ahora_iso()
    ronda = repo_ronda.obtener(con, ronda_id)
    evento_id = ronda.evento_id if ronda else None

    with transaccion(con):
        if ids_reparto is not None:
            if not set(ids_reparto) <= ganadores_ids:
                raise ErrorValidacion("ganador.error.id_no_detectado")
            for ganador_id in ganadores_ids:
                decision = "reparto" if ganador_id in ids_reparto else "rechazado"
                repo_ganador.actualizar_decision(
                    con,
                    ganador_id,
                    confirmado=True,
                    confirmado_en=momento,
                    decision=decision,
                    reparte_premio=decision == "reparto",
                )
        else:
            if id_unico not in ganadores_ids:
                raise ErrorValidacion("ganador.error.id_no_detectado")
            for ganador_id in ganadores_ids:
                decision = "unico" if ganador_id == id_unico else "rechazado"
                repo_ganador.actualizar_decision(
                    con,
                    ganador_id,
                    confirmado=True,
                    confirmado_en=momento,
                    decision=decision,
                    reparte_premio=decision == "unico",
                )
        repo_auditoria.registrar(
            con,
            evento_id,
            "ganador.empate_resuelto",
            detalle=f"ronda_id={ronda_id} ids_reparto={ids_reparto} id_unico={id_unico}",
        )
