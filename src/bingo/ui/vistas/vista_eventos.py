"""Vista de eventos: pantalla de inicio de la aplicación (enmienda E18).

Lista TODOS los eventos de todas las organizaciones; el filtro por
organización es un filtro, no un modo global (enmienda E14). Hacer clic en una
fila abre su espacio de trabajo (enmienda E18b): en las fases 2 a 5 ese clic es
el gesto principal de la aplicación.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from bingo import i18n
from bingo.dominio.dinero import a_centavos
from bingo.dominio.modelos import Evento, Organizacion
from bingo.i18n import t
from bingo.persistencia import repo_evento, repo_organizacion
from bingo.servicios import servicio_eventos
from bingo.ui.dialogos import FranjaError, limpiar_error_campo, marcar_error_campo
from bingo.utilidades.errores import ErrorBingo, ErrorValidacion


class FormularioEvento(QDialog):
    def __init__(self, con: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self.setMinimumWidth(380)

        self._combo_organizacion = QComboBox()
        for org in repo_organizacion.listar(con):
            self._combo_organizacion.addItem(org.nombre, org.id)

        self._campo_nombre = QLineEdit()
        self._error_nombre = QLabel()
        self._error_nombre.setStyleSheet("color: #e5484d;")
        self._error_nombre.setVisible(False)
        self._aviso_duplicado = QLabel()
        self._aviso_duplicado.setStyleSheet("color: #e2a33d;")
        self._aviso_duplicado.setVisible(False)

        self._campo_fecha = QDateEdit()
        self._campo_fecha.setCalendarPopup(True)
        self._campo_fecha.setDate(QDate.currentDate())

        self._casilla_hora = QCheckBox()
        self._campo_hora = QTimeEdit()
        self._campo_hora.setDisplayFormat("HH:mm")
        self._campo_hora.setEnabled(False)
        self._casilla_hora.toggled.connect(self._campo_hora.setEnabled)

        self._campo_lugar = QLineEdit()

        self._campo_precio = QDoubleSpinBox()
        self._campo_precio.setDecimals(2)
        self._campo_precio.setMaximum(999999.99)
        self._campo_precio.setPrefix("$ ")
        self._error_precio = QLabel()
        self._error_precio.setStyleSheet("color: #e5484d;")
        self._error_precio.setVisible(False)

        self._formulario = QFormLayout()
        self._etiqueta_organizacion = QLabel()
        self._etiqueta_nombre = QLabel()
        self._etiqueta_fecha = QLabel()
        self._etiqueta_hora = QLabel()
        self._etiqueta_lugar = QLabel()
        self._etiqueta_precio = QLabel()
        self._formulario.addRow(self._etiqueta_organizacion, self._combo_organizacion)
        self._formulario.addRow(self._etiqueta_nombre, self._campo_nombre)
        self._formulario.addRow(self._error_nombre)
        self._formulario.addRow(self._aviso_duplicado)
        self._formulario.addRow(self._etiqueta_fecha, self._campo_fecha)
        fila_hora = QHBoxLayout()
        fila_hora.addWidget(self._casilla_hora)
        fila_hora.addWidget(self._campo_hora)
        self._formulario.addRow(self._etiqueta_hora, fila_hora)
        self._formulario.addRow(self._etiqueta_lugar, self._campo_lugar)
        self._formulario.addRow(self._etiqueta_precio, self._campo_precio)
        self._formulario.addRow(self._error_precio)

        self._botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._botones.accepted.connect(self._guardar)
        self._botones.rejected.connect(self.reject)

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(self._formulario)
        distribucion.addWidget(self._botones)

        self._campo_nombre.textChanged.connect(self._revisar_duplicado)
        self._combo_organizacion.currentIndexChanged.connect(self._revisar_duplicado)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self._campo_nombre.setFocus()

    def _revisar_duplicado(self) -> None:
        org_id = self._combo_organizacion.currentData()
        nombre = self._campo_nombre.text().strip()
        if org_id is None or not nombre:
            self._aviso_duplicado.setVisible(False)
            return
        if repo_evento.existe_nombre(self._con, org_id, nombre):
            self._aviso_duplicado.setText(t("eventos.aviso.nombre_duplicado", nombre=nombre))
            self._aviso_duplicado.setVisible(True)
        else:
            self._aviso_duplicado.setVisible(False)

    def _guardar(self) -> None:
        limpiar_error_campo(self._campo_nombre, self._error_nombre)
        limpiar_error_campo(self._campo_precio, self._error_precio)

        org_id = self._combo_organizacion.currentData()
        if org_id is None:
            marcar_error_campo(
                self._combo_organizacion,
                self._error_nombre,
                t("eventos.error.organizacion_requerida"),
            )
            return

        hora = self._campo_hora.time().toString("HH:mm") if self._casilla_hora.isChecked() else None
        evento = Evento(
            organizacion_id=org_id,
            nombre=self._campo_nombre.text().strip(),
            fecha=self._campo_fecha.date().toString("yyyy-MM-dd"),
            hora=hora,
            lugar=self._campo_lugar.text().strip() or None,
            precio_tabla_centavos=a_centavos(f"{self._campo_precio.value():.2f}"),
        )

        try:
            self.resultado = servicio_eventos.crear_evento(self._con, evento)
        except ErrorValidacion as error:
            if error.campo == "precio_tabla_centavos":
                marcar_error_campo(self._campo_precio, self._error_precio, t(error.clave_i18n))
            else:
                marcar_error_campo(self._campo_nombre, self._error_nombre, t(error.clave_i18n))
            return

        self.accept()

    def retraducir(self) -> None:
        self.setWindowTitle(t("eventos.formulario.titulo_nuevo"))
        self._etiqueta_organizacion.setText(t("eventos.campo.organizacion"))
        self._etiqueta_nombre.setText(t("eventos.campo.nombre"))
        self._etiqueta_fecha.setText(t("eventos.campo.fecha"))
        self._etiqueta_hora.setText(t("eventos.campo.hora"))
        self._casilla_hora.setText(f"({t('comun.opcional')})")
        self._etiqueta_lugar.setText(t("eventos.campo.lugar"))
        self._etiqueta_precio.setText(t("eventos.campo.precio"))
        self._botones.button(QDialogButtonBox.StandardButton.Save).setText(t("comun.guardar"))
        self._botones.button(QDialogButtonBox.StandardButton.Cancel).setText(t("comun.cancelar"))


class VistaEventos(QWidget):
    evento_abierto = Signal(object)
    ir_a_organizaciones_solicitado = Signal()

    def __init__(self, con: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._organizaciones: dict[int, Organizacion] = {}

        self._titulo = QLabel()
        self._campo_busqueda = QLineEdit()
        self._campo_busqueda.textChanged.connect(self.cargar)
        self._boton_nuevo = QPushButton()
        self._boton_nuevo.setObjectName("primario")
        self._boton_nuevo.clicked.connect(self._nuevo)

        cabecera = QHBoxLayout()
        cabecera.addWidget(self._titulo)
        cabecera.addWidget(self._campo_busqueda, stretch=1)
        cabecera.addWidget(self._boton_nuevo)

        self._franja = FranjaError()

        self._lista = QListWidget()
        self._lista.itemActivated.connect(self._abrir_item)
        self._lista.itemClicked.connect(self._abrir_item)

        self._etiqueta_vacio = QLabel()
        self._etiqueta_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._etiqueta_vacio.setVisible(False)
        self._boton_vacio = QPushButton()
        self._boton_vacio.setVisible(False)
        self._boton_vacio.clicked.connect(self._accion_vacio)

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(cabecera)
        distribucion.addWidget(self._franja)
        distribucion.addWidget(self._etiqueta_vacio)
        distribucion.addWidget(self._boton_vacio, alignment=Qt.AlignmentFlag.AlignCenter)
        distribucion.addWidget(self._lista, stretch=1)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self.cargar()

    def _accion_vacio(self) -> None:
        if not self._organizaciones:
            self.ir_a_organizaciones_solicitado.emit()
        else:
            self._campo_busqueda.clear()

    def cargar(self) -> None:
        self._franja.ocultar()
        try:
            self._organizaciones = {o.id: o for o in repo_organizacion.listar(self._con)}
            eventos = repo_evento.listar_todos(self._con)
        except ErrorBingo as error:
            self._franja.mostrar_error(error, on_reintentar=self.cargar)
            return

        texto_busqueda = self._campo_busqueda.text().strip().lower()
        if texto_busqueda:
            eventos = [
                e
                for e in eventos
                if texto_busqueda in e.nombre.lower()
                or texto_busqueda
                in (
                    self._organizaciones.get(e.organizacion_id).nombre.lower()
                    if e.organizacion_id in self._organizaciones
                    else ""
                )
                or texto_busqueda in t(f"estado_evento.{e.estado}").lower()
                or (e.fecha and texto_busqueda in e.fecha)
            ]

        self._lista.clear()
        sin_organizaciones = len(self._organizaciones) == 0
        sin_eventos = len(eventos) == 0

        self._etiqueta_vacio.setVisible(sin_eventos)
        self._boton_vacio.setVisible(sin_eventos)
        if sin_organizaciones:
            self._etiqueta_vacio.setText(t("eventos.vacio.sin_organizaciones.titulo"))
            self._boton_vacio.setText(t("eventos.vacio.sin_organizaciones.boton"))
        elif texto_busqueda:
            self._etiqueta_vacio.setText(t("eventos.vacio.filtro", texto=texto_busqueda))
            self._boton_vacio.setText(t("comun.limpiar_filtro"))
        else:
            self._etiqueta_vacio.setText(t("eventos.vacio.con_organizaciones"))
            self._boton_vacio.setVisible(False)

        for evento in eventos:
            org = self._organizaciones.get(evento.organizacion_id)
            nombre_org = org.nombre if org else "?"
            estado = t(f"estado_evento.{evento.estado}")
            texto = f"{evento.nombre}  ·  {nombre_org}  ·  {evento.fecha or '—'}  ·  {estado}"
            item = QListWidgetItem(texto)
            if org and org.logo_path and Path(org.logo_path).exists():
                item.setIcon(QPixmap(org.logo_path).scaled(32, 32))
            item.setData(Qt.ItemDataRole.UserRole, evento)
            self._lista.addItem(item)

    def _abrir_item(self, item: QListWidgetItem) -> None:
        evento = item.data(Qt.ItemDataRole.UserRole)
        if evento is not None:
            self.evento_abierto.emit(evento)

    def crear_nuevo(self) -> None:
        """Punto de entrada público: abre el formulario de alta (usado también
        desde `ventana_principal` tras crear la primera organización, E17d).
        """
        self._nuevo()

    def _nuevo(self) -> None:
        if not repo_organizacion.listar(self._con):
            self.ir_a_organizaciones_solicitado.emit()
            return
        dialogo = FormularioEvento(self._con, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self.cargar()

    def retraducir(self) -> None:
        self._titulo.setText(t("eventos.titulo"))
        self._campo_busqueda.setPlaceholderText(t("comun.buscar"))
        self._boton_nuevo.setText(t("eventos.nuevo"))
