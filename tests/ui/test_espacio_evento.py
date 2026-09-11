from __future__ import annotations

import sqlite3

from factorias import crear_carton, crear_comprador, crear_patron, crear_ronda

from bingo import i18n
from bingo.persistencia import repo_ronda
from bingo.servicios.servicio_sorteo import MotorSorteo
from bingo.ui import dialogos
from bingo.ui.espacio_evento import EspacioEvento
from bingo.ui.registro_vistas import SECCIONES_ESPACIO_EVENTO


def _cantidad_de_grupos() -> int:
    return len({entrada.grupo for entrada in SECCIONES_ESPACIO_EVENTO})


def test_riel_tiene_un_encabezado_por_grupo_y_una_fila_por_seccion(
    qapp, con: sqlite3.Connection, evento_creado
) -> None:
    i18n.cargar("es")
    espacio = EspacioEvento(con, evento_creado)
    total_esperado = len(SECCIONES_ESPACIO_EVENTO) + _cantidad_de_grupos()
    assert espacio._riel.count() == total_esperado  # noqa: SLF001
    assert len(espacio._indices_widget) == len(SECCIONES_ESPACIO_EVENTO)  # noqa: SLF001


def test_encabezados_de_grupo_no_son_seleccionables(
    qapp, con: sqlite3.Connection, evento_creado
) -> None:
    from PySide6.QtCore import Qt

    i18n.cargar("es")
    espacio = EspacioEvento(con, evento_creado)
    for fila, (tipo, _valor) in enumerate(espacio._filas_riel):  # noqa: SLF001
        if tipo == "encabezado":
            item = espacio._riel.item(fila)  # noqa: SLF001
            assert not (item.flags() & Qt.ItemFlag.ItemIsSelectable)


def test_motor_sorteo_es_una_sola_instancia_estable(
    qapp, con: sqlite3.Connection, evento_creado
) -> None:
    """Hallazgo S5-3: el motor vive en `EspacioEvento`, no en la vista —
    tiene que sobrevivir a un cambio de sección del riel."""
    i18n.cargar("es")
    espacio = EspacioEvento(con, evento_creado)
    assert isinstance(espacio.motor_sorteo, MotorSorteo)
    motor_antes = espacio.motor_sorteo
    espacio._riel.setCurrentRow(espacio._indices_widget[-1])  # noqa: SLF001
    espacio._riel.setCurrentRow(espacio._indices_widget[0])  # noqa: SLF001
    assert espacio.motor_sorteo is motor_antes


def test_modo_vivo_oculta_riel_y_cabecera(qapp, con: sqlite3.Connection, evento_creado) -> None:
    i18n.cargar("es")
    espacio = EspacioEvento(con, evento_creado)
    assert not espacio.modo_vivo

    espacio.activar_modo_vivo()
    assert espacio.modo_vivo
    assert espacio._riel.isHidden()  # noqa: SLF001
    assert espacio._franja_marca.isHidden()  # noqa: SLF001

    espacio.desactivar_modo_vivo()
    assert not espacio.modo_vivo
    assert not espacio._riel.isHidden()  # noqa: SLF001
    assert not espacio._franja_marca.isHidden()  # noqa: SLF001


def test_hay_ronda_viva_falso_sin_rondas(qapp, con: sqlite3.Connection, evento_creado) -> None:
    i18n.cargar("es")
    espacio = EspacioEvento(con, evento_creado)
    assert not espacio.hay_ronda_viva()


def test_hay_ronda_viva_verdadero_con_ronda_en_curso(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con)
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)

    espacio = EspacioEvento(con, evento_creado)
    espacio.motor_sorteo.iniciar_ronda(con, ronda.id)

    assert espacio.hay_ronda_viva()


def test_cerrar_sin_ronda_viva_emite_directo(qapp, con: sqlite3.Connection, evento_creado) -> None:
    i18n.cargar("es")
    espacio = EspacioEvento(con, evento_creado)
    emitidos = []
    espacio.cerrado.connect(lambda: emitidos.append(1))

    espacio._boton_cerrar.click()  # noqa: SLF001

    assert emitidos == [1]


