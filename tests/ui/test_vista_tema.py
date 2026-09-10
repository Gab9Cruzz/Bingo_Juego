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
