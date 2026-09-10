from random import Random

import pytest

import bingo.dominio.partida as partida_mod
from bingo.dominio.carton import BIT_LIBRE, generar_carton, numeros_por_bit
from bingo.dominio.partida import CartonEnJuego, EstadoPartida
from bingo.dominio.patron import es_ganador, mascara


def _carton_en_juego(carton_id: int, rng: Random) -> CartonEnJuego:
    matriz = generar_carton(rng)
    return CartonEnJuego(
        carton_id=carton_id, codigo=f"A-{carton_id}", numeros_por_bit=numeros_por_bit(matriz)
    )


def test_espacio_libre_arranca_marcado() -> None:
    carton = _carton_en_juego(1, Random(1))
    assert carton.marcado == 1 << BIT_LIBRE


def test_marcar_numero_ausente_no_toca_el_bit() -> None:
    carton = _carton_en_juego(1, Random(1))
    antes = carton.marcado
    numero_ausente = next(n for n in range(1, 76) if n not in carton.numeros_por_bit)
    assert carton.marcar(numero_ausente) is False
    assert carton.marcado == antes


def test_marcar_numero_presente_enciende_el_bit() -> None:
    carton = _carton_en_juego(1, Random(1))
    numero, bit = next(iter(carton.numeros_por_bit.items()))
    assert carton.marcar(numero) is True
    assert carton.marcado & (1 << bit)


def test_indice_inverso_toca_solo_los_que_contienen_la_bola() -> None:
    cartones = [_carton_en_juego(i, Random(i)) for i in range(30)]
    estado = EstadoPartida(cartones)
    numero = 7
    esperados = {c.carton_id for c in cartones if numero in c.numeros_por_bit}

    tocados = estado.aplicar(numero, mascaras=[])

    assert {c.carton_id for c in tocados} == esperados
    for carton in cartones:
        if carton.carton_id in esperados:
            assert carton.marcado & (1 << carton.numeros_por_bit[numero])
        else:
            assert carton.marcado == 1 << BIT_LIBRE  # sin tocar


def _bit_a_numero(carton: CartonEnJuego) -> dict[int, int]:
    return {bit: numero for numero, bit in carton.numeros_por_bit.items()}


def test_ganador_positivo_sin_espacio_libre() -> None:
    carton = _carton_en_juego(1, Random(2))
    bit_a_numero = _bit_a_numero(carton)
    m = mascara([(0, 0), (0, 4), (4, 0), (4, 4)])  # cuatro esquinas, usa_libre=False
    for fila, columna in ((0, 0), (0, 4), (4, 0), (4, 4)):
        carton.marcar(bit_a_numero[fila * 5 + columna])
    assert es_ganador(carton.marcado, [m])


def test_ganador_negativo_sin_espacio_libre() -> None:
    carton = _carton_en_juego(1, Random(2))
    bit_a_numero = _bit_a_numero(carton)
    m = mascara([(0, 0), (0, 4), (4, 0), (4, 4)])
    for fila, columna in ((0, 0), (0, 4), (4, 0)):  # falta una esquina
        carton.marcar(bit_a_numero[fila * 5 + columna])
    assert not es_ganador(carton.marcado, [m])


def test_ganador_positivo_con_espacio_libre() -> None:
    """Fila central: sus 5 celdas incluyen el espacio libre (fila 2,
    columna 2). Marcar solo las 4 celdas reales ya gana, porque el bit del
    espacio libre nace encendido."""
    carton = _carton_en_juego(1, Random(3))
    bit_a_numero = _bit_a_numero(carton)
    m = mascara((2, c) for c in range(5))
    for columna in range(5):
        if columna == 2:
            continue  # espacio libre: no hay número que marcar
        carton.marcar(bit_a_numero[2 * 5 + columna])
    assert es_ganador(carton.marcado, [m])


def test_ganador_negativo_con_espacio_libre() -> None:
    carton = _carton_en_juego(1, Random(3))
    bit_a_numero = _bit_a_numero(carton)
    m = mascara((2, c) for c in range(5))
    for columna in (0, 1, 3):  # falta la columna 4 de la fila central
        carton.marcar(bit_a_numero[2 * 5 + columna])
    assert not es_ganador(carton.marcado, [m])


def test_a_una_bola_multi_mascara_entra_y_sale_al_ganar() -> None:
    """Patrón "cualquier línea horizontal": 5 máscaras, una por fila. El
    cartón entra a "a una bola" cuando le falta una celda para la fila más
    cercana, y sale (porque ya ganó) al completarla."""
    carton = _carton_en_juego(1, Random(4))
    bit_a_numero = _bit_a_numero(carton)
    mascaras = [mascara((fila, c) for c in range(5)) for fila in range(5)]
    estado = EstadoPartida([carton])

    fila_objetivo = 1  # no toca el espacio libre (está en la fila 2)
    numeros_fila = [bit_a_numero[fila_objetivo * 5 + c] for c in range(5)]

    for numero in numeros_fila[:4]:
        estado.aplicar(numero, mascaras)
    assert carton in estado.a_una_bola

    estado.aplicar(numeros_fila[4], mascaras)
    assert carton not in estado.a_una_bola
    assert carton in estado.ganadores(mascaras)


def test_a_una_bola_no_entra_si_faltan_dos_o_mas() -> None:
    carton = _carton_en_juego(1, Random(5))
    bit_a_numero = _bit_a_numero(carton)
    mascaras = [mascara((0, c) for c in range(5))]
    estado = EstadoPartida([carton])

    numero = bit_a_numero[0 * 5 + 0]
    estado.aplicar(numero, mascaras)
    assert carton not in estado.a_una_bola


def test_ganadores_barrido_completo_no_requiere_aplicar_previo() -> None:
    ganador = _carton_en_juego(1, Random(6))
    perdedor = _carton_en_juego(2, Random(7))
    bit_a_numero = _bit_a_numero(ganador)
    m = mascara([(0, 0), (0, 4), (4, 0), (4, 4)])
    for fila, columna in ((0, 0), (0, 4), (4, 0), (4, 4)):
        ganador.marcar(bit_a_numero[fila * 5 + columna])

    estado = EstadoPartida([ganador, perdedor])
    assert estado.ganadores([m]) == [ganador]


@pytest.mark.lento
def test_aplicar_solo_evalua_los_tocados_no_barre_todos(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hallazgos E-8 y C8: la prueba asserta el número de evaluaciones, no
    solo el tiempo. Con 2.000 cartones, `faltan()` debe llamarse una vez por
    cartón tocado por la bola, nunca 2.000 veces."""
    cartones = [_carton_en_juego(i, Random(i)) for i in range(2000)]
    estado = EstadoPartida(cartones)
    mascaras = [mascara((0, c) for c in range(5))]

    llamadas: list[None] = []
    original = partida_mod.faltan

    def contador(marcado: int, mascaras_: list[int]) -> int:
        llamadas.append(None)
        return original(marcado, mascaras_)

    monkeypatch.setattr(partida_mod, "faltan", contador)

    tocados = estado.aplicar(7, mascaras)

    assert 0 < len(tocados) < len(cartones)
    assert len(llamadas) == len(tocados)
