"""`principal(argv)` completo, sin ventana visible, contra un `BINGO_HOME` limpio."""

from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

import bingo.__main__ as modulo_principal


@pytest.fixture(autouse=True)
def _salir_del_bucle_de_eventos(monkeypatch: pytest.MonkeyPatch) -> None:
    """`app.exec()` normalmente bloquea hasta que el usuario cierra la ventana.
    En la prueba, se cierra sola apenas entra al bucle.
    """

    def _exec_falso(self: QApplication) -> int:
        QTimer.singleShot(50, self.quit)
        return 0

    monkeypatch.setattr(QApplication, "exec", _exec_falso)


def test_principal_arranca_limpio_y_sale_sin_error(bingo_home) -> None:
    codigo = modulo_principal.principal([])
    assert codigo == 0
    assert (bingo_home / "datos" / "bingo.db").exists()
    assert (bingo_home / "logs" / "aplicacion.log").exists()


def test_arranque_no_deja_fila_en_auditoria(bingo_home) -> None:
    modulo_principal.principal([])
    con = sqlite3.connect(bingo_home / "datos" / "bingo.db")
    filas = con.execute("SELECT COUNT(*) FROM auditoria").fetchone()[0]
    con.close()
    assert filas == 0


def test_forzar_instancia_funciona(bingo_home) -> None:
    codigo = modulo_principal.principal(["--forzar-instancia"])
    assert codigo == 0


def test_arranque_limpia_lote_huerfano_de_una_sesion_anterior(bingo_home) -> None:
    """Simula un proceso muerto a mitad de `generar_lote` (fase 2, hallazgo Eng
    #5): un lote sin `completado_en` no debe sobrevivir al siguiente arranque.
    """
    modulo_principal.principal([])  # primer arranque: crea y migra la base

    ruta_bd = bingo_home / "datos" / "bingo.db"
    con = sqlite3.connect(ruta_bd)
    con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('Org', 'y')")
    org_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO evento (organizacion_id, nombre, creado_en) VALUES (?, 'e', 'y')", (org_id,)
    )
    evento_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO lote (evento_id, cantidad, prefijo_codigo, semilla, generado_en) "
        "VALUES (?, 1, 'H', 's', 'y')",
        (evento_id,),
    )
    con.commit()
    con.close()

    modulo_principal.principal([])  # segundo arranque: debe limpiar el huérfano

    con = sqlite3.connect(ruta_bd)
    total_lotes = con.execute("SELECT COUNT(*) FROM lote").fetchone()[0]
    con.close()
    assert total_lotes == 0
