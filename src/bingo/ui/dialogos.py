"""Tres canales de error, no uno (enmienda E22).

| Canal | Cuándo | Forma |
|---|---|---|
| En línea, junto al campo | `ErrorValidacion` | Texto bajo el campo, foco al campo |
| Franja de vista, no modal | `ErrorPersistencia` y subclases | Barra con reintento |
| Modal | Solo condiciones terminales | Diálogo con detalle copiable y ruta del log |

`ErrorBaseBloqueada` es esperado y reintentable; tratarlo como el manejador
global trataría lo inesperado es incorrecto, y en la fase 5 un modal encima de
una transmisión en vivo es un incidente.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from bingo import i18n
from bingo.i18n import t
from bingo.utilidades.errores import ErrorBingo


def marcar_error_campo(campo: QWidget, etiqueta_error: QLabel, mensaje: str) -> None:
    """Canal 1: mensaje en línea bajo el campo, foco al campo. Nunca un modal."""
    etiqueta_error.setText(mensaje)
    etiqueta_error.setVisible(True)
    campo.setProperty("error", "true")
    campo.style().unpolish(campo)
    campo.style().polish(campo)
    campo.setFocus()


def limpiar_error_campo(campo: QWidget, etiqueta_error: QLabel) -> None:
    etiqueta_error.clear()
    etiqueta_error.setVisible(False)
    campo.setProperty("error", "false")
    campo.style().unpolish(campo)
    campo.style().polish(campo)


class FranjaError(QWidget):
    """Canal 2: barra no modal en la cabecera de una vista, con reintento."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("franjaError")
        self._on_reintentar: Callable[[], None] | None = None

        distribucion = QHBoxLayout(self)
        distribucion.setContentsMargins(10, 6, 10, 6)
        self._etiqueta = QLabel(self)
        self._etiqueta.setWordWrap(True)
        self._boton_reintentar = QPushButton(self)
        self._boton_reintentar.clicked.connect(self._reintentar)
        distribucion.addWidget(self._etiqueta, stretch=1)
        distribucion.addWidget(self._boton_reintentar)
        self.setProperty("_frame_objname", "franjaError")
        self.hide()

        i18n.registrar_para_retraduccion(self)

    def _reintentar(self) -> None:
        if self._on_reintentar is not None:
            self._on_reintentar()

    def mostrar(self, mensaje: str, on_reintentar: Callable[[], None] | None = None) -> None:
        self._etiqueta.setText(mensaje)
        self._on_reintentar = on_reintentar
        self._boton_reintentar.setVisible(on_reintentar is not None)
        self.show()

    def mostrar_error(
        self, error: ErrorBingo, on_reintentar: Callable[[], None] | None = None
    ) -> None:
        self.mostrar(t(error.clave_i18n, **error.parametros), on_reintentar)

    def ocultar(self) -> None:
        self.hide()

    def retraducir(self) -> None:
        self._boton_reintentar.setText(t("comun.reintentar"))


def mostrar_error_modal(
    padre: QWidget | None, titulo_clave: str, mensaje_clave: str, *, detalle: str, ruta_log: str
) -> None:
    """Canal 3: solo condiciones terminales (migración fallida, base corrupta, sin permisos)."""
    caja = QMessageBox(padre)
    caja.setIcon(QMessageBox.Icon.Critical)
    caja.setWindowTitle(t(titulo_clave))
    caja.setText(t(mensaje_clave))
    caja.setInformativeText(t("error.ruta_log", ruta=ruta_log))
    caja.setDetailedText(detalle)
    boton_copiar = caja.addButton(t("comun.copiar_detalle"), QMessageBox.ButtonRole.ActionRole)

    def _copiar() -> None:
        QApplication.clipboard().setText(detalle)

    boton_copiar.clicked.connect(_copiar)
    caja.addButton(QMessageBox.StandardButton.Ok)
    caja.exec()


def confirmar(padre: QWidget | None, titulo: str, mensaje: str) -> bool:
    respuesta = QMessageBox.question(
        padre,
        titulo,
        mensaje,
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return respuesta == QMessageBox.StandardButton.Yes
