"""Evaluación de patrones de bingo sobre el entero de 25 bits del cartón
(contrato de la fase 4, §4.5; doc técnico §4.6; decisión D10 del plan de la
fase 4). Dominio puro: sin PySide6 ni sqlite3, sin i18n (verificado por
`tests/arquitectura/test_arquitectura.py`) — el nombre visible de cada patrón
del sistema vive en `es.json`/`en.json` bajo su `clave_i18n`, nunca aquí.

Un patrón puede tener varias máscaras ("variantes"): gana quien complete
cualquiera de ellas (decisión D1, doc técnico §16.1) — "cualquier línea
horizontal" son cinco máscaras, una por fila.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from bingo.dominio.carton import BIT_LIBRE, indice_bit

CARTON_LLENO = (1 << 25) - 1


def mascara(celdas: Iterable[tuple[int, int]]) -> int:
    """Construye el entero de 25 bits a partir de coordenadas `(fila, columna)`."""
    valor = 0
    for fila, columna in celdas:
        valor |= 1 << indice_bit(fila, columna)
    return valor


def celdas_desde_mascara(m: int) -> list[tuple[int, int]]:
    """Inverso de `mascara`: la lista de `(fila, columna)` encendidas, en
    orden de bit ascendente. Lo usa el editor de patrones para pintar la
    rejilla 5x5 de una máscara ya guardada."""
    return [(bit // 5, bit % 5) for bit in range(25) if (m >> bit) & 1]


def es_ganador(marcado: int, mascaras: Sequence[int]) -> bool:
    """`True` si `marcado` cumple cualquiera de las variantes del patrón.

    `any(marcado & m == m for m in mascaras)`: una máscara se cumple cuando
    todos sus bits están encendidos en `marcado` (los bits que `marcado` trae
    de más no importan). Una lista vacía nunca gana — es el estado de un
    patrón sin guardar, nunca el de uno persistido (el repositorio impide
    escribir `mascaras=[]`).
    """
    return any(marcado & m == m for m in mascaras)


def faltan(marcado: int, mascaras: Sequence[int]) -> int:
    """Cuántas celdas le faltan a `marcado` para la variante más cercana.

    Mínimo sobre todas las variantes del patrón; si `mascaras` está vacía no
    hay nada que cumplir y se devuelve el máximo posible (25).
    """
    if not mascaras:
        return 25
    return min(bin(m & ~marcado).count("1") for m in mascaras)


@dataclass(slots=True, frozen=True)
class PatronSistema:
    """Un patrón precargado por `servicio_patrones.asegurar_patrones_sistema`.

    `nombre_es` es el respaldo en español que se guarda en `patron.nombre`
    (decisión M9 del plan de la fase 4): la vista siempre intenta primero
    `t(clave_i18n)` y solo cae a `nombre` si la clave no resuelve. Guardar un
    texto en español aquí no es una cadena visible saltándose `t()` — es el
    dato de semilla de una fila de base, análogo a `TEXTO_INFERIOR_DEFECTO`
    en `impresion/plantilla.py`.
    """

    clave_i18n: str
    nombre_es: str
    mascaras: tuple[int, ...]
    usa_libre: bool
    descripcion_i18n: str | None = None


def _fila(f: int) -> int:
    return mascara((f, c) for c in range(5))


def _columna(c: int) -> int:
    return mascara((f, c) for f in range(5))


_DIAGONAL_PRINCIPAL = mascara((i, i) for i in range(5))
_DIAGONAL_INVERSA = mascara((i, 4 - i) for i in range(5))
_FILA_CENTRAL = _fila(2)
_COLUMNA_CENTRAL = _columna(2)


def _bloque_2x2(fila: int, columna: int) -> int:
    return mascara((fila + df, columna + dc) for df in (0, 1) for dc in (0, 1))


PATRONES_SISTEMA: tuple[PatronSistema, ...] = (
    PatronSistema(
        "patron.sistema.linea_horizontal",
        "Línea horizontal (cualquiera)",
        tuple(_fila(f) for f in range(5)),
        usa_libre=True,
    ),
    PatronSistema(
        "patron.sistema.linea_vertical",
        "Línea vertical (cualquiera)",
        tuple(_columna(c) for c in range(5)),
        usa_libre=True,
    ),
    PatronSistema(
        "patron.sistema.diagonal",
        "Diagonal (cualquiera)",
        (_DIAGONAL_PRINCIPAL, _DIAGONAL_INVERSA),
        usa_libre=True,
    ),
    PatronSistema(
        "patron.sistema.cuatro_esquinas",
        "Cuatro esquinas",
        (mascara([(0, 0), (0, 4), (4, 0), (4, 4)]),),
        usa_libre=False,
    ),
    PatronSistema(
        "patron.sistema.equis",
        "Equis (X)",
        (_DIAGONAL_PRINCIPAL | _DIAGONAL_INVERSA,),
        usa_libre=True,
    ),
    PatronSistema(
        "patron.sistema.cruz",
        "Cruz",
        (_FILA_CENTRAL | _COLUMNA_CENTRAL,),
        usa_libre=True,
    ),
    PatronSistema(
        "patron.sistema.marco",
        "Marco (borde completo)",
        (_fila(0) | _fila(4) | _columna(0) | _columna(4),),
        usa_libre=False,
    ),
    PatronSistema(
        "patron.sistema.diamante",
        "Diamante",
        (mascara([(0, 2), (1, 1), (1, 3), (2, 0), (2, 4), (3, 1), (3, 3), (4, 2)]),),
        usa_libre=False,
    ),
    PatronSistema(
        "patron.sistema.sello_postal",
        "Sello postal (cualquier esquina)",
        (_bloque_2x2(0, 0), _bloque_2x2(0, 3), _bloque_2x2(3, 0), _bloque_2x2(3, 3)),
        usa_libre=False,
    ),
    PatronSistema(
        "patron.sistema.letra_t",
        "Letra T",
        (_fila(0) | _columna(2),),
        usa_libre=True,
    ),
    PatronSistema(
        "patron.sistema.letra_l",
        "Letra L",
        (_columna(0) | _fila(4),),
        usa_libre=False,
    ),
    PatronSistema(
        "patron.sistema.letra_h",
        "Letra H",
        (_columna(0) | _columna(4) | _FILA_CENTRAL,),
        usa_libre=True,
    ),
    PatronSistema(
        "patron.sistema.letra_e",
        "Letra E",
        (_columna(0) | _fila(0) | _FILA_CENTRAL | _fila(4),),
        usa_libre=True,
    ),
    PatronSistema(
        "patron.sistema.escalera",
        "Escalera",
        (mascara([(0, 0), (1, 0), (1, 1), (2, 1), (2, 2), (3, 2), (3, 3), (4, 3), (4, 4)]),),
        usa_libre=True,
    ),
    PatronSistema(
        "patron.sistema.carton_lleno",
        "Cartón lleno",
        (CARTON_LLENO,),
        usa_libre=True,
    ),
)


def usa_libre_incoherente(mascaras: Sequence[int], usa_libre: bool) -> bool:
    """`True` si alguna máscara exige el bit del espacio libre (12) sin que
    `usa_libre` lo permita — esa combinación es imposible de cumplir: el
    espacio libre nunca lleva un número (contrato §4.5, doc técnico §4.6).
    """
    if usa_libre:
        return False
    return any((m >> BIT_LIBRE) & 1 for m in mascaras)
