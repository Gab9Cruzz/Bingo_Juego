"""G18: la justificación entera de la enmienda E20. El registro de
retraducción es un `weakref.WeakSet` con baja explícita en `destroyed`; sin
eso, cambiar de idioma después de destruir una segunda ventana de nivel
superior (la de transmisión, en la fase 5) lanza
`RuntimeError: Internal C++ object already deleted`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget

from bingo import i18n
from bingo.i18n import t


class _VentanaDePrueba(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.etiqueta = QLabel(self)
        i18n.registrar_para_retraduccion(self)

    def retraducir(self) -> None:
        self.etiqueta.setText(t("comun.guardar"))


def test_segunda_ventana_destruida_no_revienta_retraduccion(qapp) -> None:
    i18n.cargar("es")

    ventana = _VentanaDePrueba()
    assert ventana.etiqueta.text() == "Guardar"

    ventana.deleteLater()
    qapp.processEvents()  # fuerza la destrucción real del objeto C++ ahora

    # Sin la baja explícita en `destroyed`, esto lanzaría RuntimeError.
    i18n.cargar("en")


def test_widget_vivo_se_retraduce_normalmente(qapp) -> None:
    i18n.cargar("es")
    ventana = _VentanaDePrueba()
    i18n.cargar("en")
    assert ventana.etiqueta.text() == "Save"
    ventana.deleteLater()
    qapp.processEvents()
