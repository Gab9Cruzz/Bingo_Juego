"""Estado de una ronda en juego: qué cartones participan y qué han marcado
(contrato §5.2). Dominio puro: no importa nada del proyecto salvo
`dominio/carton.py`, `dominio/patron.py` y `utilidades/errores`, nunca
PySide6 ni sqlite3 (verificado por `tests/arquitectura/test_arquitectura.py`).

`es_ganador` y `faltan` se reexportan de `dominio/patron.py`: la evaluación
del patrón no cambia entre la fase 4 (edición) y la fase 5 (juego), así que
no se reescriben aquí.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from bingo.dominio.carton import BIT_LIBRE
from bingo.dominio.patron import es_ganador, faltan

__all__ = ["CartonEnJuego", "EstadoPartida", "es_ganador", "faltan"]


@dataclass(slots=True)
class CartonEnJuego:
    """Un cartón vendido y elegible, con su estado de marcado durante una
    ronda. `numeros_por_bit` es `dominio.carton.numeros_por_bit(matriz)`,
    calculado una sola vez al construirse (`servicio_sorteo.iniciar_ronda`):
    marcar una bola no vuelve a recorrer la matriz 5x5.

    `marcado` arranca con el bit del espacio libre (12) ya encendido — el
    espacio libre nunca lleva número y siempre cuenta como marcado (contrato
    §4.5). Si el patrón no usa ese bit (`usa_libre=False`), sobra y no
    estorba: `marcado & m == m` lo ignora igual (`patron.usa_libre_incoherente`
    ya impide guardar un patrón que dependa de él sin permitirlo).
    """

    carton_id: int
    codigo: str
    numeros_por_bit: dict[int, int]
    marcado: int = field(init=False)

    def __post_init__(self) -> None:
        self.marcado = 1 << BIT_LIBRE

    def marcar(self, numero: int) -> bool:
        """Enciende el bit de `numero` si el cartón lo contiene. Devuelve si
        lo tocó — es lo que `EstadoPartida.aplicar` usa para saber a quién
        recalcular."""
        bit = self.numeros_por_bit.get(numero)
        if bit is None:
            return False
        self.marcado |= 1 << bit
        return True


class EstadoPartida:
    """Índice inverso `{numero: [CartonEnJuego]}` y conjunto vivo de "a una
    bola", mantenido incrementalmente (hallazgos E-8 y C8, plan de la fase
    5): un barrido completo por bola contradice el contrato §5.2 literal
    ("evaluación tras cada bola únicamente sobre los cartones que se
    marcaron en esa jugada"). Un cartón solo puede *entrar* a "a una bola"
    si la bola que se acaba de aplicar lo tocó — nunca se reevalúan los
    demás.

    Una instancia vive una ronda completa (un patrón, un conjunto de
    cartones elegibles): por eso `aplicar()` no recibe las máscaras del
    patrón como argumento propio en cada llamada más que para calcular
    "a una bola", que sí depende de ellas.
    """

    __slots__ = ("_cartones", "_indice", "_a_una_bola")

    def __init__(self, cartones: Sequence[CartonEnJuego]) -> None:
        self._cartones: list[CartonEnJuego] = list(cartones)
        self._indice: dict[int, list[CartonEnJuego]] = {}
        for carton in self._cartones:
            for numero in carton.numeros_por_bit:
                self._indice.setdefault(numero, []).append(carton)
        self._a_una_bola: dict[int, CartonEnJuego] = {}

    @property
    def cartones(self) -> list[CartonEnJuego]:
        return list(self._cartones)

    @property
    def a_una_bola(self) -> list[CartonEnJuego]:
        """El conjunto vivo, tal como quedó tras la última llamada a
        `aplicar()`. No es un cálculo bajo demanda: mantenerlo así es
        justamente lo que evita el barrido completo."""
        return list(self._a_una_bola.values())

    def aplicar(self, numero: int, mascaras: Sequence[int]) -> list[CartonEnJuego]:
        """Marca `numero` en los cartones que lo contienen y actualiza "a una
        bola" para esos mismos cartones, y solo esos (índice inverso: los que
        no tienen `numero` ni se tocan ni se reevalúan).

        Un cartón cuyo `faltan()` no baja de 1 tras marcar permanece en el
        conjunto; uno que llega a 0 sale de "a una bola" porque ya ganó —
        `servicio_sorteo` decide qué hacer con eso filtrando el resultado de
        esta llamada con `es_ganador`, no con otra pasada aparte.
        """
        tocados = self._indice.get(numero, [])
        for carton in tocados:
            carton.marcar(numero)
            faltantes = faltan(carton.marcado, mascaras)
            if faltantes == 0:
                self._a_una_bola.pop(carton.carton_id, None)
            elif faltantes == 1:
                self._a_una_bola[carton.carton_id] = carton
        return list(tocados)

    def ganadores(self, mascaras: Sequence[int]) -> list[CartonEnJuego]:
        """Barrido completo deliberado: a diferencia de `aplicar()`, esto no
        se llama por cada bola durante el juego en vivo (ahí gana la
        detección incremental sobre `aplicar()`). Sirve para verificar el
        estado completo tras reconstruir una ronda al reanudar (decisión
        D13) o para cualquier consulta puntual que no dependa de qué bola
        salió último."""
        return [c for c in self._cartones if es_ganador(c.marcado, mascaras)]
