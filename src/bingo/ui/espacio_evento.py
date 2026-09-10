"""Espacio de trabajo del evento (enmienda E14): cabecera propia + riel de
secciones. En la fase 1 el riel tiene una sola entrada real, *Datos del
evento*; las fases 2 a 5 le cuelgan Cartones, Plantilla, Compradores, Rondas y
Transmisión apendeando a `ui.registro_vistas.SECCIONES_ESPACIO_EVENTO`, sin
tocar este archivo.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from bingo import i18n
from bingo.dominio.modelos import Evento
from bingo.i18n import t
from bingo.persistencia import repo_organizacion
from bingo.ui.registro_vistas import SECCIONES_ESPACIO_EVENTO
from bingo.ui.tema import paleta_organizacion
from bingo.utilidades.errores import ErrorBingo

_OBJETO_CHIP = {
    "borrador": "chipBorrador",
    "preparado": "chipPreparado",
    "en_curso": "chipEnCurso",
    "finalizado": "chipFinalizado",
}


class _ChipListoParaJugar(QLabel):
    """Decisión DS1 del plan de la fase 4: "¿qué falta para poder jugar?"
    respondida en la cabecera del evento, no enterrada dentro de la vista de
    rondas — clicable, despliega el detalle de
    `servicio_rondas.validar_evento_listo`."""

    def __init__(self, con: Any, evento: Evento, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.actualizar()

    def actualizar(self) -> None:
        from bingo.servicios import servicio_rondas

        try:
            pendientes = servicio_rondas.validar_evento_listo(self._con, self._evento.id)
        except ErrorBingo:
            self.setVisible(False)
            return
        bloqueantes = [p for p in pendientes if p.bloqueante]
        self._pendientes = pendientes
        if not bloqueantes:
            self.setText("✔ " + t("espacio_evento.chip.listo"))
            self.setObjectName("chipFinalizado")
        else:
            self.setText(t("espacio_evento.chip.faltan", cantidad=len(bloqueantes)))
            self.setObjectName("chipBorrador")
        self.style().unpolish(self)
        self.style().polish(self)

    def mousePressEvent(self, evento: QMouseEvent) -> None:  # noqa: N802 - override Qt
        detalle = "\n".join(f"• {t(p.clave_i18n, **p.parametros)}" for p in self._pendientes)
        if not detalle:
            detalle = "✔ " + t("espacio_evento.chip.listo")
        QMessageBox.information(self, t("espacio_evento.chip.detalle_titulo"), detalle)
        super().mousePressEvent(evento)


class EspacioEvento(QWidget):
    cerrado = Signal()

    def __init__(self, con: Any, evento: Evento, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento
        organizacion = repo_organizacion.obtener(con, evento.organizacion_id)
        self._organizacion = organizacion
        paleta = paleta_organizacion(organizacion) if organizacion else None

        self._franja_marca = QFrame()
        self._franja_marca.setFixedHeight(4)
        color = paleta.color_primario if paleta else "#1a1a2e"
        self._franja_marca.setStyleSheet(f"background-color: {color};")

        self._logo = QLabel()
        self._logo.setFixedSize(28, 28)
        self._logo.setScaledContents(True)
        if organizacion and organizacion.logo_path and Path(organizacion.logo_path).exists():
            self._logo.setPixmap(QPixmap(organizacion.logo_path))

        self._boton_volver = QPushButton()
        self._boton_volver.clicked.connect(self.cerrado.emit)
        self._etiqueta_nombre = QLabel(evento.nombre)
        self._etiqueta_fecha = QLabel(evento.fecha or "")
        self._chip_estado = QLabel(t(f"estado_evento.{evento.estado}"))
        self._chip_estado.setObjectName(_OBJETO_CHIP.get(evento.estado, "chipBorrador"))
        self._chip_listo = _ChipListoParaJugar(con, evento)
        self._boton_cerrar = QPushButton()
        self._boton_cerrar.clicked.connect(self.cerrado.emit)

        cabecera = QHBoxLayout()
        cabecera.addWidget(self._boton_volver)
        cabecera.addWidget(self._logo)
        cabecera.addWidget(self._etiqueta_nombre)
        cabecera.addWidget(self._etiqueta_fecha)
        cabecera.addWidget(self._chip_estado)
        cabecera.addWidget(self._chip_listo)
        cabecera.addStretch()
        cabecera.addWidget(self._boton_cerrar)

        self._riel = QListWidget()
        self._riel.setObjectName("navegacionEvento")
        self._riel.setFixedWidth(180)
        self._contenido = QStackedWidget()

        for entrada in SECCIONES_ESPACIO_EVENTO:
            item = QListWidgetItem()
            self._riel.addItem(item)
            if entrada.fabrica is not None:
                pagina = entrada.fabrica(con, evento)
            else:
                pagina = QLabel(t("espacio_evento.proximamente"))
                pagina.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pagina.setObjectName("etiquetaSecundaria")
            self._contenido.addWidget(pagina)
        self._riel.currentRowChanged.connect(self._contenido.setCurrentIndex)
        # Recalcula el chip al cambiar de sección: es el momento natural en
        # que el operador acaba de guardar algo en Rondas/Compradores.
        self._riel.currentRowChanged.connect(lambda _fila: self._chip_listo.actualizar())
        self._riel.setCurrentRow(0)

        cuerpo = QHBoxLayout()
        cuerpo.addWidget(self._riel)
        cuerpo.addWidget(self._contenido, stretch=1)

        distribucion = QVBoxLayout(self)
        distribucion.setContentsMargins(0, 0, 0, 0)
        distribucion.addWidget(self._franja_marca)
        distribucion.addLayout(cabecera)
        distribucion.addLayout(cuerpo, stretch=1)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    @property
    def evento(self) -> Evento:
        return self._evento

    def retraducir(self) -> None:
        self._boton_volver.setText("◀ " + t("espacio_evento.volver"))
        self._boton_cerrar.setText(t("espacio_evento.cerrar"))
        for indice, entrada in enumerate(SECCIONES_ESPACIO_EVENTO):
            texto = t(entrada.clave_i18n)
            if entrada.fabrica is None:
                texto += " ⏳"
            self._riel.item(indice).setText(texto)
