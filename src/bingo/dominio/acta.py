"""Comprobante de una ronda jugada (contrato §5.9, decisión D7).

`carga_canonica()` es una serialización determinista de lo que de verdad
importa de una ronda ya cerrada — **nunca** los bytes del PDF: un PDF de
ReportLab lleva la fecha de creación en sus metadatos, así que dos actas
del mismo sorteo darían hashes distintos, y el hash impreso no podría estar
dentro de su propio PDF. Regenerar el acta del mismo sorteo tiene que dar
el mismo hash — es lo que lo hace un comprobante.

**La carga empieza por "acta/v1" (hallazgo E-5).** Si el formato cambia en
una v1.1, todas las actas ya emitidas dejarían de verificar contra
documentos legítimos. El verificador (tarea 4.20,
`servicios/servicio_actas.py::verificar_acta`) siempre construye la carga
con la función de *este* módulo — la versión importa el día en que haya una
`v2` y haga falta decidir con cuál serializar una ronda vieja; hoy solo
existe v1.

Dominio puro: solo `hashlib` y tipos estándar, sin PySide6 ni sqlite3.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass

_VERSION_CARGA = "acta/v1"


@dataclass(frozen=True, slots=True)
class GanadorActa:
    """Código de cartón, no nombre (decisión S5-7/DU-18): el acta puede
    circular fuera del control del operador."""

    codigo: str
    decision: str | None


def carga_canonica(
    *,
    organizacion_nombre: str,
    evento_nombre: str,
    ronda_nombre: str,
    patron_nombre: str,
    premio_texto: str,
    numeros: Sequence[int],
    ganadores: Sequence[GanadorActa],
) -> str:
    """Una línea por campo, orden fijo, sin depender de qué locale del
    sistema formatee lo que sea — todo lo que entra aquí ya es texto plano.
    `ganadores` se ordena por código antes de serializar: dos llamadas con
    la misma ronda pero las filas leídas en otro orden deben dar la misma
    carga."""
    ganadores_ordenados = sorted(ganadores, key=lambda g: g.codigo)
    partes = [
        _VERSION_CARGA,
        organizacion_nombre,
        evento_nombre,
        ronda_nombre,
        patron_nombre,
        premio_texto,
        ",".join(str(n) for n in numeros),
        ";".join(f"{g.codigo}:{g.decision or ''}" for g in ganadores_ordenados),
    ]
    return "\n".join(partes)


def hash_acta(carga: str) -> str:
    return hashlib.sha256(carga.encode("utf-8")).hexdigest()
