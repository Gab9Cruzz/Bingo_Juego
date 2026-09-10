"""`principal(argv)` completo, sin ventana visible, contra un `BINGO_HOME` limpio."""

from __future__ import annotations

import sqlite3

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QMessageBox

import bingo.__main__ as modulo_principal
from bingo.utilidades import log as bingo_log


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


def _crear_evento_y_devolver_id(ruta_bd) -> int:
    con = sqlite3.connect(ruta_bd)
    con.execute("INSERT INTO organizacion (nombre, creada_en) VALUES ('Org', 'y')")
    org_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.execute(
        "INSERT INTO evento (organizacion_id, nombre, creado_en) VALUES (?, 'Evento X', 'y')",
        (org_id,),
    )
    evento_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.commit()
    con.close()
    return evento_id


def test_restaurar_exitoso_arranca_normal(bingo_home) -> None:
    """Tarea 4.12, hallazgo E-11: `--restaurar` corre antes que todo lo
    demás y deja la aplicación arrancando normal encima de los datos
    restaurados."""
    modulo_principal.principal([])
    ruta_bd = bingo_home / "datos" / "bingo.db"
    evento_id = _crear_evento_y_devolver_id(ruta_bd)

    from bingo.servicios import servicio_respaldos

    ruta_zip = servicio_respaldos.exportar(evento_id)
    assert ruta_zip is not None

    # `principal()` deja el manejador del log de la aplicación abierto
    # (correcto: en uso real, `--restaurar` corre en un proceso nuevo que
    # todavía no configuró ningún log). Aquí, en el mismo proceso de la
    # prueba, hay que soltarlo a mano o mover la carpeta de datos falla con
    # `WinError 32` — el mismo motivo por el que la tarea 4.12 exige que
    # `--restaurar` solo se use con la aplicación cerrada.
    bingo_log.reiniciar_para_pruebas()

    codigo = modulo_principal.principal(["--restaurar", str(ruta_zip), "--forzar-instancia"])

    assert codigo == 0
    con = sqlite3.connect(ruta_bd)
    nombre = con.execute("SELECT nombre FROM evento WHERE id = ?", (evento_id,)).fetchone()[0]
    con.close()
    assert nombre == "Evento X"


def test_restaurar_zip_invalido_devuelve_codigo_6(
    bingo_home, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # El modal de error es de verdad (canal 3, "condición terminal") — sin
    # esto, `.exec()` bloquearía la prueba esperando un clic que no llega.
    monkeypatch.setattr(QMessageBox, "critical", lambda *a, **k: QMessageBox.StandardButton.Ok)

    modulo_principal.principal([])
    zip_malo = tmp_path / "malo.zip"
    zip_malo.write_bytes(b"esto no es un zip de verdad")
    bingo_log.reiniciar_para_pruebas()

    codigo = modulo_principal.principal(["--restaurar", str(zip_malo), "--forzar-instancia"])

    assert codigo == 6