def test_cerrar_con_ronda_viva_pide_confirmacion_y_respeta_cancelar(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado, monkeypatch
) -> None:
    """Hallazgo DU-11: los dos botones que hoy destruyen `EspacioEvento` sin
    avisar (`_boton_volver`, `_boton_cerrar`) exigen confirmación explícita
    con una ronda en curso o pausada."""
    i18n.cargar("es")
    patron = crear_patron(con)
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)

    espacio = EspacioEvento(con, evento_creado)
    espacio.motor_sorteo.iniciar_ronda(con, ronda.id)
    emitidos = []
    espacio.cerrado.connect(lambda: emitidos.append(1))

    monkeypatch.setattr(dialogos, "confirmar", lambda *a, **k: False)
    espacio._boton_cerrar.click()  # noqa: SLF001
    assert emitidos == []

    monkeypatch.setattr(dialogos, "confirmar", lambda *a, **k: True)
    espacio._boton_volver.click()  # noqa: SLF001
    assert emitidos == [1]


def test_modo_vivo_degrada_error_no_terminal_pero_no_uno_terminal(
    qapp, con: sqlite3.Connection, evento_creado, monkeypatch
) -> None:
    """Tarea 4.27 (regla explícita de `modo_vivo`, corrección §B.5,
    DU-12): con `modo_vivo` activo, un `ErrorPersistencia` (canal 2, no
    terminal) sigue sin abrir modal — nunca lo hizo, en ningún modo: cada
    vista atrapa `ErrorBingo` y lo pinta con `self._franja.mostrar_error`,
    nunca con un `QMessageBox`. La separación es del lado del tipo de error
    y de qué código lo atrapa, no de una bandera en tiempo de ejecución, así
    que no hace falta (ni existe) un parámetro `modo_vivo` en
    `dialogos.confirmar`/`dialogos.mostrar_error_modal` para lograrlo — la
    prueba fija esa garantía, no la reimplementa.

    `mostrar_error_modal` (canal 3, terminal: base corrupta, migración
    fallida, sin permisos) sigue siendo modal SIEMPRE, incluso en directo:
    solo se llama desde `__main__.principal()`, antes de que exista
    cualquier `EspacioEvento`/`modo_vivo` — estructuralmente no puede
    degradarse.
    """
    from bingo.ui import dialogos as modulo_dialogos
    from bingo.utilidades.errores import ErrorBaseCorrupta, ErrorPersistencia

    i18n.cargar("es")
    espacio = EspacioEvento(con, evento_creado)
    espacio.activar_modo_vivo()
    # El widget en `_contenido` se añade en el mismo orden que
    # `SECCIONES_ESPACIO_EVENTO` (sin encabezados) — no el índice de fila del
    # riel, que sí cuenta los encabezados de grupo.
    indice_pila_sorteo = [e.clave_i18n for e in SECCIONES_ESPACIO_EVENTO].index(
        "espacio_evento.seccion.sorteo"
    )
    vista_sorteo = espacio._contenido.widget(indice_pila_sorteo)  # noqa: SLF001

    def _fallar_si_se_abre_un_modal(self: object) -> None:
        raise AssertionError("un error no terminal no debe abrir un modal, ni en modo_vivo")

    monkeypatch.setattr(modulo_dialogos.QMessageBox, "exec", _fallar_si_se_abre_un_modal)

    vista_sorteo._al_fallar(ErrorPersistencia("error.persistencia.generico"))  # noqa: SLF001

    assert not vista_sorteo._franja.isHidden()  # noqa: SLF001
    assert vista_sorteo._franja.objectName() == "franjaError"  # noqa: SLF001

    # Canal 3: sigue siendo modal, incluso con modo_vivo activo — se prueba
    # llamando directo a `mostrar_error_modal` (no toma `modo_vivo`: no
    # existe ningún camino, ni en `__main__.py`, para pasárselo — solo se
    # invoca antes de que exista ningún `EspacioEvento`).
    abierto = {"veces": 0}
    monkeypatch.setattr(
        modulo_dialogos.QMessageBox,
        "exec",
        lambda self: abierto.__setitem__("veces", abierto["veces"] + 1),
    )
    modulo_dialogos.mostrar_error_modal(
        None,
        "arranque.error.base.titulo",
        "error.base_corrupta",
        detalle=str(ErrorBaseCorrupta("error.base_corrupta")),
        ruta_log="x",
    )
    assert abierto["veces"] == 1


def test_repo_ronda_obtener_en_juego_refleja_pausada(
    qapp, con: sqlite3.Connection, evento_creado, lote_creado
) -> None:
    i18n.cargar("es")
    patron = crear_patron(con)
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    ronda = crear_ronda(con, evento_creado.id, patron.id)

    espacio = EspacioEvento(con, evento_creado)
    espacio.motor_sorteo.iniciar_ronda(con, ronda.id)
    espacio.motor_sorteo.pausar(con, ronda.id)

    assert espacio.hay_ronda_viva()
    assert repo_ronda.obtener(con, ronda.id).estado == "pausada"
