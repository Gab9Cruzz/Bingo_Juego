"""Ventana principal: dos niveles de navegación (enmienda E14).

Nivel global (Eventos, Organizaciones, Ajustes) y espacio de trabajo del
evento, abierto haciendo clic en una fila de la vista de eventos. El eje es el
evento, no la organización: `Preferencias.organizacion_activa_id` no existe,
en su lugar hay `ultimo_evento_abierto_id`.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from bingo import i18n
from bingo.config import preferencias
from bingo.dominio.modelos import Evento
from bingo.i18n import t
from bingo.ui.atajos import ATAJOS
from bingo.ui.espacio_evento import EspacioEvento
from bingo.ui.registro_vistas import REGISTRO_NAVEGACION_GLOBAL


class VentanaPrincipal(QMainWindow):
    def __init__(self, con: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._espacio_evento: EspacioEvento | None = None

        self._nav_global = QListWidget()
        self._nav_global.setObjectName("navegacionGlobal")
        self._nav_global.setFixedWidth(180)
        self._paginas_globales = QStackedWidget()
        self._vistas_globales: list[QWidget] = []
        for entrada in REGISTRO_NAVEGACION_GLOBAL:
            self._nav_global.addItem("")
            vista = entrada.fabrica(con)
            self._vistas_globales.append(vista)
            self._paginas_globales.addWidget(vista)
        self._nav_global.currentRowChanged.connect(self._paginas_globales.setCurrentIndex)

        self._vista_eventos = self._vistas_globales[0]
        self._vista_eventos.evento_abierto.connect(self.abrir_evento)
        self._vista_eventos.ir_a_organizaciones_solicitado.connect(
            lambda: self._navegar_a("nav.organizaciones")
        )
        self._vista_organizaciones = self._vistas_globales[1]
        self._vista_organizaciones.crear_primer_evento_solicitado.connect(
            self._ir_a_eventos_y_crear
        )

        pagina_nivel_global = QWidget()
        distribucion_global = QHBoxLayout(pagina_nivel_global)
        distribucion_global.setContentsMargins(0, 0, 0, 0)
        distribucion_global.addWidget(self._nav_global)
        distribucion_global.addWidget(self._paginas_globales, stretch=1)

        self._pila_principal = QStackedWidget()
        self._pila_principal.addWidget(pagina_nivel_global)
        self.setCentralWidget(self._pila_principal)

        self._nav_global.setCurrentRow(0)

        self._barra_estado = self.statusBar()

        for accion, secuencia in (
            ("navegar_eventos", 0),
            ("navegar_organizaciones", 1),
            ("navegar_ajustes", 2),
        ):
            atajo = QShortcut(QKeySequence(ATAJOS[accion]), self)
            atajo.activated.connect(lambda i=secuencia: self._nav_global.setCurrentRow(i))

        self._restaurar_geometria()
        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self._actualizar_barra_estado()

    def _navegar_a(self, clave_i18n: str) -> None:
        for indice, entrada in enumerate(REGISTRO_NAVEGACION_GLOBAL):
            if entrada.clave_i18n == clave_i18n:
                self._pila_principal.setCurrentIndex(0)
                self._nav_global.setCurrentRow(indice)
                return

    def _ir_a_eventos_y_crear(self) -> None:
        self._navegar_a("nav.eventos")
        self._vista_eventos.crear_nuevo()  # gesto explícito de la enmienda E17d

    def abrir_evento(self, evento: Evento) -> None:
        if self._espacio_evento is not None:
            self._pila_principal.removeWidget(self._espacio_evento)
            self._espacio_evento.deleteLater()
        self._espacio_evento = EspacioEvento(self._con, evento)
        self._espacio_evento.cerrado.connect(self.cerrar_evento)
        self._pila_principal.addWidget(self._espacio_evento)
        self._pila_principal.setCurrentWidget(self._espacio_evento)

        prefs = preferencias.cargar()
        prefs.ultimo_evento_abierto_id = evento.id
        preferencias.guardar(prefs)
        self._actualizar_barra_estado(evento)

    def cerrar_evento(self) -> None:
        self._pila_principal.setCurrentIndex(0)
        if self._espacio_evento is not None:
            self._pila_principal.removeWidget(self._espacio_evento)
            self._espacio_evento.deleteLater()
            self._espacio_evento = None
        self._vista_eventos.cargar()
        self._actualizar_barra_estado()

    def _actualizar_barra_estado(self, evento: Evento | None = None) -> None:
        sujeto = evento.nombre if evento is not None else t("comun.sin_evento_abierto")
        self._barra_estado.showMessage(f"{sujeto} · {t('comun.sin_cambios')}")

    def _restaurar_geometria(self) -> None:
        prefs = preferencias.cargar()
        if prefs.ventana.geometria:
            self.restoreGeometry(QByteArray.fromBase64(prefs.ventana.geometria.encode("ascii")))
        if prefs.ventana.maximizada:
            self.setWindowState(Qt.WindowState.WindowMaximized)

    def closeEvent(self, event: object) -> None:  # noqa: N802 - override Qt
        prefs = preferencias.cargar()
        prefs.ventana.geometria = bytes(self.saveGeometry().toBase64()).decode("ascii")
        prefs.ventana.maximizada = self.isMaximized()
        preferencias.guardar(prefs)
        super().closeEvent(event)

    def retraducir(self) -> None:
        self.setWindowTitle(t("app.titulo"))
        for indice, entrada in enumerate(REGISTRO_NAVEGACION_GLOBAL):
            self._nav_global.item(indice).setText(t(entrada.clave_i18n))
        self._actualizar_barra_estado(self._espacio_evento.evento if self._espacio_evento else None)
