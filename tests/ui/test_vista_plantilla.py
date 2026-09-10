"""Pruebas offscreen de `VistaPlantilla` (contrato de la fase 3, §3.4).

El temporizador de guardado/vista-previa no se espera con tiempo real: se
verifica que un cambio lo deja `isActive()` y se dispara a mano llamando al
método que conecta (mismo patrón que "mock de Tarea... sin hilo real" de
`test_vista_cartones.py`, aplicado aquí al `QTimer` en vez de al `QThread`).
"""

from __future__ import annotations

from typing import Any

from factorias import crear_evento, crear_organizacion

from bingo import i18n
from bingo.impresion.plantilla import PlantillaCarton
from bingo.persistencia import repo_evento
from bingo.ui.vistas.vista_plantilla import VistaPlantilla


def _preparar(con: Any) -> tuple[Any, Any]:
    i18n.cargar("es")
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    return con, evento


def test_carga_plantilla_por_defecto(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaPlantilla(con, evento)
    assert vista._combo_tamano.currentText() == "A4"
    assert vista._combo_cartones_por_hoja.currentData() == 4
    assert vista._campo_libre_texto.text() == "LIBRE"


def test_vista_previa_se_dibuja_al_abrir(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaPlantilla(con, evento)
    assert not vista._etiqueta_previa.pixmap().isNull()


def test_guarda_en_evento_al_cambiar_un_campo(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaPlantilla(con, evento)

    vista._campo_titulo.setText("Bingo Solidario 2026")
    assert vista._temporizador.isActive()
    vista._temporizador.stop()
    vista._guardar_y_previsualizar()

    guardado = repo_evento.obtener(con, evento.id)
    plantilla = PlantillaCarton.desde_json(guardado.plantilla_json)
    assert plantilla.marca.titulo == "Bingo Solidario 2026"


def test_campo_invalido_no_se_guarda(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaPlantilla(con, evento)
    guardado_valido = repo_evento.obtener(con, evento.id).plantilla_json
    assert guardado_valido is not None  # la construcción ya guardó la plantilla por defecto

    # Fuerza un estado inválido sin pasar por los widgets (p. ej. un color
    # corrupto no alcanzable desde `BotonColor`, que siempre produce hex
    # válido) para probar que `validar()` bloquea el guardado.
    vista._plantilla.marca.color_encabezado = "no-es-color"
    vista._guardar_y_previsualizar()

    guardado = repo_evento.obtener(con, evento.id)
    assert guardado.plantilla_json == guardado_valido  # sin cambios: el guardado inválido no pasó
    assert not vista._franja.isHidden()


def test_restablecer_desde_organizacion_copia_logo(qapp, con, bingo_home) -> None:
    from bingo.persistencia import repo_organizacion

    con, evento = _preparar(con)
    org = repo_organizacion.obtener(con, evento.organizacion_id)
    org.logo_path = "/ruta/logo-organizacion.png"
    org.color_primario = "#654321"
    repo_organizacion.actualizar(con, org)

    vista = VistaPlantilla(con, evento)
    vista._restablecer_desde_organizacion()

    assert vista._logo_actual == "/ruta/logo-organizacion.png"
    assert vista._color_encabezado.color == "#654321"


def test_asegura_clave_evento_al_abrir(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    assert evento.clave_evento is None
    VistaPlantilla(con, evento)
    assert repo_evento.obtener(con, evento.id).clave_evento is not None
