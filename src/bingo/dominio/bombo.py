"""Bombo de 75 bolas, sin reposición (contrato §5.1).

Dominio puro: no importa nada del proyecto salvo `utilidades/errores`, nunca
PySide6 ni sqlite3 (verificado por `tests/arquitectura/test_arquitectura.py`).

El generador aleatorio (`rng`) se recibe siempre como parámetro, nunca se
instancia aquí: en producción es `secrets.SystemRandom()`, en pruebas
`random.Random(semilla)` (mismo convenio que `dominio/carton.py`).

`siguiente()` / `confirmar()` en dos pasos, no un `extraer()` que muta
(hallazgo B1, crítico, plan de la fase 5): la extracción se
persiste antes de confirmarse (§6.2, "el commit ocurre antes de que la
interfaz muestre la bola"). Si la transacción de esa bola falla —base
bloqueada, disco lleno, integridad—, un `extraer()` mutante ya habría
eliminado el número del bombo en memoria, y el rollback dejaría dos estados
distintos según si el operador reinició la aplicación o no: el número
desaparecería del juego en silencio. Con el bombo separado en dos pasos, un
intento fallido no muta nada — `siguiente()` puede volver a elegir (el mismo
candidato, cacheado, o uno nuevo si se descarta explícitamente) sin que
`restantes` se haya movido.
"""

from __future__ import annotations

from random import Random

from bingo.utilidades.errores import ErrorBingo, ErrorValidacion

NUMERO_MINIMO = 1
NUMERO_MAXIMO = 75


class BomboVacio(ErrorBingo):
    """Las 75 bolas ya salieron. Red de seguridad de programación, no un
    camino de usuario (hallazgo C7): agotar el bombo sin ganador es un final
    de ronda legítimo. La interfaz consulta `Bombo.agotado` antes de ofrecer
    "Extraer" y nunca debería llegar a disparar esta excepción en uso normal.
    """


class Bombo:
    """`ya_extraidas` reconstruye un bombo a partir de lo que ya salió (D13,
    reanudación): validado igual que si se hubiera ido llenando bola a bola,
    nunca se muta durante la reconstrucción.
    """

    __slots__ = ("_rng", "_extraidas", "_restantes", "_candidato")

    def __init__(self, rng: Random, ya_extraidas: list[int] | None = None) -> None:
        self._rng = rng
        self._extraidas: list[int] = []
        self._restantes: list[int] = list(range(NUMERO_MINIMO, NUMERO_MAXIMO + 1))
        self._candidato: int | None = None

        vistas: set[int] = set()
        for numero in ya_extraidas or []:
            if not (NUMERO_MINIMO <= numero <= NUMERO_MAXIMO):
                raise ErrorValidacion(
                    "bombo.error.numero_fuera_de_rango",
                    detalle=f"{numero} fuera de {NUMERO_MINIMO}-{NUMERO_MAXIMO}",
                    parametros={"numero": numero},
                )
            if numero in vistas:
                raise ErrorValidacion(
                    "bombo.error.numero_repetido",
                    detalle=f"{numero} extraído más de una vez",
                    parametros={"numero": numero},
                )
            vistas.add(numero)
            self._extraidas.append(numero)
            self._restantes.remove(numero)

    @property
    def extraidas(self) -> list[int]:
        return list(self._extraidas)

    @property
    def restantes(self) -> int:
        return len(self._restantes)

    @property
    def agotado(self) -> bool:
        return not self._restantes

    def siguiente(self) -> int:
        """Elige la próxima bola sin sacarla del bombo. Llamadas repetidas
        sin `confirmar()` de por medio devuelven el mismo candidato — el
        motor de sorteo puede reintentar una transacción fallida sin que el
        número cambie bajo los pies de la interfaz que ya lo esté mostrando.
        """
        if self._candidato is not None:
            return self._candidato
        if self.agotado:
            raise BomboVacio("sorteo.error.bombo_vacio", detalle="Las 75 bolas ya se extrajeron")
        self._candidato = self._rng.choice(self._restantes)
        return self._candidato

    def confirmar(self, numero: int) -> None:
        """Saca `numero` del bombo. Se llama **después** de que la
        transacción de la bola hizo commit (D2), nunca antes."""
        if numero not in self._restantes:
            raise ValueError(
                f"{numero} no está disponible en el bombo (¿ya se confirmó, o nunca "
                "fue elegido por siguiente()?)"
            )
        self._restantes.remove(numero)
        self._extraidas.append(numero)
        self._candidato = None
