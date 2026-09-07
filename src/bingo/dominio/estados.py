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
    "impreso": {"entregado", "anulado"},
    "entregado": {"vendido", "anulado"},
    "vendido": {"anulado"},
    "anulado": set(),
}


def puede_transicionar(transiciones: Mapping[str, set[str]], actual: str, nuevo: str) -> bool:
    return nuevo in transiciones.get(actual, set())
