import inspect

import pytest

from bingo.dominio.modelos import Organizacion
from bingo.ui.tema import (
    DEFECTO_PRIMARIO,
    aplicar_tema_operador,
    contraste,
    paleta_organizacion,
)


def test_paleta_con_colores_validos() -> None:
    org = Organizacion(nombre="X", color_primario="#123456", color_texto="#ffffff")
    paleta = paleta_organizacion(org)
    assert paleta.color_primario == "#123456"


def test_paleta_cae_al_defecto_ante_basura() -> None:
    org = Organizacion(nombre="X", color_primario="no-es-un-color", color_texto="#ffffff")
    paleta = paleta_organizacion(org)
    assert paleta.color_primario == DEFECTO_PRIMARIO


def test_contraste_blanco_negro_maximo() -> None:
    assert contraste("#ffffff", "#000000") == pytest.approx(21.0, rel=1e-6)


def test_contraste_paleta_documento_tecnico_no_pasa_aa() -> None:
    """Base fáctica de la enmienda E15 y del desafío DU-1."""
    ratio = contraste("#ffffff", "#e94560")
    assert ratio < 4.5


def test_paleta_organizacion_marca_contraste_ok() -> None:
    org_ok = Organizacion(nombre="X", color_primario="#000000", color_texto="#ffffff")
    org_mal = Organizacion(nombre="X", color_primario="#e94560", color_texto="#ffffff")
    assert paleta_organizacion(org_ok).contraste_ok
    assert not paleta_organizacion(org_mal).contraste_ok


def test_aplicar_tema_operador_no_acepta_organizacion() -> None:
    firma = inspect.signature(aplicar_tema_operador)
    assert list(firma.parameters) == ["app"]


def test_aplicar_tema_operador_no_lanza(qapp) -> None:
    aplicar_tema_operador(qapp)
