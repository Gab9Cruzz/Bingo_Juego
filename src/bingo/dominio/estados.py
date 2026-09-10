"""Máquinas de estado, genéricas. `dominio/` es Python puro: sin PySide6 ni sqlite3.

`puede_transicionar` recibe la tabla de transiciones como argumento, en vez de
tener una tabla fija por función: así la fase 2 solo añade
`TRANSICIONES_CARTON` y la fase 5 `TRANSICIONES_RONDA`, sin renombrar esta
función ni sus pruebas.
"""

from __future__ import annotations

from collections.abc import Mapping

TRANSICIONES_EVENTO: Mapping[str, set[str]] = {
    "borrador": {"preparado"},
    "preparado": {"en_curso"},
    "en_curso": {"finalizado"},
    "finalizado": set(),
}

TRANSICIONES_CARTON: Mapping[str, set[str]] = {
    "generado": {"impreso", "anulado"},
    # impreso -> vendido: la organización vende cartones que nunca pasaron
    # por "entregado" (talonarios repartidos y vendidos en la puerta). El
    # paso "entregado" es un control de inventario opcional, no obligatorio
    # (fase 4, decisión D2, docs/Fase_4/Plan_Implementacion_Fase4.md).
    "impreso": {"entregado", "vendido", "anulado"},
    "entregado": {"vendido", "anulado"},
    # vendido -> impreso: camino de anular_venta (fase 4, hallazgo C2). El
    # comprador se equivocó o se arrepintió; el cartón físico sigue siendo
    # válido y vuelve a su estado anterior, que `anular_venta` recupera de
    # `comprador.estado_carton_previo` (nunca se asume "entregado" a ciegas).
    # vendido -> entregado también es válido si el estado previo era ese.
    "vendido": {"impreso", "entregado", "anulado"},
    "anulado": set(),
}

TRANSICIONES_RONDA: Mapping[str, set[str]] = {
    "pendiente": {"en_curso"},
    "en_curso": {"pausada", "cerrada"},
    "pausada": {"en_curso", "cerrada"},
    # cerrada -> en_curso (hallazgo V5, fase 5): cerrar una ronda por error
    # en directo (botón mal pulsado, Ctrl+Enter en el panel equivocado)
    # tiene que tener deshacer. La reapertura exige confirmación escrita y
    # se registra en auditoría (sorteo.ronda_reabierta); si la ronda ya
    # tenía acta generada, además invalida el hash (servicio_actas, hallazgo
    # E-16/C6). Sin esta transición, la promesa del alcance §6.6 de retomar
    # un bingo otro día desde la ronda pendiente sería falsa.
    "cerrada": {"en_curso"},
}


def puede_transicionar(transiciones: Mapping[str, set[str]], actual: str, nuevo: str) -> bool:
    return nuevo in transiciones.get(actual, set())
