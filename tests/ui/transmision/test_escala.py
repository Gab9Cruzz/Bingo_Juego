from bingo.ui.transmision.escala import calcular_escala


def test_lienzo_exacto_da_factor_uno() -> None:
    escala = calcular_escala(1920, 1080)
    assert escala.factor == 1.0
    assert escala.desplazamiento_x == 0.0
    assert escala.desplazamiento_y == 0.0


def test_ventana_mas_ancha_deja_barras_laterales() -> None:
    """21:9 (más ancho que 16:9 a igual alto): barras a los lados, nunca
    estira el contenido de forma desigual."""
    escala = calcular_escala(2560, 1080)
    assert escala.factor == 1.0
    assert escala.desplazamiento_x > 0
    assert escala.desplazamiento_y == 0.0


def test_ventana_mas_alta_deja_barras_arriba_y_abajo() -> None:
    escala = calcular_escala(1920, 1440)
    assert escala.factor == 1.0
    assert escala.desplazamiento_y > 0
    assert escala.desplazamiento_x == 0.0


def test_escala_hacia_abajo_reduce_el_factor() -> None:
    escala = calcular_escala(960, 540)
    assert escala.factor == 0.5


def test_dimensiones_invalidas_no_lanza() -> None:
    escala = calcular_escala(0, 0)
    assert escala.factor == 1.0
