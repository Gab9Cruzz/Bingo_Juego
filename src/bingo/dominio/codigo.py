"""Normalización de códigos de cartón para la importación de compradores
(fase 4, ANEXO A hallazgo F5 / decisión R3 del plan de la fase).

Un Excel real trae códigos con variaciones de formato que no son errores del
operador: espacios de más, minúsculas, o solo la parte numérica ("1" en vez
de "A-2026-000001"). Reportar "código inexistente" para las 980 filas de un
archivo por lo demás correcto es peor que no normalizar nada. Dominio puro:
sin PySide6 ni sqlite3, sin acceso a base — recibe los códigos reales del
evento ya cargados por el llamador.

No se adivina cuando hay ambigüedad real (hallazgo M7): si el sufijo
numérico de un código calza con más de un cartón (dos lotes con prefijos
distintos, por ejemplo), se reporta como ambiguo en vez de elegir uno.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

_PATRON_SUFIJO_NUMERICO = re.compile(r"(\d+)$")


@dataclass(slots=True, frozen=True)
class ResultadoNormalizacion:
    """`codigos` son los códigos reales del evento que calzan con el texto
    de entrada, ya reconciliados: 0 = no reconocible, 1 = candidato único,
    2+ = ambiguo (no se elige)."""

    codigos: tuple[str, ...]

    @property
    def es_unico(self) -> bool:
        return len(self.codigos) == 1

    @property
    def es_ambiguo(self) -> bool:
        return len(self.codigos) > 1

    @property
    def codigo_unico(self) -> str | None:
        return self.codigos[0] if self.es_unico else None


def normalizar_texto(valor: str) -> str:
    """Trim + colapso de espacios internos + mayúsculas. Sin conocimiento de
    prefijos: es el primer paso, tanto para la coincidencia exacta como para
    detectar si lo que queda es puramente numérico."""
    return " ".join(valor.strip().split()).upper()


def _sufijo_numerico(codigo: str) -> int | None:
    coincidencia = _PATRON_SUFIJO_NUMERICO.search(codigo)
    return int(coincidencia.group(1)) if coincidencia else None


def normalizar(codigo_bruto: str, codigos_existentes: Sequence[str]) -> ResultadoNormalizacion:
    """Reconcilia `codigo_bruto` (tal como viene de la fila del Excel) contra
    `codigos_existentes` (los códigos reales de cartón del evento).

    Orden de intento:
    1. Coincidencia exacta tras normalizar texto (case-insensitive, espacios
       colapsados) — cubre la inmensa mayoría de los casos reales.
    2. Si lo que queda es puramente numérico, coincidencia por sufijo
       numérico del código completo ("1" -> "...-000001"). Si más de un
       código del evento comparte ese sufijo, se reporta ambiguo.
    """
    texto = normalizar_texto(codigo_bruto)
    if not texto:
        return ResultadoNormalizacion(())

    por_texto = {normalizar_texto(c): c for c in codigos_existentes}
    if texto in por_texto:
        return ResultadoNormalizacion((por_texto[texto],))

    if texto.isdigit():
        numero = int(texto)
        candidatos = [c for c in codigos_existentes if _sufijo_numerico(c) == numero]
        # dict.fromkeys conserva el orden y quita duplicados si el llamador
        # pasó códigos repetidos por error.
        return ResultadoNormalizacion(tuple(dict.fromkeys(candidatos)))

    return ResultadoNormalizacion(())
