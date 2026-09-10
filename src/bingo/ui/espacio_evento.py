"""Espacio de trabajo del evento (enmienda E14): cabecera propia + riel de
secciones. En la fase 1 el riel tiene una sola entrada real, *Datos del
evento*; las fases 2 a 5 le cuelgan Cartones, Plantilla, Compradores, Rondas y
Transmisión apendeando a `ui.registro_vistas.SECCIONES_ESPACIO_EVENTO`, sin
tocar este archivo.
"""

from __future__ import annotations

import secrets
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
from bingo.persistencia import repo_organizacion, repo_ronda
from bingo.servicios.servicio_sorteo import MotorSorteo
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
        self._boton_volver.clicked.connect(self._pedir_cierre)
        self._etiqueta_nombre = QLabel(evento.nombre)
        self._etiqueta_fecha = QLabel(evento.fecha or "")
        self._chip_estado = QLabel(t(f"estado_evento.{evento.estado}"))
        self._chip_estado.setObjectName(_OBJETO_CHIP.get(evento.estado, "chipBorrador"))
        self._chip_listo = _ChipListoParaJugar(con, evento)
        self._boton_cerrar = QPushButton()
        self._boton_cerrar.clicked.connect(self._pedir_cierre)

        cabecera = QHBoxLayout()
        cabecera.addWidget(self._boton_volver)
        cabecera.addWidget(self._logo)
        cabecera.addWidget(self._etiqueta_nombre)
        cabecera.addWidget(self._etiqueta_fecha)
        cabecera.addWidget(self._chip_estado)
        cabecera.addWidget(self._chip_listo)
        cabecera.addStretch()
        cabecera.addWidget(self._boton_cerrar)
        self._cabecera = cabecera

        # Dueño del motor de sorteo (hallazgo S5-3): vive aquí, no en
        # VistaSorteo — cambiar de sección del riel a mitad de ronda no
        # puede destruir la partida. `secrets.SystemRandom()` en producción
        # (mismo convenio que `dominio/carton.py`/`dominio/bombo.py`).
        self.motor_sorteo = MotorSorteo(rng=secrets.SystemRandom())
        # Decisión DU-12: bandera simple, sin estado global de módulo.
        self.modo_vivo = False

        self._riel = QListWidget()
        self._riel.setObjectName("navegacionEvento")
        self._riel.setFixedWidth(180)
        self._contenido = QStackedWidget()

        # Decisión D10: encabezado de grupo no seleccionable antes de la
        # primera entrada de cada grupo nuevo. `self._filas_riel[i]` es
        # `("encabezado", grupo)` o `("seccion", entrada)` — una sola fuente
        # para construir el riel y para `retraducir()`, sin recalcular nada.
        self._filas_riel: list[tuple[str, Any]] = []
        grupo_anterior: str | None = None
        for entrada in SECCIONES_ESPACIO_EVENTO:
            if entrada.grupo != grupo_anterior:
                self._filas_riel.append(("encabezado", entrada.grupo))
                grupo_anterior = entrada.grupo
            self._filas_riel.append(("seccion", entrada))

        self._indices_widget: list[int] = []
        for fila, (tipo, valor) in enumerate(self._filas_riel):
            if tipo == "encabezado":
                item = QListWidgetItem()
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self._riel.addItem(item)
                continue
            entrada = valor
            item = QListWidgetItem()
            self._riel.addItem(item)
            self._indices_widget.append(fila)
            if entrada.fabrica is not None:
                pagina = entrada.fabrica(con, evento, self)
            else:
                pagina = QLabel(t("espacio_evento.proximamente"))
                pagina.setAlignment(Qt.AlignmentFlag.AlignCenter)
                pagina.setObjectName("etiquetaSecundaria")
            self._contenido.addWidget(pagina)
        self._riel.currentRowChanged.connect(self._al_cambiar_fila_riel)
        self._riel.setCurrentRow(self._indices_widget[0] if self._indices_widget else 0)

        cuerpo = QHBoxLayout()
        cuerpo.addWidget(self._riel)
        cuerpo.addWidget(self._contenido, stretch=1)
        self._cuerpo = cuerpo

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

    def _al_cambiar_fila_riel(self, fila: int) -> None:
        # Las filas de encabezado de grupo no son seleccionables
        # (`NoItemFlags`), pero por si algún día cambia, se ignoran aquí
        # también en vez de intentar mostrar una página que no existe.
        if fila in self._indices_widget:
            self._contenido.setCurrentIndex(self._indices_widget.index(fila))
        # Recalcula el chip al cambiar de sección: es el momento natural en
        # que el operador acaba de guardar algo en Rondas/Compradores.
        self._chip_listo.actualizar()

    def hay_ronda_viva(self) -> bool:
        """Decisión DU-11: hay algo que un cierre destruiría sin avisar."""
        return repo_ronda.obtener_en_juego(self._con, self._evento.id) is not None

    def _pedir_cierre(self) -> None:
        if self.hay_ronda_viva() and not self._confirmar_cierre_con_ronda_viva():
            return
        self.cerrado.emit()

    def _confirmar_cierre_con_ronda_viva(self) -> bool:
        from bingo.ui.dialogos import confirmar

        return confirmar(
            self,
            t("espacio_evento.confirmar_cierre.titulo"),
            t("espacio_evento.confirmar_cierre.mensaje"),
        )

    def activar_modo_vivo(self) -> None:
        """Decisión D9/DU-12: oculta riel y cabecera, deja la pantalla
        entera al juego. Franjas de error/éxito y diálogos de empate/reclamo
        siguen visibles — solo se ocultan el cromo de navegación y la marca
        de la organización."""
        self.modo_vivo = True
        self._franja_marca.setVisible(False)
        for indice in range(self._cabecera.count()):
            widget = self._cabecera.itemAt(indice).widget()
            if widget is not None:
                widget.setVisible(False)
        self._riel.setVisible(False)

    def desactivar_modo_vivo(self) -> None:
        self.modo_vivo = False
        self._franja_marca.setVisible(True)
        for indice in range(self._cabecera.count()):
            widget = self._cabecera.itemAt(indice).widget()
            if widget is not None:
                widget.setVisible(True)
        self._riel.setVisible(True)

    def retraducir(self) -> None:
        self._boton_volver.setText("◀ " + t("espacio_evento.volver"))
        self._boton_cerrar.setText(t("espacio_evento.cerrar"))
        for fila, (tipo, valor) in enumerate(self._filas_riel):
            item = self._riel.item(fila)
            if tipo == "encabezado":
                item.setText(t(f"espacio_evento.grupo.{valor}"))
                continue
            entrada = valor
            texto = t(entrada.clave_i18n)
            if entrada.fabrica is None:
                texto += " ⏳"
            item.setText(texto)
