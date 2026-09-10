from random import Random

import pytest

from bingo.dominio.bombo import Bombo, BomboVacio
from bingo.utilidades.errores import ErrorValidacion


def test_no_repite_en_75_extracciones() -> None:
    bombo = Bombo(Random(1))
    vistas: set[int] = set()
    for _ in range(75):
        numero = bombo.siguiente()
        assert numero not in vistas
        vistas.add(numero)
        bombo.confirmar(numero)
    assert len(vistas) == 75
    assert vistas == set(range(1, 76))


def test_se_agota_exactamente_en_75() -> None:
    bombo = Bombo(Random(1))
    for _ in range(75):
        bombo.confirmar(bombo.siguiente())
    assert bombo.agotado
    assert bombo.restantes == 0
    with pytest.raises(BomboVacio):
        bombo.siguiente()


def test_restantes_disminuye_de_uno_en_uno() -> None:
    bombo = Bombo(Random(1))
    assert bombo.restantes == 75
    bombo.confirmar(bombo.siguiente())
    assert bombo.restantes == 74


def test_reconstruccion_desde_lista_previa_deja_el_complemento() -> None:
    ya_extraidas = [5, 12, 40, 75]
    bombo = Bombo(Random(1), ya_extraidas=ya_extraidas)
    assert bombo.extraidas == ya_extraidas
    assert bombo.restantes == 75 - len(ya_extraidas)
    for _ in range(bombo.restantes):
        numero = bombo.siguiente()
        assert numero not in ya_extraidas
        bombo.confirmar(numero)
    assert bombo.agotado


def test_reconstruccion_rechaza_numero_fuera_de_rango() -> None:
    with pytest.raises(ErrorValidacion):
        Bombo(Random(1), ya_extraidas=[0])
    with pytest.raises(ErrorValidacion):
        Bombo(Random(1), ya_extraidas=[76])


def test_reconstruccion_rechaza_numero_repetido() -> None:
    with pytest.raises(ErrorValidacion):
        Bombo(Random(1), ya_extraidas=[10, 10])


def test_siguiente_sin_confirmar_no_muta_nada() -> None:
    """Hallazgo B1, crítico: si la transacción de la bola falla, el motor no
    llama a `confirmar()`. `siguiente()` debe poder consultarse repetidas
    veces sin que `restantes` se mueva, y sin cambiar de candidato."""
    bombo = Bombo(Random(1))
    primero = bombo.siguiente()
    segundo = bombo.siguiente()
    assert primero == segundo
    assert bombo.restantes == 75
    assert bombo.extraidas == []


def test_confirmar_numero_fuera_de_rango_falla() -> None:
    bombo = Bombo(Random(1))
    bombo.siguiente()
    with pytest.raises(ValueError):
        bombo.confirmar(999)


def test_confirmar_numero_ya_extraido_falla() -> None:
    bombo = Bombo(Random(1))
    numero = bombo.siguiente()
    bombo.confirmar(numero)
    with pytest.raises(ValueError):
        bombo.confirmar(numero)
