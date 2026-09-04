from decimal import Decimal

from bingo.dominio.dinero import a_centavos, formatear


def test_a_centavos_casos_que_rompen_coma_flotante() -> None:
    assert a_centavos("0.1") == 10
    assert a_centavos("0.29") == 29
    assert a_centavos("19.99") == 1999
    assert a_centavos(Decimal("19.99")) == 1999


def test_a_centavos_redondeo() -> None:
    assert a_centavos("1.005") == 101  # ROUND_HALF_UP


def test_formatear_es() -> None:
    assert formatear(1999, "es") == "$19,99"


def test_formatear_en() -> None:
    assert formatear(1999, "en") == "$19.99"


def test_ida_y_vuelta() -> None:
    assert a_centavos("5.00") == 500
    assert formatear(500, "en") == "$5.00"
