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


# ── DRY con dominio.tema.BLOQUES y campos nuevos (tarea 4.21) ───────────────


def test_editar_un_bloque_no_borra_los_campos_de_directo_del_juego(qapp, con, bingo_home) -> None:
    """Hallazgo encontrado al escribir la tarea 4.21: antes de basar
    `_leer_formulario()` en `dataclasses.replace(self._tema.juego, ...)`,
    cualquier autoguardado de esta vista reescribía `ConfigJuego` entero,
    revirtiendo en silencio los campos "de directo" (decisión DU-7) que la
    sección Sorteo persiste sueltos con `repo_evento.actualizar_juego`."""
    import dataclasses

    con, evento = _preparar(con)
    tema = TemaDashboard.por_defecto()
    tema = dataclasses.replace(
        tema, juego=dataclasses.replace(tema.juego, modo="automatico", intervalo_seg=10)
    )
    repo_evento.actualizar_tema(con, evento.id, tema.a_json())
    evento = repo_evento.obtener(con, evento.id)

    vista = VistaTema(con, evento)
    vista._campos_bloque["bombo"]["visible"].setChecked(False)  # noqa: SLF001
    vista._marcar_cambio()  # noqa: SLF001
    vista._guardar()  # noqa: SLF001

    guardado = TemaDashboard.desde_json(repo_evento.obtener(con, evento.id).tema_json)
    assert guardado.juego.modo == "automatico"
    assert guardado.juego.intervalo_seg == 10
    assert guardado.bombo.visible is False


def test_bloques_nuevos_de_la_fase_5_son_editables(qapp, con, bingo_home) -> None:
    """`dominio.tema.BLOQUES` (única fuente, tarea 4.21) trae cuatro bloques
    que el editor no exponía: numero_actual, patron_activo, imagen_premio,
    logo."""
    con, evento = _preparar(con)
    vista = VistaTema(con, evento)

    for clave in ("numero_actual", "patron_activo", "imagen_premio", "logo"):
        assert clave in vista._campos_bloque  # noqa: SLF001

    vista._campos_bloque["logo"]["visible"].setChecked(False)  # noqa: SLF001
    vista._marcar_cambio()  # noqa: SLF001
    vista._guardar()  # noqa: SLF001

    guardado = TemaDashboard.desde_json(repo_evento.obtener(con, evento.id).tema_json)
    assert guardado.logo.visible is False


def test_campos_de_preparacion_del_juego_persisten(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaTema(con, evento)

    vista._check_pausa_al_ganador.setChecked(False)  # noqa: SLF001
    vista._spin_segundos_reclamo.setValue(45)  # noqa: SLF001
    vista._campo_canal_reclamo.setText("WhatsApp 099-000-0000")  # noqa: SLF001
    indice_cerrar = vista._combo_sin_reclamo.findData("cerrar")  # noqa: SLF001
    vista._combo_sin_reclamo.setCurrentIndex(indice_cerrar)  # noqa: SLF001
    vista._marcar_cambio()  # noqa: SLF001
    vista._guardar()  # noqa: SLF001

    guardado = TemaDashboard.desde_json(repo_evento.obtener(con, evento.id).tema_json)
    assert guardado.juego.pausa_al_ganador is False
    assert guardado.juego.segundos_reclamo == 45
    assert guardado.juego.canal_reclamo == "WhatsApp 099-000-0000"
    assert guardado.juego.sin_reclamo == "cerrar"


def test_color_numero_actual_persiste(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaTema(con, evento)

    vista._color_numero_actual.establecer_color("#00aaff")  # noqa: SLF001
    vista._marcar_cambio()  # noqa: SLF001
    vista._guardar()  # noqa: SLF001

    guardado = TemaDashboard.desde_json(repo_evento.obtener(con, evento.id).tema_json)
    assert guardado.colores.numero_actual == "#00aaff"


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
