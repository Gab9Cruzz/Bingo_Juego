from __future__ import annotations

from typing import Any

from factorias import crear_evento, crear_organizacion

from bingo import i18n
from bingo.dominio.tema import TemaDashboard
from bingo.persistencia import repo_evento
from bingo.ui.vistas.vista_tema import VistaTema


def _preparar(con: Any) -> tuple[Any, Any]:
    i18n.cargar("es")
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    return con, evento


def test_carga_tema_por_defecto(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaTema(con, evento)
    assert vista._tema == TemaDashboard.por_defecto()


def test_marcar_cambio_guarda_en_repo_evento(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaTema(con, evento)

    vista._color_acento.establecer_color("#112233")
    vista._marcar_cambio()
    assert vista._temporizador.isActive()
    vista._guardar()  # dispara a mano lo que el QTimer haría al vencer

    actualizado = repo_evento.obtener(con, evento.id)
    assert actualizado.tema_json is not None
    tema_guardado = TemaDashboard.desde_json(actualizado.tema_json)
    assert tema_guardado.colores.acento == "#112233"


def test_lienzo_se_actualiza_con_cada_cambio(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaTema(con, evento)
    vista._campos_bloque["bombo"]["visible"].setChecked(False)
    vista._marcar_cambio()
    assert vista._lienzo._tema.bombo.visible is False


def test_tildar_fondo_transparente_guarda_el_valor_especial(qapp, con, bingo_home) -> None:
    """Tarea 4.18 (expansión E2): la casilla, no el `BotonColor` de fondo
    (que nunca sabe mostrar "transparente"), decide qué se guarda."""
    from bingo.dominio.tema import FONDO_TRANSPARENTE

    con, evento = _preparar(con)
    vista = VistaTema(con, evento)

    vista._casilla_fondo_transparente.setChecked(True)
    vista._color_croma.establecer_color("#00ffcc")
    vista._marcar_cambio()
    vista._guardar()

    tema_guardado = TemaDashboard.desde_json(repo_evento.obtener(con, evento.id).tema_json)
    assert tema_guardado.colores.fondo == FONDO_TRANSPARENTE
    assert tema_guardado.colores.croma == "#00ffcc"


def test_destildar_fondo_transparente_vuelve_al_color_elegido(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaTema(con, evento)

    vista._casilla_fondo_transparente.setChecked(True)
    vista._casilla_fondo_transparente.setChecked(False)
    vista._color_fondo.establecer_color("#123456")
    vista._marcar_cambio()

    assert vista._tema.colores.fondo == "#123456"


def test_cargar_tema_transparente_muestra_la_casilla_tildada(qapp, con, bingo_home) -> None:
    from bingo.dominio.tema import FONDO_TRANSPARENTE, ConfigColores

    con, evento = _preparar(con)
    tema = TemaDashboard(colores=ConfigColores(fondo=FONDO_TRANSPARENTE, croma="#ff00ff"))
    repo_evento.actualizar_tema(con, evento.id, tema.a_json())
    evento = repo_evento.obtener(con, evento.id)  # `evento` original quedó con tema_json=None

    vista = VistaTema(con, evento)

    assert vista._casilla_fondo_transparente.isChecked()
    assert vista._color_croma.color == "#ff00ff"
    assert not vista._color_croma.isHidden()
    assert vista._color_fondo.isHidden()
