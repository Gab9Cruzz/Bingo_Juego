"""Diálogo de empate (contrato §5.6). Lista los cartones detectados
ganadores de una ronda, agrupados por bola de detección (decisión V2:
"empate" es únicamente coincidir en la misma `extraccion.orden`; el motor
solo persiste las de la primera bola ganadora — D8 — así que en el uso
normal esto siempre muestra un único grupo).

El operador elige **uno** (los demás quedan `rechazado`) o marca varios
para **repartir** el premio entre ellos.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)

from bingo import i18n
from bingo.dominio.modelos import Ganador
from bingo.i18n import t


class DialogoEmpate(QDialog):
    def __init__(
        self, ganadores: list[Ganador], compradores_por_carton: dict[int, Any], parent=None
    ) -> None:
        super().__init__(parent)
        self.setModal(True)
        self._ganadores = ganadores
        self._compradores = compradores_por_carton

        self._etiqueta = QLabel()
        self._etiqueta.setWordWrap(True)

        self._lista = QListWidget()
        self._lista.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for ganador in ganadores:
            comprador = compradores_por_carton.get(ganador.carton_id)
            nombre = comprador.nombre if comprador is not None else "?"
            item = QListWidgetItem(f"{nombre} — bola {ganador.bola_numero}")
            item.setData(Qt.ItemDataRole.UserRole, ganador.id)
            self._lista.addItem(item)
        if ganadores:
            self._lista.item(0).setSelected(True)

        self._botones = QDialogButtonBox()
        self._boton_unico = self._botones.addButton("", QDialogButtonBox.ButtonRole.AcceptRole)
        self._boton_reparto = self._botones.addButton("", QDialogButtonBox.ButtonRole.ActionRole)
        self._boton_cancelar = self._botones.addButton(QDialogButtonBox.StandardButton.Cancel)

        self._boton_unico.clicked.connect(self._elegir_unico)
        self._boton_reparto.clicked.connect(self._elegir_reparto)

        distribucion = QVBoxLayout(self)
        distribucion.addWidget(self._etiqueta)
        distribucion.addWidget(self._lista)
        distribucion.addWidget(self._botones)

        self._resultado_unico: int | None = None
        self._resultado_reparto: list[int] | None = None

        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    def retraducir(self) -> None:
        self.setWindowTitle(t("sorteo.empate.titulo"))
        self._etiqueta.setText(t("sorteo.empate.instruccion"))
        self._boton_unico.setText(t("sorteo.empate.elegir_unico"))
        self._boton_reparto.setText(t("sorteo.empate.repartir"))
        self._boton_cancelar.setText(t("comun.cancelar"))

    def _elegir_unico(self) -> None:
        seleccionados = self._lista.selectedItems()
        if len(seleccionados) != 1:
            return
        self._resultado_unico = seleccionados[0].data(Qt.ItemDataRole.UserRole)
        self.accept()

    def _elegir_reparto(self) -> None:
        seleccionados = self._lista.selectedItems()
        if not seleccionados:
            return
        self._resultado_reparto = [item.data(Qt.ItemDataRole.UserRole) for item in seleccionados]
        self.accept()

    @property
    def id_unico(self) -> int | None:
        return self._resultado_unico

    @property
    def ids_reparto(self) -> list[int] | None:
        return self._resultado_reparto
