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
