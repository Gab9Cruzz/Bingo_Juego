import dataclasses

import pytest

from bingo.dominio.modelos import Organizacion
from bingo.impresion.plantilla import (
    PlantillaCarton,
    restablecer_marca_desde_organizacion,
    validar,
)
from bingo.utilidades.errores import ErrorValidacion


def test_por_defecto_sin_organizacion() -> None:
    plantilla = PlantillaCarton.por_defecto()
    assert plantilla.hoja.tamano == "A4"
    assert plantilla.hoja.cartones_por_hoja == 4
    assert plantilla.marca.logo is None
    validar(plantilla)  # no lanza


def test_por_defecto_siembra_marca_desde_organizacion() -> None:
    org = Organizacion(
        nombre="Fundación X",
        logo_path="/tmp/logo.png",
        color_primario="#123456",
        color_secundario="#abcdef",
        contacto="WhatsApp 0999999999",
    )
    plantilla = PlantillaCarton.por_defecto(org)
    assert plantilla.marca.logo == "/tmp/logo.png"
    assert plantilla.marca.color_encabezado == "#123456"
    assert plantilla.marca.color_grilla == "#abcdef"
    assert plantilla.textos.contacto == "WhatsApp 0999999999"
    # No siembra título/subtítulo: son del evento, no de la organización.
    assert plantilla.marca.titulo == ""


def test_por_defecto_no_pisa_contacto_ya_escrito() -> None:
    org = Organizacion(nombre="X", contacto="contacto-org")
    textos = dataclasses.replace(PlantillaCarton().textos, contacto="ya-puesto")
    plantilla = PlantillaCarton(textos=textos)
    resultado = restablecer_marca_desde_organizacion(plantilla, org)
    assert resultado.textos.contacto == "ya-puesto"


def test_roundtrip_json() -> None:
    original = PlantillaCarton.por_defecto()
    original.marca.titulo = "Bingo Solidario"
    original.hoja.cartones_por_hoja = 6
    texto = original.a_json()
    reconstruida = PlantillaCarton.desde_json(texto)
    assert reconstruida == original


def test_desde_json_vacio_devuelve_plantilla_por_defecto() -> None:
    assert PlantillaCarton.desde_json(None) == PlantillaCarton()
    assert PlantillaCarton.desde_json("") == PlantillaCarton()


def test_desde_json_corrupto_no_lanza() -> None:
    assert PlantillaCarton.desde_json("{esto no es json}") == PlantillaCarton()


def test_desde_json_con_claves_desconocidas_las_ignora() -> None:
    texto = '{"hoja": {"tamano": "A5", "campo_del_futuro": 123}}'
    plantilla = PlantillaCarton.desde_json(texto)
    assert plantilla.hoja.tamano == "A5"


def test_desde_json_con_campos_ausentes_cae_al_defecto() -> None:
    texto = '{"hoja": {"tamano": "A5"}}'
    plantilla = PlantillaCarton.desde_json(texto)
    assert plantilla.hoja.tamano == "A5"
    assert plantilla.hoja.cartones_por_hoja == 4  # el resto de hoja.* al defecto
    assert plantilla.marca.color_encabezado == "#1a1a2e"  # otro bloque, sin tocar


@pytest.mark.parametrize(
    "mutacion",
    [
        lambda p: setattr(p.hoja, "tamano", "Legal"),
        lambda p: setattr(p.hoja, "orientacion", "diagonal"),
        lambda p: setattr(p.hoja, "cartones_por_hoja", 3),
        lambda p: setattr(p.hoja, "margen_mm", 0),
        lambda p: setattr(p.hoja, "margen_mm", -5),
        lambda p: setattr(p.marca, "color_encabezado", "no-es-color"),
        lambda p: setattr(p.marca, "color_grilla", "#zzzzzz"),
        lambda p: setattr(p.marca, "opacidad_fondo", 1.5),
        lambda p: setattr(p.marca, "opacidad_fondo", -0.1),
        lambda p: setattr(p.marca, "logo_pos", "centro-centro"),
        lambda p: setattr(p.marca, "logo_alto_mm", 0),
        lambda p: setattr(p.encabezado, "letras", ["B", "I", "N"]),
        lambda p: setattr(p.libre, "tipo", "emoji"),
        lambda p: setattr(p.numeros, "tamano_pt", 0),
        lambda p: setattr(p.identificacion, "pos", "centro"),
        lambda p: setattr(p.identificacion, "opacidad_marca_agua", 2.0),
    ],
)
def test_validar_rechaza_campos_fuera_de_rango(mutacion) -> None:
    plantilla = PlantillaCarton.por_defecto()
    mutacion(plantilla)
    with pytest.raises(ErrorValidacion):
        validar(plantilla)


def test_validar_campo_apunta_al_widget_correcto() -> None:
    plantilla = PlantillaCarton.por_defecto()
    plantilla.hoja.tamano = "Legal"
    with pytest.raises(ErrorValidacion) as excinfo:
        validar(plantilla)
    assert excinfo.value.campo == "hoja.tamano"
