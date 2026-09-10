from bingo.dominio.carton import BIT_LIBRE, indice_bit
from bingo.dominio.patron import (
    CARTON_LLENO,
    PATRONES_SISTEMA,
    celdas_desde_mascara,
    es_ganador,
    faltan,
    mascara,
    usa_libre_incoherente,
)


def test_carton_lleno_es_25_bits() -> None:
    assert CARTON_LLENO == 2**25 - 1


def test_mascara_y_celdas_desde_mascara_son_inversas() -> None:
    celdas = [(0, 0), (2, 2), (4, 4)]
    m = mascara(celdas)
    assert sorted(celdas_desde_mascara(m)) == sorted(celdas)


def test_mascara_vacia_no_gana_nada() -> None:
    assert es_ganador(CARTON_LLENO, []) is False


def test_es_ganador_con_una_sola_mascara() -> None:
    m = mascara([(0, 0), (0, 1)])
    assert es_ganador(mascara([(0, 0), (0, 1), (0, 2)]), [m]) is True
    assert es_ganador(mascara([(0, 0)]), [m]) is False


def test_es_ganador_con_variantes_cualquiera_gana() -> None:
    """El caso que el contrato §4.9 pide explícitamente: un cartón que
    completa la línea horizontal 3 (índice 2, fila central) gana el patrón
    "cualquier línea horizontal" y no gana "línea horizontal superior"."""
    fila_2 = mascara((2, c) for c in range(5))
    fila_0 = mascara((0, c) for c in range(5))
    cualquier_horizontal = [mascara((f, c) for c in range(5)) for f in range(5)]

    marcado = fila_2  # completó exactamente la fila central, nada más
    assert es_ganador(marcado, cualquier_horizontal) is True
    assert es_ganador(marcado, [fila_0]) is False


def test_faltan_con_una_mascara() -> None:
    m = mascara([(0, 0), (0, 1), (0, 2)])
    assert faltan(mascara([(0, 0)]), [m]) == 2
    assert faltan(m, [m]) == 0


def test_faltan_es_el_minimo_sobre_las_variantes() -> None:
    fila_0 = mascara((0, c) for c in range(5))
    fila_1 = mascara((1, c) for c in range(5))
    marcado = mascara([(0, 0), (0, 1), (0, 2), (0, 3)])  # falta 1 para fila_0
    assert faltan(marcado, [fila_0, fila_1]) == 1


def test_faltan_sin_mascaras_devuelve_25() -> None:
    assert faltan(0, []) == 25


def test_usa_libre_incoherente_detecta_bit_libre_sin_permiso() -> None:
    con_libre = mascara((2, c) for c in range(5))  # fila central: incluye (2,2)
    assert usa_libre_incoherente([con_libre], usa_libre=False) is True
    assert usa_libre_incoherente([con_libre], usa_libre=True) is False


def test_usa_libre_incoherente_sin_bit_libre_siempre_ok() -> None:
    sin_libre = mascara([(0, 0), (0, 1)])
    assert usa_libre_incoherente([sin_libre], usa_libre=False) is False


def test_patrones_sistema_no_estan_vacios_y_tienen_clave_unica() -> None:
    assert len(PATRONES_SISTEMA) >= 15
    claves = [p.clave_i18n for p in PATRONES_SISTEMA]
    assert len(claves) == len(set(claves)), "clave_i18n repetida entre patrones del sistema"
    for spec in PATRONES_SISTEMA:
        assert spec.mascaras, f"{spec.clave_i18n} no tiene ninguna máscara"
        for m in spec.mascaras:
            assert 1 <= m <= CARTON_LLENO
        assert usa_libre_incoherente(spec.mascaras, spec.usa_libre) is False, (
            f"{spec.clave_i18n}: usa_libre={spec.usa_libre} pero alguna máscara exige el libre"
        )


def test_patron_cuatro_esquinas_bit_por_bit() -> None:
    spec = next(p for p in PATRONES_SISTEMA if p.clave_i18n == "patron.sistema.cuatro_esquinas")
    (m,) = spec.mascaras
    assert sorted(celdas_desde_mascara(m)) == [(0, 0), (0, 4), (4, 0), (4, 4)]


def test_patron_marco_bit_por_bit() -> None:
    spec = next(p for p in PATRONES_SISTEMA if p.clave_i18n == "patron.sistema.marco")
    (m,) = spec.mascaras
    esperado = {(f, c) for f in range(5) for c in range(5) if f in (0, 4) or c in (0, 4)}
    assert set(celdas_desde_mascara(m)) == esperado


def test_patron_linea_horizontal_tiene_cinco_variantes_una_por_fila() -> None:
    spec = next(p for p in PATRONES_SISTEMA if p.clave_i18n == "patron.sistema.linea_horizontal")
    assert len(spec.mascaras) == 5
    for fila, m in enumerate(spec.mascaras):
        assert sorted(celdas_desde_mascara(m)) == [(fila, c) for c in range(5)]


def test_patron_linea_vertical_tiene_cinco_variantes_una_por_columna() -> None:
    spec = next(p for p in PATRONES_SISTEMA if p.clave_i18n == "patron.sistema.linea_vertical")
    assert len(spec.mascaras) == 5
    for columna, m in enumerate(spec.mascaras):
        assert sorted(celdas_desde_mascara(m)) == [(f, columna) for f in range(5)]


def test_patron_diagonal_tiene_dos_variantes() -> None:
    spec = next(p for p in PATRONES_SISTEMA if p.clave_i18n == "patron.sistema.diagonal")
    assert len(spec.mascaras) == 2
    esperado_principal = [(i, i) for i in range(5)]
    esperado_inversa = [(i, 4 - i) for i in range(5)]
    encontrados = [sorted(celdas_desde_mascara(m)) for m in spec.mascaras]
    assert sorted(esperado_principal) in encontrados
    assert sorted(esperado_inversa) in encontrados


def test_patron_carton_lleno_es_todas_las_celdas() -> None:
    spec = next(p for p in PATRONES_SISTEMA if p.clave_i18n == "patron.sistema.carton_lleno")
    (m,) = spec.mascaras
    assert m == CARTON_LLENO
    assert len(celdas_desde_mascara(m)) == 25


def test_bit_libre_coincide_con_fila_2_columna_2() -> None:
    assert indice_bit(2, 2) == BIT_LIBRE
