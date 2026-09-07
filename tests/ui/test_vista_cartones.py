"""Pruebas offscreen de `VistaCartones` (contrato de la fase 2, §2.5).

`Tarea` real (`QThread`) no se ejercita aquí: se sustituye por un doble de
prueba que expone las mismas señales pero no arranca un hilo real, siguiendo
la nota del propio plan de la fase ("mock de Tarea... sin hilo real en
prueba"). El flujo del hilo en sí (`ui/tarea.py::Tarea`) ya tiene su propia
cobertura implícita en `servicio_cartones` (que es lo que `Tarea.run()`
invoca) y no necesita reprobarse aquí.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from factorias import crear_evento, crear_organizacion
from PySide6.QtCore import QObject, Signal

from bingo import i18n
from bingo.servicios import servicio_cartones
from bingo.ui.vistas import vista_cartones as modulo_vista
from bingo.ui.vistas.vista_cartones import VistaCartones
from bingo.utilidades.errores import ErrorValidacion


class _TareaFalsa(QObject):
    """Mismas señales que `ui/tarea.py::Tarea`, sin `QThread` real: `start()`
    solo registra que se pidió arrancar, para que la prueba controle a mano
    cuándo "termina" emitiendo `terminado`/`fallado`.
    """

    progreso = Signal(int, int)
    terminado = Signal(object)
    fallado = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.iniciada = False
        self.cancelada = False

    def start(self) -> None:
        self.iniciada = True

    def cancelar(self) -> None:
        self.cancelada = True


def _preparar(con: Any) -> tuple[Any, Any]:
    i18n.cargar("es")
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id)
    return con, evento


def test_vista_vacia_muestra_cta(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaCartones(con, evento)

    # `isVisible()` es siempre False en un widget que nunca se `.show()`; la
    # bandera explícita que sí importa aquí es `isHidden()` (ver test_navegacion.py).
    assert not vista._panel_vacio.isHidden()
    assert vista._splitter.isHidden()
    assert vista._etiqueta_vacio.text() == "Aún no hay cartones generados"
    assert not vista._boton_vacio.isHidden()


def test_generar_lote_actualiza_listado_y_resumen(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    servicio_cartones.generar_lote(con, evento.id, 5, "ABC", semilla="s1")

    vista = VistaCartones(con, evento)

    assert vista._panel_vacio.isHidden()
    assert not vista._splitter.isHidden()
    assert vista._modelo.rowCount() == 5
    assert vista._etiquetas_resumen[None].text() == "Total 5"
    assert vista._etiquetas_resumen["generado"].text() == "Generado 5"


def test_filtro_sin_resultados_muestra_mensaje(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    servicio_cartones.generar_lote(con, evento.id, 3, "ABC", semilla="s2")

    vista = VistaCartones(con, evento)
    vista._campo_busqueda.setText("NO-EXISTE")

    assert not vista._panel_vacio.isHidden()
    assert vista._splitter.isHidden()
    assert vista._etiqueta_vacio.text() == "Ningún cartón coincide con el filtro"
    assert vista._boton_vacio.isHidden()  # no se ofrece "generar" de nuevo, ya hay cartones


def test_seleccionar_fila_dibuja_el_carton_y_perderla_limpia_el_visor(
    qapp, con, bingo_home
) -> None:
    con, evento = _preparar(con)
    servicio_cartones.generar_lote(con, evento.id, 3, "ABC", semilla="s3")

    vista = VistaCartones(con, evento)
    vista._tabla.selectRow(0)
    assert vista._visor._carton is not None

    vista._campo_busqueda.setText("NO-EXISTE")
    assert vista._visor._carton is None


def test_doble_clic_no_lanza_una_segunda_tarea(qapp, con, bingo_home, monkeypatch) -> None:
    con, evento = _preparar(con)
    vista = VistaCartones(con, evento)

    tareas_creadas: list[_TareaFalsa] = []

    def _fabrica_tarea(*_args: object, **_kwargs: object) -> _TareaFalsa:
        falsa = _TareaFalsa()
        tareas_creadas.append(falsa)
        return falsa

    monkeypatch.setattr(modulo_vista, "Tarea", _fabrica_tarea)

    vista._lanzar_tarea(5, "DBL")

    assert len(tareas_creadas) == 1
    assert tareas_creadas[0].iniciada
    assert vista._boton_generar.isHidden()
    assert not vista._boton_cancelar_tarea.isHidden()


def test_boton_generar_se_reactiva_en_terminado(qapp, con, bingo_home, monkeypatch) -> None:
    con, evento = _preparar(con)
    vista = VistaCartones(con, evento)

    tarea = _TareaFalsa()
    monkeypatch.setattr(modulo_vista, "Tarea", lambda *_a, **_k: tarea)
    vista._lanzar_tarea(1, "OK")

    lote_falso = SimpleNamespace(completado_en="2026-01-01T00:00:00Z")
    tarea.terminado.emit(lote_falso)

    assert not vista._boton_generar.isHidden()
    assert vista._boton_generar.isEnabled()
    assert vista._boton_cancelar_tarea.isHidden()


def test_boton_generar_se_reactiva_en_fallado(qapp, con, bingo_home, monkeypatch) -> None:
    con, evento = _preparar(con)
    vista = VistaCartones(con, evento)

    tarea = _TareaFalsa()
    monkeypatch.setattr(modulo_vista, "Tarea", lambda *_a, **_k: tarea)
    vista._lanzar_tarea(1, "FALLA")

    tarea.fallado.emit(ErrorValidacion("cartones.error.prefijo_repetido", campo="prefijo_codigo"))

    assert not vista._boton_generar.isHidden()
    assert vista._boton_generar.isEnabled()


def test_cancelacion_muestra_aviso_no_exito(qapp, con, bingo_home, monkeypatch) -> None:
    con, evento = _preparar(con)
    vista = VistaCartones(con, evento)

    tarea = _TareaFalsa()
    monkeypatch.setattr(modulo_vista, "Tarea", lambda *_a, **_k: tarea)
    vista._lanzar_tarea(100, "CANCEL")

    lote_cancelado = SimpleNamespace(completado_en=None)
    tarea.terminado.emit(lote_cancelado)

    assert vista._franja._etiqueta.text() == "Generación cancelada"


def test_retraducir_no_toca_texto_tecleado_en_busqueda(qapp, con, bingo_home) -> None:
    con, evento = _preparar(con)
    vista = VistaCartones(con, evento)
    vista._campo_busqueda.setText("algo que el operador escribió")

    i18n.cargar("en")
    i18n.cargar("es")

    assert vista._campo_busqueda.text() == "algo que el operador escribió"
