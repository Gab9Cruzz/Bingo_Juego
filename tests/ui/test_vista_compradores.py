"""Pruebas offscreen de `VistaCompradores` (contrato de la fase 4, §4.1-§4.4).

`Tarea` real no se ejercita (mismo doble de prueba que `test_vista_cartones.
_TareaFalsa`): el modal de importación se conduce a mano, llamando a los
métodos que las señales de la Tarea real dispararían.
"""

from __future__ import annotations

from typing import Any

from factorias import crear_carton, crear_evento, crear_lote, crear_organizacion
from PySide6.QtCore import QObject, Signal

from bingo import i18n
from bingo.dominio.modelos import Comprador
from bingo.persistencia import repo_carton, repo_comprador
from bingo.servicios import servicio_cartones
from bingo.servicios.servicio_compradores import FilaImportacion, InformeImportacion
from bingo.ui.vistas import vista_compradores as modulo_vista
from bingo.ui.vistas.vista_compradores import (
    FormularioCompradorDialog,
    ImportarComprasDialog,
    VentaPorRangoDialog,
    VistaCompradores,
)


class _TareaFalsa(QObject):
    progreso = Signal(int, int)
    terminado = Signal(object)
    fallado = Signal(object)

    def __init__(self, *_args: object, **_kwargs: object) -> None:
        super().__init__()
        self.iniciada = False

    def start(self) -> None:
        self.iniciada = True

    def isRunning(self) -> bool:  # noqa: N802 - mismo nombre que QThread
        return False

    def cancelar(self) -> None:
        pass


def _preparar(con: Any, cantidad: int = 3):
    i18n.cargar("es")
    org = crear_organizacion(con)
    evento = crear_evento(con, org.id, precio_tabla_centavos=100)
    lote = crear_lote(con, evento.id)
    cartones = [crear_carton(con, evento.id, lote.id, semilla=i) for i in range(cantidad)]
    for carton in cartones:
        servicio_cartones.cambiar_estado_carton(con, carton.id, "impreso")
    return con, evento, cartones


def test_vista_vacia_carga_sin_error(qapp, con, bingo_home) -> None:
    con, evento, _cartones = _preparar(con)
    vista = VistaCompradores(con, evento)
    assert vista._tabla.rowCount() == 0


def test_registrar_manual_actualiza_tabla(qapp, con, bingo_home) -> None:
    con, evento, cartones = _preparar(con)
    vista = VistaCompradores(con, evento)

    dialogo = FormularioCompradorDialog()
    dialogo._campo_codigo.setText(cartones[0].codigo)
    dialogo._campo_nombre.setText("Ana López")
    dialogo._aceptar()
    assert dialogo.resultado is not None

    codigo, comprador = dialogo.resultado
    from bingo.servicios import servicio_compradores

    servicio_compradores.registrar_manual(con, evento.id, codigo, comprador)
    vista.cargar()
    assert vista._tabla.rowCount() == 1
    assert vista._tabla.item(0, 1).text() == "Ana López"


def test_venta_por_rango_previsualiza_antes_de_habilitar_confirmar(qapp, con, bingo_home) -> None:
    con, evento, cartones = _preparar(con)
    dialogo = VentaPorRangoDialog(con, evento.id)
    assert not dialogo._boton_confirmar.isEnabled()

    dialogo._campo_desde.setText(cartones[0].codigo)
    dialogo._campo_hasta.setText(cartones[-1].codigo)
    dialogo._previsualizar()
    assert dialogo._boton_confirmar.isEnabled()
    assert "3" in dialogo._etiqueta_resumen.text()

    dialogo._confirmar()
    assert dialogo.aplicado is True
    assert repo_comprador.contar_por_evento(con, evento.id, provisional=True) == 3


def test_importar_dialog_no_escribe_hasta_confirmar(qapp, con, bingo_home, monkeypatch) -> None:
    """El requisito central del contrato §4.2: el modal de dos pasos no debe
    tocar la base hasta que el operador confirme explícitamente."""
    con, evento, cartones = _preparar(con)
    monkeypatch.setattr(modulo_vista, "Tarea", _TareaFalsa)

    dialogo = ImportarComprasDialog(con, evento)
    informe = InformeImportacion(
        correctas=[
            FilaImportacion(
                numero_fila=2, codigo=cartones[0].codigo, nombre="Ana", carton_id=cartones[0].id
            )
        ],
    )
    dialogo._validacion_terminada(informe)
    assert dialogo._boton_confirmar.isEnabled()
    # Nada se escribió todavía: solo se validó en memoria.
    assert repo_comprador.contar_por_evento(con, evento.id) == 0

    dialogo._confirmar_e_importar()
    assert isinstance(dialogo._tarea, _TareaFalsa)
    assert dialogo._tarea.iniciada
    # La Tarea falsa no corrió de verdad: sigue sin escribirse nada hasta
    # que el hilo (aquí, a mano) emite `terminado`.
    assert repo_comprador.contar_por_evento(con, evento.id) == 0

    from bingo.servicios import servicio_compradores

    resultado = servicio_compradores.aplicar_importacion(con, evento.id, informe)
    dialogo._importacion_terminada(resultado)
    assert repo_comprador.contar_por_evento(con, evento.id) == 1


