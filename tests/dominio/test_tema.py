import dataclasses

import pytest

from bingo.dominio.tema import (
    ConfigBloque,
    TemaDashboard,
    _contador_bolas_por_defecto,
    _reloj_por_defecto,
    validar,
)
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
    # Decisión DU-4: cada bloque lleva una posición por defecto propia, no
    # el genérico ConfigBloque() en (0, 0) — así un evento nuevo no arranca
    # con siete bloques superpuestos en la esquina.
    assert tema.contador_bolas == _contador_bolas_por_defecto()
    assert tema.reloj == _reloj_por_defecto()
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


def test_por_defecto_no_tiene_solapes() -> None:
    """Decisión DU-4: aplicar el plan tal como estaba dejaba siete bloques
    superpuestos en el origen. La composición por defecto no debe solapar
    ningún par de bloques visibles."""
    from bingo.dominio.tema import detectar_solapes

    assert detectar_solapes(TemaDashboard.por_defecto()) == []


def test_detectar_solapes_encuentra_dos_bloques_en_el_mismo_sitio() -> None:
    from bingo.dominio.tema import detectar_solapes

    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(base, reloj=dataclasses.replace(base.bombo))
    pares = detectar_solapes(tema)
    assert ("bombo", "reloj") in pares or ("reloj", "bombo") in pares


def test_detectar_solapes_ignora_bloques_no_visibles() -> None:
    from bingo.dominio.tema import detectar_solapes

    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(
        base,
        reloj=dataclasses.replace(base.bombo, visible=False),
    )
    assert detectar_solapes(tema) == []


def test_validar_rechaza_numero_actual_muy_pequeno() -> None:
    """Decisión DU-6: por debajo del 14% del alto del lienzo, no se lee en
    un móvil con vídeo comprimido — es un requisito duro, no un aviso."""
    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(
        base, numero_actual=dataclasses.replace(base.numero_actual, escala=0.1)
    )
    with pytest.raises(ErrorValidacion):
        validar(tema)


def test_validar_permite_numero_actual_pequeno_si_no_es_visible() -> None:
    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(
        base,
        numero_actual=dataclasses.replace(base.numero_actual, escala=0.1, visible=False),
    )
    validar(tema)  # no lanza


def test_validar_rechaza_sin_reclamo_invalido() -> None:
    from bingo.dominio.tema import ConfigJuego

    tema = dataclasses.replace(
        TemaDashboard.por_defecto(), juego=ConfigJuego(sin_reclamo="lo que sea")
    )
    with pytest.raises(ErrorValidacion):
        validar(tema)


def test_validar_rechaza_modo_invalido() -> None:
    from bingo.dominio.tema import ConfigJuego

    tema = dataclasses.replace(TemaDashboard.por_defecto(), juego=ConfigJuego(modo="rapido"))
    with pytest.raises(ErrorValidacion):
        validar(tema)


def test_validar_permite_fondo_transparente() -> None:
    """Tarea 4.18 (expansión E2): `"transparente"` es el único valor no
    hexadecimal válido de `colores.fondo` — para OBS con filtro de croma."""
    from bingo.dominio.tema import FONDO_TRANSPARENTE

    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(
        base, colores=dataclasses.replace(base.colores, fondo=FONDO_TRANSPARENTE)
    )
    validar(tema)  # no lanza


def test_validar_rechaza_croma_invalido() -> None:
    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(base, colores=dataclasses.replace(base.colores, croma="no-es-color"))
    with pytest.raises(ErrorValidacion):
        validar(tema)


def test_roundtrip_conserva_fondo_transparente_y_croma() -> None:
    from bingo.dominio.tema import FONDO_TRANSPARENTE

    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(
        base, colores=dataclasses.replace(base.colores, fondo=FONDO_TRANSPARENTE, croma="#ff00ff")
    )
    recuperado = TemaDashboard.desde_json(tema.a_json())
    assert recuperado.colores.fondo == FONDO_TRANSPARENTE
    assert recuperado.colores.croma == "#ff00ff"


def test_advertencias_contraste_preset_por_defecto_no_avisa() -> None:
    from bingo.dominio.tema import advertencias_contraste

    assert advertencias_contraste(TemaDashboard.por_defecto()) == []


def test_advertencias_contraste_detecta_bajo_contraste() -> None:
    from bingo.dominio.tema import advertencias_contraste

    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(
        base,
        colores=dataclasses.replace(base.colores, texto="#0b0b14"),  # igual al fondo
    )
    avisos = advertencias_contraste(tema)
    assert "tema.aviso.contraste_texto" in avisos


def test_advertencias_contraste_con_fondo_transparente_usa_el_croma() -> None:
    """Tarea 4.18: con `fondo == "transparente"` no hay contra qué medir
    contraste salvo el croma — es lo que de verdad pinta la vista previa y
    lo que ve el operador que abre la transmisión sin OBS delante."""
    from bingo.dominio.tema import FONDO_TRANSPARENTE, advertencias_contraste

    base = TemaDashboard.por_defecto()
    tema = dataclasses.replace(
        base,
        colores=dataclasses.replace(
            base.colores, fondo=FONDO_TRANSPARENTE, croma=base.colores.texto
        ),
    )
    avisos = advertencias_contraste(tema)
    assert "tema.aviso.contraste_texto" in avisos


def test_bloques_tiene_posicion_por_defecto_para_todos() -> None:
    """Decisión DU-4: `BLOQUES` lleva posición por defecto, no solo
    dimensiones — y cada entrada corresponde a un atributo real de
    `TemaDashboard` con esa misma posición."""
    from bingo.dominio.tema import BLOQUES

    tema = TemaDashboard.por_defecto()
    for clave, _clave_i18n, pos_x, pos_y, _ancho, _alto in BLOQUES:
        bloque = getattr(tema, clave)
        assert bloque.pos_x == pos_x
        assert bloque.pos_y == pos_y


def test_ida_y_vuelta_conserva_idioma_publico_y_version() -> None:
    tema = dataclasses.replace(TemaDashboard.por_defecto(), idioma_publico="en", version=1)
    recuperado = TemaDashboard.desde_json(tema.a_json())
    assert recuperado.idioma_publico == "en"
    assert recuperado.version == 1


def test_claves_de_tema_no_cambian_sin_darse_cuenta() -> None:
    """Hallazgo V6: `_combinar()` ignora claves desconocidas — una clave mal
    escrita en `tema_json` se ignoraría para siempre, sin error. Esta
    prueba compara el conjunto de campos de nivel superior contra un
    fixture: ampliar el modelo pasa a ser un cambio consciente que
    actualiza esta lista, no un accidente que nadie ve."""
    campos_esperados = {
        "colores",
        "imagen_fondo",
        "bombo",
        "tablero_75",
        "contador_bolas",
        "reloj",
        "numero_actual",
        "patron_activo",
        "imagen_premio",
        "logo",
        "banner_texto",
        "pantalla_bienvenida",
        "pantalla_cierre",
        "juego",
        "idioma_publico",
        "version",
    }
    assert {f.name for f in dataclasses.fields(TemaDashboard)} == campos_esperados
