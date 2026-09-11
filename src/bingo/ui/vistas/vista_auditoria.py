"""Sección "Auditoría" del espacio de trabajo del evento (tarea 4.19 de la
fase 5, expansión E3 — cierra una deuda de la fase 4: `repo_auditoria`
existía desde entonces sin ninguna pantalla que lo leyera).

De solo lectura a propósito (decisión implícita del propio plan: "panel de
auditoría", no "editor de auditoría") — es la respuesta de la Sección 8
(observabilidad) del alcance a "un problema reportado tres semanas después,
¿se puede reconstruir?", y una fila editable dejaría de ser un rastro fiable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bingo import i18n
from bingo.i18n import t
from bingo.servicios import servicio_auditoria
from bingo.ui.dialogos import FranjaError
from bingo.utilidades.errores import ErrorBingo

_COLUMNAS = ("momento", "accion", "detalle")


class VistaAuditoria(QWidget):
    def __init__(self, con: Any, evento: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento

        self._franja = FranjaError()
        self._titulo = QLabel()

        self._campo_filtro = QLineEdit()
        self._campo_filtro.textChanged.connect(self.cargar)
        self._boton_exportar = QPushButton()
        self._boton_exportar.clicked.connect(self._exportar)
        fila_filtro = QHBoxLayout()
        fila_filtro.addWidget(self._campo_filtro, stretch=1)
        fila_filtro.addWidget(self._boton_exportar)

        self._tabla = QTableWidget(0, len(_COLUMNAS))
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tabla.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self._tabla.verticalHeader().setVisible(False)

        distribucion = QVBoxLayout(self)
        distribucion.addWidget(self._franja)
        distribucion.addWidget(self._titulo)
        distribucion.addLayout(fila_filtro)
        distribucion.addWidget(self._tabla, stretch=1)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self.cargar()

    def cargar(self) -> None:
        self._franja.ocultar()
        prefijo = self._campo_filtro.text().strip() or None
        registros = servicio_auditoria.listar(self._con, self._evento.id, prefijo=prefijo)
        self._tabla.setRowCount(len(registros))
        for fila, registro in enumerate(registros):
            valores = (registro.momento, registro.accion, registro.detalle or "")
            for columna, valor in enumerate(valores):
                item = QTableWidgetItem(valor)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._tabla.setItem(fila, columna, item)

    def _textos_reporte(self) -> dict[str, str]:
        return {
            "hoja": t("auditoria.hoja"),
            "columna_momento": t("auditoria.columna.momento"),
            "columna_accion": t("auditoria.columna.accion"),
            "columna_detalle": t("auditoria.columna.detalle"),
        }

    def _exportar(self) -> None:
        ruta, _filtro = QFileDialog.getSaveFileName(
            self, "", f"auditoria-{self._evento.nombre}.xlsx", "Excel (*.xlsx)"
        )
        if not ruta:
            return
        prefijo = self._campo_filtro.text().strip() or None
        try:
            servicio_auditoria.generar_reporte_excel(
                self._con, self._evento.id, Path(ruta), self._textos_reporte(), prefijo=prefijo
            )
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._franja.mostrar_exito(t("auditoria.exito.exportado", ruta=ruta))

    def retraducir(self) -> None:
        self._titulo.setText(t("auditoria.titulo"))
        self._campo_filtro.setPlaceholderText(t("auditoria.filtro.placeholder"))
        self._boton_exportar.setText(t("auditoria.accion.exportar"))
        self._tabla.setHorizontalHeaderLabels(
            [
                t("auditoria.columna.momento"),
                t("auditoria.columna.accion"),
                t("auditoria.columna.detalle"),
            ]
        )
