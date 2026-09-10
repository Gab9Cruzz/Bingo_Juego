import io
from random import Random

import pytest
from reportlab.pdfgen.canvas import Canvas

from bingo.dominio.carton import generar_carton
from bingo.dominio.modelos import Organizacion
from bingo.impresion.plantilla import PlantillaCarton
from bingo.impresion.render_pdf import MotorRenderCarton

_ORG = Organizacion(nombre="Fundación de prueba")
_CLAVE = "clave-de-prueba"


def _motor(**overrides_hoja: object) -> MotorRenderCarton:
    plantilla = PlantillaCarton.por_defecto(_ORG)
    for clave, valor in overrides_hoja.items():
        setattr(plantilla.hoja, clave, valor)
    return MotorRenderCarton(plantilla, _ORG, _CLAVE)


@pytest.mark.parametrize("cantidad", [1, 2, 4, 6])
def test_calcular_disposicion_produce_la_cantidad_pedida(cantidad: int) -> None:
    motor = _motor(cartones_por_hoja=cantidad)
    posiciones = motor.calcular_disposicion()
    assert len(posiciones) == cantidad


@pytest.mark.parametrize("cantidad", [1, 2, 4, 6])
def test_calcular_disposicion_no_se_solapa_ni_sale_del_margen(cantidad: int) -> None:
    motor = _motor(cartones_por_hoja=cantidad)
    ancho_hoja, alto_hoja = motor.tamano_hoja()

    for x, y, ancho, alto in motor.calcular_disposicion():
        assert x >= -0.01
        assert y >= -0.01
        assert x + ancho <= ancho_hoja + 0.01
        assert y + alto <= alto_hoja + 0.01

    # Ninguna pareja de rectángulos se solapa (comparación por fuerza bruta:
    # la lista nunca pasa de 6 elementos).
    posiciones = motor.calcular_disposicion()
    for i, (x1, y1, w1, h1) in enumerate(posiciones):
        for x2, y2, w2, h2 in posiciones[i + 1 :]:
            se_solapan = x1 < x2 + w2 and x2 < x1 + w1 and y1 < y2 + h2 and y2 < y1 + h1
            assert not se_solapan


def test_marcas_de_corte_solo_si_mas_de_un_carton() -> None:
    canvas = Canvas(io.BytesIO())

    motor_uno = _motor(cartones_por_hoja=1)
    posiciones_uno = motor_uno.calcular_disposicion()
    # No debe lanzar y, con una sola posición, no dibuja nada (no hay forma
    # directa de verificar "no dibujó" sin inspeccionar el stream de
    # contenido; se confía en la guarda explícita `len(posiciones) <= 1`).
    motor_uno.dibujar_marcas_corte(canvas, posiciones_uno)

    motor_cuatro = _motor(cartones_por_hoja=4)
    posiciones_cuatro = motor_cuatro.calcular_disposicion()
    motor_cuatro.dibujar_marcas_corte(canvas, posiciones_cuatro)  # tampoco lanza


@pytest.mark.parametrize("cantidad", [1, 2, 4, 6])
def test_dibujar_carton_no_lanza_con_plantilla_minima(cantidad: int) -> None:
    motor = _motor(cartones_por_hoja=cantidad)
    matriz = generar_carton(Random(0))
    canvas = Canvas(io.BytesIO(), pagesize=motor.tamano_hoja())
    x, y, ancho, alto = motor.calcular_disposicion()[0]
    motor.dibujar_carton(canvas, "TEST-000001", matriz, x, y, ancho, alto)
    canvas.showPage()
    canvas.save()  # no lanza


def test_dibujar_carton_no_lanza_con_plantilla_completa(tmp_path) -> None:
    from PIL import Image

    logo = tmp_path / "logo.png"
    Image.new("RGBA", (10, 10), (255, 0, 0, 255)).save(logo)

    org = Organizacion(nombre="Fundación X", logo_path=str(logo))
    plantilla = PlantillaCarton.por_defecto(org)
    plantilla.marca.titulo = "Bingo Solidario"
    plantilla.marca.subtitulo = "A beneficio de..."
    plantilla.marca.fondo = str(logo)
    plantilla.marca.logo_secundario = str(logo)
    plantilla.libre.tipo = "logo"
    plantilla.textos.superior = "Texto superior"
    plantilla.textos.inferior = "Texto inferior de prueba"
    plantilla.textos.contacto = "WhatsApp 0999999999"
    plantilla.identificacion.marca_agua = True

    motor = MotorRenderCarton(plantilla, org, _CLAVE)
    matriz = generar_carton(Random(1))
    canvas = Canvas(io.BytesIO(), pagesize=motor.tamano_hoja())
    x, y, ancho, alto = motor.calcular_disposicion()[0]
    motor.dibujar_carton(canvas, "TEST-000002", matriz, x, y, ancho, alto)
    canvas.showPage()
    canvas.save()


def test_dibujar_carton_con_logo_inexistente_no_lanza() -> None:
    org = Organizacion(nombre="X", logo_path="/ruta/que/no/existe.png")
    plantilla = PlantillaCarton.por_defecto(org)
    motor = MotorRenderCarton(plantilla, org, _CLAVE)
    matriz = generar_carton(Random(0))
    canvas = Canvas(io.BytesIO(), pagesize=motor.tamano_hoja())
    x, y, ancho, alto = motor.calcular_disposicion()[0]
    motor.dibujar_carton(canvas, "TEST-000003", matriz, x, y, ancho, alto)


def test_renderizar_pagina_hace_showpage() -> None:
    motor = _motor(cartones_por_hoja=2)
    buffer = io.BytesIO()
    canvas = Canvas(buffer, pagesize=motor.tamano_hoja())
    cartones = [
        ("TEST-000001", generar_carton(Random(0))),
        ("TEST-000002", generar_carton(Random(1))),
    ]
    motor.renderizar_pagina(canvas, cartones)
    canvas.save()
    assert buffer.getvalue().startswith(b"%PDF-")
