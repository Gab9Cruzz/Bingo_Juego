from __future__ import annotations

from random import Random

import pytest

from bingo.dominio.carton import (
    RANGOS,
    carton_desde_orden_canonico,
    firma,
    generar_carton,
    indice_bit,
    numeros_por_bit,
    orden_canonico,
)


def test_indice_bit() -> None:
    assert indice_bit(0, 0) == 0
    assert indice_bit(2, 2) == 12
    assert indice_bit(4, 4) == 24


def test_columna_sin_repetidos() -> None:
    carton = generar_carton(Random(1))
    for columna in range(5):
        numeros = [carton[fila][columna] for fila in range(5) if carton[fila][columna] is not None]
        assert len(numeros) == len(set(numeros))


def test_cada_columna_respeta_su_rango() -> None:
    carton = generar_carton(Random(2))
    for columna in range(5):
        inicio, fin = RANGOS[columna]
        for fila in range(5):
            valor = carton[fila][columna]
            if valor is not None:
                assert inicio <= valor <= fin


def test_columna_n_tiene_4_numeros_y_centro_libre() -> None:
    carton = generar_carton(Random(3))
    columna_n = [carton[fila][2] for fila in range(5)]
    assert columna_n[2] is None
    assert len([v for v in columna_n if v is not None]) == 4


@pytest.mark.parametrize("columna", [0, 1, 3, 4])
def test_columnas_sin_libre_tienen_5_numeros(columna: int) -> None:
    carton = generar_carton(Random(4))
    valores = [carton[fila][columna] for fila in range(5)]
    assert all(v is not None for v in valores)
    assert len(valores) == 5


def test_orden_canonico_y_firma_deterministas_con_semilla() -> None:
    a = generar_carton(Random(42))
    b = generar_carton(Random(42))
    assert orden_canonico(a) == orden_canonico(b)
    assert firma(a) == firma(b)


def test_orden_canonico_tiene_24_numeros() -> None:
    carton = generar_carton(Random(5))
    assert len(orden_canonico(carton).split(",")) == 24


def test_firma_es_sha256_hexadecimal() -> None:
    carton = generar_carton(Random(6))
    resultado = firma(carton)
    assert len(resultado) == 64
    int(resultado, 16)  # no lanza si es hexadecimal válido


def test_numeros_por_bit() -> None:
    carton = generar_carton(Random(7))
    mapa = numeros_por_bit(carton)
    assert len(mapa) == 24
    for fila in range(5):
        for columna in range(5):
            valor = carton[fila][columna]
            if valor is not None:
                assert mapa[valor] == indice_bit(fila, columna)


def test_carton_desde_orden_canonico_round_trip() -> None:
    original = generar_carton(Random(8))
    reconstruido = carton_desde_orden_canonico(orden_canonico(original))
    assert reconstruido == original


def test_carton_desde_orden_canonico_centro_es_libre() -> None:
    original = generar_carton(Random(9))
    reconstruido = carton_desde_orden_canonico(orden_canonico(original))
    assert reconstruido[2][2] is None


def test_carton_desde_orden_canonico_cadena_invalida() -> None:
    with pytest.raises(ValueError, match="24"):
        carton_desde_orden_canonico("1,2,3")


@pytest.mark.lento
def test_50000_cartones_sin_firmas_repetidas() -> None:
    rng = Random(123)
    firmas = {firma(generar_carton(rng)) for _ in range(50_000)}
    assert len(firmas) == 50_000


def test_reproducibilidad_de_un_lote_con_la_misma_semilla() -> None:
    rng_a = Random(999)
    rng_b = Random(999)
    lote_a = [orden_canonico(generar_carton(rng_a)) for _ in range(20)]
    lote_b = [orden_canonico(generar_carton(rng_b)) for _ in range(20)]
    assert lote_a == lote_b
