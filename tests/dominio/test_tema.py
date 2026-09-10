import dataclasses

import pytest

from bingo.dominio.tema import ConfigBloque, TemaDashboard, validar
from bingo.utilidades.errores import ErrorValidacion


def test_por_defecto_es_valido() -> None:
    validar(TemaDashboard.por_defecto())  # no lanza


def test_roundtrip_a_json_y_desde_json() -> None:
    tema = TemaDashboard.por_defecto()
    tema = dataclasses.replace(tema, colores=dataclasses.replace(tema.colores, fondo="#112233"))
    nuevo_bombo = ConfigBloque(visible=False, pos_x=0.3, pos_y=0.4, escala=0.5)
    tema = dataclasses.replace(tema, bombo=nuevo_bombo)
    recuperado = TemaDashboard.desde_json(tema.a_json())
    assert recuperado.colores.fondo == "#112233"
    assert recuperado.bombo == ConfigBloque(visible=False, pos_x=0.3, pos_y=0.4, escala=0.5)


def test_json_vacio_o_none_da_valores_por_defecto() -> None:
    assert TemaDashboard.desde_json(None) == TemaDashboard.por_defecto()
    assert TemaDashboard.desde_json("") == TemaDashboard.por_defecto()


def test_json_corrupto_no_lanza_y_cae_a_defecto() -> None:
    assert TemaDashboard.desde_json("{esto no es json") == TemaDashboard.por_defecto()


def test_campos_ausentes_caen_al_valor_por_defecto() -> None:
    """Un tema_json de una versión anterior, sin `contador_bolas` ni `reloj`
    ni `banner_texto` (decisión D.2 del plan de la fase 4): no debe reventar,
    ni perder los demás bloques."""
    parcial = '{"colores": {"fondo": "#000000"}}'
    tema = TemaDashboard.desde_json(parcial)
    assert tema.colores.fondo == "#000000"
    assert tema.contador_bolas == ConfigBloque()
    assert tema.reloj == ConfigBloque()
    assert tema.banner_texto.visible is False
    assert tema.banner_texto.texto == ""


def test_banner_texto_conserva_su_forma_distinta() -> None:
    """E-A12: `banner_texto` no tiene `pos`/`escala`, a diferencia de los
    demás bloques."""
    tema = TemaDashboard.desde_json('{"banner_texto": {"visible": true, "texto": "Feliz Bingo"}}')
    assert tema.banner_texto.visible is True
    assert tema.banner_texto.texto == "Feliz Bingo"


def test_claves_desconocidas_se_ignoran() -> None:
    tema = TemaDashboard.desde_json('{"campo_futuro": {"x": 1}, "colores": {"fondo": "#abcdef"}}')
    assert tema.colores.fondo == "#abcdef"


def test_validar_rechaza_color_invalido() -> None:
    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(base, colores=dataclasses.replace(base.colores, fondo="no-es-color"))
    with pytest.raises(ErrorValidacion):
        validar(tema)


def test_validar_rechaza_posicion_fuera_de_rango() -> None:
    tema = dataclasses.replace(TemaDashboard.por_defecto(), bombo=ConfigBloque(pos_x=1.5))
    with pytest.raises(ErrorValidacion):
        validar(tema)


def test_validar_rechaza_escala_no_positiva() -> None:
    tema = dataclasses.replace(TemaDashboard.por_defecto(), bombo=ConfigBloque(escala=0))
    with pytest.raises(ErrorValidacion):
        validar(tema)


def test_validar_rechaza_ultimas_bolas_negativo() -> None:
    from bingo.dominio.tema import ConfigJuego

    tema = dataclasses.replace(
        TemaDashboard.por_defecto(), juego=ConfigJuego(mostrar_ultimas_bolas=-1)
    )
    with pytest.raises(ErrorValidacion):
        validar(tema)
