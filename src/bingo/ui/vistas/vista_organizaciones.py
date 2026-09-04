"""Vista de organizaciones: rejilla de tarjetas (enmienda E17), no lista-detalle.

Una organización tiene entre cinco y quince filas en toda la vida de la
aplicación y su razón de ser es la identidad visual: se reconoce a un cliente
por su marca, no por una etiqueta de texto.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from bingo import i18n
from bingo.dominio.modelos import Organizacion
from bingo.i18n import t
from bingo.persistencia import repo_organizacion
from bingo.servicios import servicio_organizaciones
from bingo.ui.dialogos import (
    FranjaError,
    confirmar,
    limpiar_error_campo,
    marcar_error_campo,
)
from bingo.ui.tema import paleta_organizacion
from bingo.utilidades.errores import ErrorBingo, ErrorValidacion

_TIPOGRAFIAS = [
    ("", "organizaciones.tipografia.predeterminada"),
    ("Merriweather", "Merriweather"),
    ("Open Sans", "Open Sans"),
]


def _muestra_color(color: str) -> QLabel:
    etiqueta = QLabel()
    etiqueta.setFixedSize(20, 20)
    etiqueta.setStyleSheet(f"background-color: {color}; border-radius: 4px;")
    return etiqueta


class BotonColor(QPushButton):
    def __init__(self, color_inicial: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.color = color_inicial
        self.setFixedWidth(90)
        self._actualizar()
        self.clicked.connect(self._elegir)

    def _actualizar(self) -> None:
        self.setText(self.color)
        self.setStyleSheet(f"background-color: {self.color}; color: white;")

    def _elegir(self) -> None:
        from PySide6.QtGui import QColor

        color = QColorDialog.getColor(QColor(self.color), self, "")
        if color.isValid():
            self.color = color.name()
            self._actualizar()


class FormularioOrganizacion(QDialog):
    def __init__(
        self, con: Any, organizacion: Organizacion | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self._con = con
        self._organizacion = organizacion
        self._logo_origen: Path | None = None
        self.setMinimumWidth(420)

        self._campo_nombre = QLineEdit(organizacion.nombre if organizacion else "")
        self._error_nombre = QLabel()
        self._error_nombre.setStyleSheet("color: #e5484d;")
        self._error_nombre.setVisible(False)
        self._campo_contacto = QLineEdit(organizacion.contacto if organizacion else "")

        self._etiqueta_logo = QLabel()
        self._etiqueta_logo.setFixedSize(64, 64)
        self._etiqueta_logo.setScaledContents(True)
        self._actualizar_previa_logo(organizacion.logo_path if organizacion else None)
        self._boton_logo = QPushButton()
        self._boton_logo.clicked.connect(self._cargar_logo)

        self._campo_eslogan = QLineEdit(organizacion.eslogan if organizacion else "")
        self._campo_pie = QLineEdit(organizacion.pie_pagina if organizacion else "")
        self._campo_condiciones = QLineEdit(organizacion.condiciones if organizacion else "")
        self._campo_aviso = QLineEdit(organizacion.aviso_legal if organizacion else "")
        self._color_primario = BotonColor(
            organizacion.color_primario if organizacion else "#1a1a2e"
        )
        self._color_secundario = BotonColor(
            organizacion.color_secundario if organizacion else "#e94560"
        )
        self._color_texto = BotonColor(organizacion.color_texto if organizacion else "#ffffff")
        self._combo_tipografia = QComboBox()
        for valor, _clave in _TIPOGRAFIAS:
            self._combo_tipografia.addItem(valor, valor)
        if organizacion and organizacion.tipografia:
            indice = self._combo_tipografia.findData(organizacion.tipografia)
            if indice >= 0:
                self._combo_tipografia.setCurrentIndex(indice)

        self._etiqueta_contraste = QLabel()
        self._etiqueta_contraste.setWordWrap(True)
        self._etiqueta_contraste.setVisible(False)

        self._grupo_identidad = QGroupBox()
        self._grupo_identidad.setCheckable(True)
        self._grupo_identidad.setChecked(bool(organizacion and organizacion.logo_path))
        formulario_identidad = QFormLayout()
        formulario_identidad.addRow(self._boton_logo, self._etiqueta_logo)
        formulario_identidad.addRow(self._campo_eslogan)
        formulario_identidad.addRow(self._campo_pie)
        formulario_identidad.addRow(self._campo_condiciones)
        formulario_identidad.addRow(self._campo_aviso)
        formulario_identidad.addRow(self._color_primario, self._color_secundario)
        formulario_identidad.addRow(self._color_texto, self._combo_tipografia)
        formulario_identidad.addRow(self._etiqueta_contraste)
        self._grupo_identidad.setLayout(formulario_identidad)

        self._formulario = QFormLayout()
        self._formulario.addRow(self._campo_nombre)
        self._formulario.addRow(self._error_nombre)
        self._formulario.addRow(self._campo_contacto)

        self._error_general = QLabel()
        self._error_general.setStyleSheet("color: #e5484d;")
        self._error_general.setWordWrap(True)
        self._error_general.setVisible(False)

        self._botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._botones.accepted.connect(self._guardar)
        self._botones.rejected.connect(self.reject)

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(self._formulario)
        distribucion.addWidget(self._grupo_identidad)
        distribucion.addWidget(self._error_general)
        distribucion.addWidget(self._botones)

        self.setTabOrder(self._campo_nombre, self._campo_contacto)
        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self._campo_nombre.setFocus()

    def _actualizar_previa_logo(self, ruta: str | None) -> None:
        if ruta and Path(ruta).exists():
            self._etiqueta_logo.setPixmap(QPixmap(ruta))
        else:
            self._etiqueta_logo.clear()
            self._etiqueta_logo.setText("—")
            self._etiqueta_logo.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _cargar_logo(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, t("organizaciones.logo.cargar"), "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if not ruta:
            return
        self._logo_origen = Path(ruta)
        self._etiqueta_logo.setPixmap(QPixmap(ruta))

    def _datos_formulario(self) -> Organizacion:
        base = self._organizacion or Organizacion(nombre="")
        return Organizacion(
            id=base.id,
            nombre=self._campo_nombre.text().strip(),
            logo_path=base.logo_path,
            logo_secundario=base.logo_secundario,
            color_primario=self._color_primario.color,
            color_secundario=self._color_secundario.color,
            color_texto=self._color_texto.color,
            tipografia=self._combo_tipografia.currentData() or None,
            contacto=self._campo_contacto.text().strip() or None,
            eslogan=self._campo_eslogan.text().strip() or None,
            pie_pagina=self._campo_pie.text().strip() or None,
            condiciones=self._campo_condiciones.text().strip() or None,
            aviso_legal=self._campo_aviso.text().strip() or None,
            creada_en=base.creada_en,
        )

    def _guardar(self) -> None:
        limpiar_error_campo(self._campo_nombre, self._error_nombre)
        self._error_general.setVisible(False)
        datos = self._datos_formulario()

        paleta = paleta_organizacion(datos)
        if not paleta.contraste_ok:
            self._etiqueta_contraste.setText(t("organizaciones.contraste.aviso"))
            self._etiqueta_contraste.setVisible(True)
        else:
            self._etiqueta_contraste.setVisible(False)

        try:
            if self._organizacion is None:
                self.resultado = servicio_organizaciones.crear_organizacion(
                    self._con, datos, self._logo_origen
                )
            else:
                self.resultado = servicio_organizaciones.actualizar_organizacion(
                    self._con, datos, self._logo_origen
                )
        except ErrorValidacion as error:
            marcar_error_campo(self._campo_nombre, self._error_nombre, t(error.clave_i18n))
            return
        except ErrorBingo as error:
            self._error_general.setText(t(error.clave_i18n, **error.parametros))
            self._error_general.setVisible(True)
            return

        self.accept()

    def retraducir(self) -> None:
        self.setWindowTitle(
            t("organizaciones.formulario.titulo_editar")
            if self._organizacion
            else t("organizaciones.formulario.titulo_nuevo")
        )
        self._formulario.labelForField(self._campo_nombre)
        self._campo_nombre.setPlaceholderText(t("organizaciones.campo.nombre"))
        self._campo_contacto.setPlaceholderText(t("organizaciones.campo.contacto"))
        self._campo_eslogan.setPlaceholderText(t("organizaciones.campo.eslogan"))
        self._campo_pie.setPlaceholderText(t("organizaciones.campo.pie_pagina"))
        self._campo_condiciones.setPlaceholderText(t("organizaciones.campo.condiciones"))
        self._campo_aviso.setPlaceholderText(t("organizaciones.campo.aviso_legal"))
        self._boton_logo.setText(t("organizaciones.logo.cargar"))
        self._grupo_identidad.setTitle(t("organizaciones.seccion.identidad_visual"))
        self._botones.button(QDialogButtonBox.StandardButton.Save).setText(t("comun.guardar"))
        self._botones.button(QDialogButtonBox.StandardButton.Cancel).setText(t("comun.cancelar"))


class TarjetaOrganizacion(QFrame):
    clicada = Signal()

    def __init__(
        self, org: Organizacion, cantidad_eventos: int, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("tarjetaOrganizacion")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(220, 160)
        distribucion = QVBoxLayout(self)

        logo = QLabel()
        logo.setFixedSize(48, 48)
        logo.setScaledContents(True)
        if org.logo_path and Path(org.logo_path).exists():
            logo.setPixmap(QPixmap(org.logo_path))
        else:
            logo.setText("—")
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        distribucion.addWidget(logo)

        nombre = QLabel(org.nombre)
        nombre.setWordWrap(True)
        distribucion.addWidget(nombre)

        colores = QHBoxLayout()
        colores.addWidget(_muestra_color(org.color_primario))
        colores.addWidget(_muestra_color(org.color_secundario))
        colores.addWidget(_muestra_color(org.color_texto))
        colores.addStretch()
        distribucion.addLayout(colores)

        self._etiqueta_eventos = QLabel(
            t("organizaciones.eventos_contador", cantidad=cantidad_eventos)
        )
        self._etiqueta_eventos.setObjectName("etiquetaSecundaria")
        distribucion.addWidget(self._etiqueta_eventos)
        distribucion.addStretch()

    def mousePressEvent(self, event: object) -> None:  # noqa: N802 - override Qt
        self.clicada.emit()


class VistaOrganizaciones(QWidget):
    crear_primer_evento_solicitado = Signal()

    def __init__(self, con: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con

        self._titulo = QLabel()
        self._boton_nueva = QPushButton()
        self._boton_nueva.setObjectName("primario")
        self._boton_nueva.clicked.connect(self._nueva)

        cabecera = QHBoxLayout()
        cabecera.addWidget(self._titulo, stretch=1)
        cabecera.addWidget(self._boton_nueva)

        self._franja = FranjaError()

        self._contenedor_rejilla = QWidget()
        self._rejilla = QGridLayout(self._contenedor_rejilla)
        self._rejilla.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(self._contenedor_rejilla)

        self._etiqueta_vacio = QLabel()
        self._etiqueta_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._etiqueta_vacio.setVisible(False)

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(cabecera)
        distribucion.addWidget(self._franja)
        distribucion.addWidget(self._etiqueta_vacio)
        distribucion.addWidget(area, stretch=1)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self.cargar()

    def cargar(self) -> None:
        self._franja.ocultar()
        try:
            organizaciones = repo_organizacion.listar(self._con)
        except ErrorBingo as error:
            self._franja.mostrar_error(error, on_reintentar=self.cargar)
            return

        while self._rejilla.count():
            item = self._rejilla.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._etiqueta_vacio.setVisible(len(organizaciones) == 0)
        self._etiqueta_vacio.setText(t("organizaciones.vacio.titulo"))

        for indice, org in enumerate(organizaciones):
            cantidad = repo_organizacion.contar_eventos(self._con, org.id)
            tarjeta = TarjetaOrganizacion(org, cantidad, self._contenedor_rejilla)
            tarjeta.clicada.connect(lambda o=org: self._editar(o))
            self._rejilla.addWidget(tarjeta, indice // 4, indice % 4)

    def _nueva(self) -> None:
        habia_organizaciones = len(repo_organizacion.listar(self._con)) > 0
        dialogo = FormularioOrganizacion(self._con, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.cargar()
            if not habia_organizaciones and confirmar(
                self,
                t("organizaciones.exito.primera.titulo"),
                t("organizaciones.exito.primera.boton"),
            ):
                self.crear_primer_evento_solicitado.emit()

    def _editar(self, org: Organizacion) -> None:
        dialogo = FormularioOrganizacion(self._con, organizacion=org, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.cargar()

    def retraducir(self) -> None:
        self._titulo.setText(t("organizaciones.titulo"))
        self._boton_nueva.setText(t("organizaciones.nuevo"))
        self._etiqueta_vacio.setText(t("organizaciones.vacio.titulo"))
