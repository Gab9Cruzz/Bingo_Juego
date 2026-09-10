from __future__ import annotations

from typing import Any

from factorias import crear_evento, crear_organizacion, crear_patron, crear_ronda

from bingo import i18n
from bingo.persistencia import repo_ronda
from bingo.ui.vistas.vista_rondas import VistaRondas


def _preparar(con: Any) -> tuple[Any, Any]:
    i18n.cargar("es")
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    return con, evento


def test_vista_vacia(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaRondas(con, evento)
    assert vista._lista.count() == 0
    assert not vista._panel_formulario.isEnabled()


def test_seleccionar_ronda_habilita_formulario(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    patron = crear_patron(con)
    crear_ronda(con, evento.id, patron.id, orden=1, nombre="Ronda 1")
    vista = VistaRondas(con, evento)
    assert vista._lista.count() == 1
    assert vista._panel_formulario.isEnabled()
    assert vista._campo_nombre.text() == "Ronda 1"


def test_subir_llama_a_reordenar_con_la_lista_correcta(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    patron = crear_patron(con)
    r1 = crear_ronda(con, evento.id, patron.id, orden=1, nombre="R1")
    r2 = crear_ronda(con, evento.id, patron.id, orden=2, nombre="R2")
    vista = VistaRondas(con, evento)
    vista._lista.setCurrentRow(1)  # R2

    vista._mover(-1)

    rondas = repo_ronda.listar_por_evento(con, evento.id)
    assert [r.id for r in rondas] == [r2.id, r1.id]
    # DS15: la ronda movida sigue seleccionada tras el reordenado.
    assert vista._lista.currentItem().text() == "R2"


def test_guardar_formulario_actualiza_la_ronda(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    patron = crear_patron(con)
    crear_ronda(con, evento.id, patron.id, orden=1, nombre="Original")
    vista = VistaRondas(con, evento)

    vista._campo_nombre.setText("Renombrada")
    vista._marcar_cambio()

    actualizada = repo_ronda.listar_por_evento(con, evento.id)[0]
    assert actualizada.nombre == "Renombrada"


def test_pendientes_se_actualizan_al_cargar(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaRondas(con, evento)
    assert "rondas.pendiente.sin_rondas" not in vista._etiqueta_pendientes.text()
    assert vista._etiqueta_pendientes.text() != ""
