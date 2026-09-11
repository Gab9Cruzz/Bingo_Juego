"""Pruebas offscreen de `VistaAjustes` (tarea 4.12: sección de respaldos)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from bingo import i18n
from bingo.ui.vistas.vista_ajustes import VistaAjustes


def test_boton_restaurar_sin_gancho_no_hace_nada(
    qapp, con: sqlite3.Connection, monkeypatch
) -> None:
    """Defensivo: una prueba (u otro código) que instancie esta vista sola,
    sin pasar por `VentanaPrincipal.establecer_gancho_restaurar`, no debe
    reventar al pulsar el botón — ni siquiera debe abrir el diálogo de
    archivo, que en una prueba real bloquearía esperando un clic."""
    i18n.cargar("es")
    vista = VistaAjustes(con)

    def _fallar_si_se_llama(*_a: object, **_k: object) -> tuple[str, str]:
        raise AssertionError("no debería abrirse el diálogo sin un gancho registrado")

    monkeypatch.setattr(
        "bingo.ui.vistas.vista_ajustes.QFileDialog.getOpenFileName", _fallar_si_se_llama
    )

    vista._restaurar_desde_respaldo()  # noqa: SLF001 — no debe lanzar


def test_restaurar_desde_respaldo_llama_al_gancho_si_se_confirma(
    qapp, con: sqlite3.Connection, tmp_path: Path, monkeypatch
) -> None:
    i18n.cargar("es")
    vista = VistaAjustes(con)

    ruta_zip = tmp_path / "respaldo.zip"
    monkeypatch.setattr(
        "bingo.ui.vistas.vista_ajustes.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(ruta_zip), "Zip (*.zip)"),
    )
    monkeypatch.setattr("bingo.ui.vistas.vista_ajustes.confirmar", lambda *a, **k: True)

    recibido: list[Path] = []
    vista.establecer_gancho_restaurar(recibido.append)
    vista._restaurar_desde_respaldo()  # noqa: SLF001

    assert recibido == [ruta_zip]


def test_restaurar_desde_respaldo_no_llama_al_gancho_si_se_cancela(
    qapp, con: sqlite3.Connection, tmp_path: Path, monkeypatch
) -> None:
    i18n.cargar("es")
    vista = VistaAjustes(con)

    ruta_zip = tmp_path / "respaldo.zip"
    monkeypatch.setattr(
        "bingo.ui.vistas.vista_ajustes.QFileDialog.getOpenFileName",
        lambda *a, **k: (str(ruta_zip), "Zip (*.zip)"),
    )
    monkeypatch.setattr("bingo.ui.vistas.vista_ajustes.confirmar", lambda *a, **k: False)

    recibido: list[Path] = []
    vista.establecer_gancho_restaurar(recibido.append)
    vista._restaurar_desde_respaldo()  # noqa: SLF001

    assert recibido == []


def test_restaurar_desde_respaldo_no_llama_al_gancho_si_no_elige_archivo(
    qapp, con: sqlite3.Connection, monkeypatch
) -> None:
    i18n.cargar("es")
    vista = VistaAjustes(con)

    monkeypatch.setattr(
        "bingo.ui.vistas.vista_ajustes.QFileDialog.getOpenFileName", lambda *a, **k: ("", "")
    )
    monkeypatch.setattr("bingo.ui.vistas.vista_ajustes.confirmar", lambda *a, **k: True)

    recibido: list[Path] = []
    vista.establecer_gancho_restaurar(recibido.append)
    vista._restaurar_desde_respaldo()  # noqa: SLF001

    assert recibido == []
