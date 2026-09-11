from __future__ import annotations

import sqlite3
from pathlib import Path

from factorias import crear_evento, crear_organizacion

from bingo import i18n
from bingo.persistencia import repo_auditoria
from bingo.ui.vistas import vista_auditoria as modulo_vista
from bingo.ui.vistas.vista_auditoria import VistaAuditoria


def _preparar(con: sqlite3.Connection):
    i18n.cargar("es")
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    repo_auditoria.registrar(con, evento.id, "sorteo.ronda_iniciada", detalle="1")
    repo_auditoria.registrar(con, evento.id, "venta.anulada", detalle="carton=A-1")
    return con, evento


def test_carga_muestra_todas_las_filas(qapp, con: sqlite3.Connection, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaAuditoria(con, evento)
    assert vista._tabla.rowCount() == 2  # noqa: SLF001


def test_filtro_por_prefijo_reduce_las_filas(qapp, con: sqlite3.Connection, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaAuditoria(con, evento)

    vista._campo_filtro.setText("venta.")  # noqa: SLF001

    assert vista._tabla.rowCount() == 1  # noqa: SLF001
    assert vista._tabla.item(0, 1).text() == "venta.anulada"  # noqa: SLF001


def test_tabla_no_es_editable(qapp, con: sqlite3.Connection, bingo_home) -> None:
    from PySide6.QtCore import Qt

    con, evento = _preparar(con)
    vista = VistaAuditoria(con, evento)
    item = vista._tabla.item(0, 0)  # noqa: SLF001
    assert not (item.flags() & Qt.ItemFlag.ItemIsEditable)


def test_exportar_llama_al_servicio_con_el_filtro_activo(
    qapp, con: sqlite3.Connection, bingo_home, tmp_path: Path, monkeypatch
) -> None:
    con, evento = _preparar(con)
    vista = VistaAuditoria(con, evento)
    vista._campo_filtro.setText("venta.")  # noqa: SLF001

    ruta = tmp_path / "auditoria.xlsx"
    monkeypatch.setattr(
        modulo_vista.QFileDialog, "getSaveFileName", lambda *a, **k: (str(ruta), "")
    )

    vista._exportar()  # noqa: SLF001

    assert ruta.exists()
    assert not vista._franja.isHidden()  # noqa: SLF001


def test_exportar_cancelado_no_llama_al_servicio(
    qapp, con: sqlite3.Connection, bingo_home, monkeypatch
) -> None:
    con, evento = _preparar(con)
    vista = VistaAuditoria(con, evento)

    monkeypatch.setattr(modulo_vista.QFileDialog, "getSaveFileName", lambda *a, **k: ("", ""))

    vista._exportar()  # noqa: SLF001 — no debe lanzar
