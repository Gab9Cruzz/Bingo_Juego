"""Generación y representación del cartón de 75 bolas (documento técnico §4.1-4.2).

Dominio puro: no importa nada del proyecto salvo `utilidades/errores`, nunca
PySide6 ni sqlite3 (verificado por `tests/arquitectura/test_arquitectura.py`).

Cuadrícula 5x5, columnas B-I-N-G-O de izquierda a derecha con sus rangos fijos.
`None` marca el espacio libre, siempre en el centro (fila 2, columna 2). El
generador aleatorio (`rng`) se recibe siempre como parámetro, nunca se
instancia aquí: en producción es `secrets.SystemRandom()`, en pruebas
`random.Random(semilla)` para resultados reproducibles (mismo convenio que
`dominio/bombo.py` usará en la fase 5).
"""

from __future__ import annotations

import hashlib
from random import Random

RANGOS: dict[int, tuple[int, int]] = {
    0: (1, 15),  # B
    1: (16, 30),  # I
    2: (31, 45),  # N (4 números + espacio libre)
    3: (46, 60),  # G
    4: (61, 75),  # O
}
BIT_LIBRE = 12
_COLUMNA_LIBRE = 2
_FILA_LIBRE = 2

MatrizCarton = list[list[int | None]]


def indice_bit(fila: int, columna: int) -> int:
    """Posición de una celda en el entero de 25 bits usado en la partida (fase 5)."""
    return fila * 5 + columna


def generar_carton(rng: Random) -> MatrizCarton:
    """Genera un cartón: extracción sin reemplazo por columna, libre al centro.

    Devuelve una matriz 5x5 (`list[list[int | None]]`), indexada `[fila][columna]`.
    """
    columnas: list[list[int | None]] = []
    for columna in range(5):
        inicio, fin = RANGOS[columna]
        disponibles = list(range(inicio, fin + 1))
        cantidad = 4 if columna == _COLUMNA_LIBRE else 5
        seleccion: list[int | None] = []
        for _ in range(cantidad):
            indice = rng.randrange(len(disponibles))
            seleccion.append(disponibles.pop(indice))
        if columna == _COLUMNA_LIBRE:
            seleccion.insert(_FILA_LIBRE, None)
        columnas.append(seleccion)
    return [[columnas[columna][fila] for columna in range(5)] for fila in range(5)]


def orden_canonico(carton: MatrizCarton) -> str:
    """Serializa los 24 números (sin el espacio libre) en orden de columna,
    de arriba a abajo, separados por comas. Es lo que se persiste en
    `carton.numeros` y lo que se firma para garantizar unicidad.
    """
    numeros: list[int] = []
    for columna in range(5):
        for fila in range(5):
            valor = carton[fila][columna]
            if valor is not None:
                numeros.append(valor)
    return ",".join(str(n) for n in numeros)


def firma(carton: MatrizCarton) -> str:
    """SHA-256 del orden canónico. Es lo que el índice único de la base
    (`UNIQUE(evento_id, firma)`) usa para garantizar que no hay dos cartones
    iguales dentro de un mismo evento.
    """
    return hashlib.sha256(orden_canonico(carton).encode("utf-8")).hexdigest()


def numeros_por_bit(carton: MatrizCarton) -> dict[int, int]:
    """`{numero: bit}` — usado por `CartonEnJuego` en la fase 5 para marcar
    rápido qué bit enciende una bola extraída, sin recorrer la matriz.
    """
    resultado: dict[int, int] = {}
    for fila in range(5):
        for columna in range(5):
            valor = carton[fila][columna]
            if valor is not None:
                resultado[valor] = indice_bit(fila, columna)
    return resultado


def carton_desde_orden_canonico(cadena: str) -> MatrizCarton:
    """Inverso de `orden_canonico`: reconstruye la matriz 5x5 desde los 24
    números persistidos en `carton.numeros`. Necesaria para el visor
    (`ui/widgets/cuadricula_carton.py`): la base solo guarda la cadena, nunca
    la matriz, y no hay otra forma de volver a dibujarla.
    """
    numeros = [int(n) for n in cadena.split(",")] if cadena else []
    if len(numeros) != 24:
        raise ValueError(
            f"Se esperaban 24 números en el orden canónico, se recibieron {len(numeros)}"
        )

    columnas: list[list[int | None]] = []
    cursor = 0
    for columna in range(5):
        cantidad = 4 if columna == _COLUMNA_LIBRE else 5
        valores = numeros[cursor : cursor + cantidad]
        cursor += cantidad
        celdas: list[int | None] = list(valores)
        if columna == _COLUMNA_LIBRE:
            celdas.insert(_FILA_LIBRE, None)
        columnas.append(celdas)
    return [[columnas[columna][fila] for columna in range(5)] for fila in range(5)]