def test_importar_dialog_confirmar_deshabilitado_al_primer_clic(
    qapp, con, bingo_home, monkeypatch
) -> None:
    """Hallazgo "doble clic en Confirmar" (ANEXO A del plan de la fase 4):
    el botón se deshabilita en el primer clic, antes de que la Tarea
    termine."""
    con, evento, cartones = _preparar(con)
    monkeypatch.setattr(modulo_vista, "Tarea", _TareaFalsa)

    dialogo = ImportarComprasDialog(con, evento)
    informe = InformeImportacion(
        correctas=[
            FilaImportacion(
                numero_fila=2, codigo=cartones[0].codigo, nombre="Ana", carton_id=cartones[0].id
            )
        ],
    )
    dialogo._validacion_terminada(informe)
    dialogo._confirmar_e_importar()
    assert not dialogo._boton_confirmar.isEnabled()


def test_anular_venta_pide_confirmacion(qapp, con, bingo_home, monkeypatch) -> None:
    con, evento, cartones = _preparar(con)
    from bingo.servicios import servicio_compradores

    servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Juan")
    )
    vista = VistaCompradores(con, evento)
    vista._tabla.selectRow(0)

    monkeypatch.setattr(modulo_vista, "confirmar", lambda *_a, **_k: False)
    vista._anular_seleccionado()
    assert repo_comprador.contar_por_evento(con, evento.id) == 1  # no se anuló

    monkeypatch.setattr(modulo_vista, "confirmar", lambda *_a, **_k: True)
    vista._anular_seleccionado()
    assert repo_comprador.contar_por_evento(con, evento.id) == 0
    assert repo_carton.obtener(con, cartones[0].id).estado == "impreso"


# ── Borrado de datos de compradores (tarea 4.25, LOPDP) ─────────────────────


def test_boton_eliminar_datos_deshabilitado_si_evento_no_finalizado(qapp, con, bingo_home) -> None:
    con, evento, _cartones = _preparar(con)
    vista = VistaCompradores(con, evento)
    assert not vista._boton_eliminar_datos.isEnabled()


def test_boton_eliminar_datos_habilitado_con_evento_finalizado(qapp, con, bingo_home) -> None:
    from bingo.persistencia import repo_evento

    con, evento, _cartones = _preparar(con)
    repo_evento.actualizar_estado(con, evento.id, "finalizado")
    vista = VistaCompradores(con, evento)
    assert vista._boton_eliminar_datos.isEnabled()


def test_eliminar_datos_requiere_escribir_el_nombre_exacto(
    qapp, con, bingo_home, monkeypatch
) -> None:
    from bingo.persistencia import repo_evento

    con, evento, cartones = _preparar(con)
    repo_evento.actualizar_estado(con, evento.id, "finalizado")
    from bingo.servicios import servicio_compradores

    servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Juan")
    )
    vista = VistaCompradores(con, evento)

    monkeypatch.setattr(
        modulo_vista.QInputDialog, "getText", lambda *_a, **_k: ("no coincide", True)
    )
    vista._eliminar_datos_compradores()
    assert repo_comprador.contar_por_evento(con, evento.id) == 1

    monkeypatch.setattr(
        modulo_vista.QInputDialog, "getText", lambda *_a, **_k: (evento.nombre, True)
    )
    vista._eliminar_datos_compradores()
    assert repo_comprador.contar_por_evento(con, evento.id) == 0


def test_eliminar_datos_cancelado_no_borra_nada(qapp, con, bingo_home, monkeypatch) -> None:
    from bingo.persistencia import repo_evento

    con, evento, cartones = _preparar(con)
    repo_evento.actualizar_estado(con, evento.id, "finalizado")
    from bingo.servicios import servicio_compradores

    servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Juan")
    )
    vista = VistaCompradores(con, evento)

    monkeypatch.setattr(modulo_vista.QInputDialog, "getText", lambda *_a, **_k: ("", False))
    vista._eliminar_datos_compradores()

    assert repo_comprador.contar_por_evento(con, evento.id) == 1


def test_eliminar_datos_bloqueado_si_no_esta_finalizado_aunque_se_llame_directo(
    qapp, con, bingo_home, monkeypatch
) -> None:
    """Defensivo (mismo criterio que 4.13 con "Finalizar evento"): el botón
    ya lo impide, pero el método vuelve a comprobarlo por si acaso."""
    con, evento, cartones = _preparar(con)
    from bingo.servicios import servicio_compradores

    servicio_compradores.registrar_manual(
        con, evento.id, cartones[0].codigo, Comprador(carton_id=0, nombre="Juan")
    )
    vista = VistaCompradores(con, evento)

    monkeypatch.setattr(
        modulo_vista.QInputDialog, "getText", lambda *_a, **_k: (evento.nombre, True)
    )
    vista._eliminar_datos_compradores()

    assert repo_comprador.contar_por_evento(con, evento.id) == 1
