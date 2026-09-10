import pytest
from PySide6.QtGui import QPainter, QPixmap

from bingo.dominio.patron import mascara
from bingo.dominio.tema import TemaDashboard
from bingo.ui.transmision.bloques import ContextoTransmision, pintar_fotograma
from bingo.ui.transmision.estado_transmision import EstadoTransmision


def _pintar(estado: EstadoTransmision, **overrides) -> None:
    lienzo = QPixmap(400, 225)
    pintor = QPainter(lienzo)
    try:
        ctx = ContextoTransmision(
            tema=TemaDashboard.por_defecto(),
            estado=estado,
            idioma="es",
            numero_actual=42,
            numeros_extraidos=frozenset({1, 2, 42}),
            patron_mascara=mascara([(0, 0)]),
            **overrides,
        )
        pintar_fotograma(pintor, ctx)
    finally:
        pintor.end()


@pytest.mark.parametrize("estado", list(EstadoTransmision))
def test_pintar_fotograma_no_lanza_en_ningun_estado(qapp, estado: EstadoTransmision) -> None:
    _pintar(estado)


def test_hay_carton_ganador_no_recibe_codigo_ni_nombre_en_el_contexto_de_pintado(qapp) -> None:
    """No es una prueba de píxeles (imposible de mantener): el pintor de
    este estado nunca recibe `codigo_ganador`/`nombre_ganador` como
    argumento — están en `ContextoTransmision`, pero
    `pintar_overlay_hay_carton_ganador` no los lee. Se comprueba leyendo el
    código fuente de la función, no adivinando a partir de píxeles."""
    import inspect

    from bingo.ui.transmision.bloques import pintar_overlay_hay_carton_ganador

    codigo_fuente = inspect.getsource(pintar_overlay_hay_carton_ganador)
    assert "codigo_ganador" not in codigo_fuente
    assert "nombre_ganador" not in codigo_fuente


def test_ganador_confirmado_es_el_unico_pintor_que_usa_codigo_y_nombre(qapp) -> None:
    import inspect

    from bingo.ui.transmision import bloques

    for nombre, funcion in vars(bloques).items():
        if not nombre.startswith("pintar_overlay_") or not inspect.isfunction(funcion):
            continue
        fuente = inspect.getsource(funcion)
        usa_datos_personales = "codigo_ganador" in fuente or "nombre_ganador" in fuente
        if usa_datos_personales:
            assert nombre == "pintar_overlay_ganador_confirmado", (
                f"{nombre} no debería tener acceso a datos del ganador"
            )
