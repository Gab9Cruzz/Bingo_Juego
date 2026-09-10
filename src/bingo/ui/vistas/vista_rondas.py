"""Sección "Rondas" del espacio de trabajo del evento (contrato de la fase 4,
§4.6, §4.7). Lista de rondas ordenada a la izquierda (con Subir/Bajar);
formulario de la ronda seleccionada a la derecha; panel fijo abajo con
`servicio_rondas.validar_evento_listo` (decisión DS1/B.3 del plan de la
fase 4).

El selector de patrón **no es un `QComboBox`** (decisión DS17): una lista con
miniatura de la rejilla 5x5 de cada patrón, agrupada Sistema/Organización,
con *Nuevo*/*Duplicar*/*Editar* en el propio selector.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from bingo import i18n
from bingo.dominio.dinero import a_centavos
from bingo.dominio.modelos import Evento, Patron, Ronda
from bingo.i18n import t
from bingo.persistencia import repo_patron, repo_ronda
from bingo.servicios import servicio_patrones, servicio_rondas
from bingo.ui.dialogos import FranjaError, confirmar
from bingo.ui.widgets.rejilla_patron import RejillaPatron
from bingo.utilidades.errores import ErrorBingo

_TIPOS_PREMIO = (
    (None, "rondas.premio_tipo.sin_elegir"),
    ("bien", "rondas.premio_tipo.bien"),
    ("efectivo", "rondas.premio_tipo.efectivo"),
)


class EditorPatronDialog(QDialog):
    """Nuevo/duplicar/editar un patrón propio de la organización (contrato
    §4.6). Los patrones del sistema nunca se editan aquí — solo se duplican
    (`servicio_patrones.duplicar_patron` construye la copia antes de abrir
    este diálogo)."""

    def __init__(
        self,
        con: Any,
        organizacion_id: int,
        patron: Patron | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._con = con
        self._organizacion_id = organizacion_id
        self._patron_original = patron

        self._campo_nombre = QLineEdit(patron.nombre if patron else "")
        self._check_usa_libre = QCheckBox()
        self._check_usa_libre.setChecked(patron.usa_libre if patron else True)
        self._rejilla = RejillaPatron(mascara_inicial=patron.mascaras[0] if patron else 0)
        self._rejilla.cambiado.connect(self._actualizar_contador)
        self._etiqueta_contador = QLabel()

        self._botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._botones.accepted.connect(self._guardar)
        self._botones.rejected.connect(self.reject)

        formulario = QFormLayout()
        self._etiqueta_nombre = QLabel()
        formulario.addRow(self._etiqueta_nombre, self._campo_nombre)
        formulario.addRow(self._check_usa_libre)

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(formulario)
        distribucion.addWidget(self._rejilla, alignment=Qt.AlignmentFlag.AlignCenter)
        distribucion.addWidget(self._etiqueta_contador, alignment=Qt.AlignmentFlag.AlignCenter)
        distribucion.addWidget(self._botones)

        self.patron_guardado: Patron | None = None
        self._actualizar_contador()
        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    def _actualizar_contador(self) -> None:
        self._etiqueta_contador.setText(
            t("patrones.editor.contador", cantidad=self._rejilla.contador_celdas())
        )
        self._botones.button(QDialogButtonBox.StandardButton.Save).setEnabled(
            self._rejilla.contador_celdas() > 0 and bool(self._campo_nombre.text().strip())
        )

    def _guardar(self) -> None:
        nombre = self._campo_nombre.text().strip()
        datos = Patron(
            nombre=nombre,
            mascaras=[self._rejilla.mascara()],
            usa_libre=self._check_usa_libre.isChecked(),
            organizacion_id=self._organizacion_id,
            id=self._patron_original.id if self._patron_original else None,
        )
        try:
            if self._patron_original is not None:
                servicio_patrones.validar_patron(self._con, datos)
                repo_patron.actualizar(self._con, datos)
                self.patron_guardado = datos
            else:
                self.patron_guardado = servicio_patrones.crear_patron(self._con, datos)
        except ErrorBingo as error:
            QMessageBox.warning(self, "", t(error.clave_i18n, **error.parametros))
            return
        self.accept()

    def retraducir(self) -> None:
        self.setWindowTitle(
            t(
                "patrones.editor.titulo_editar"
                if self._patron_original
                else "patrones.editor.titulo_nuevo"
            )
        )
        self._etiqueta_nombre.setText(t("patrones.campo.nombre"))
        self._check_usa_libre.setText(t("patrones.campo.usa_libre"))
        self._actualizar_contador()


class SelectorPatronDialog(QDialog):
    """DS17: selector visual por miniaturas, agrupado Sistema/Organización,
    con Nuevo/Duplicar/Editar dentro del propio selector."""

    def __init__(
        self,
        con: Any,
        organizacion_id: int,
        patron_id_actual: int | None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._con = con
        self._organizacion_id = organizacion_id
        self.patron_id_elegido: int | None = patron_id_actual

        self._lista = QListWidget()
        self._lista.setIconSize(self._lista.iconSize())
        self._lista.itemSelectionChanged.connect(self._actualizar_botones)
        self._lista.itemDoubleClicked.connect(lambda _i: self._botones.accepted.emit())

        self._boton_nuevo = QPushButton()
        self._boton_nuevo.clicked.connect(self._nuevo)
        self._boton_duplicar = QPushButton()
        self._boton_duplicar.clicked.connect(self._duplicar)
        self._boton_editar = QPushButton()
        self._boton_editar.clicked.connect(self._editar)

        fila_acciones = QHBoxLayout()
        fila_acciones.addWidget(self._boton_nuevo)
        fila_acciones.addWidget(self._boton_duplicar)
        fila_acciones.addWidget(self._boton_editar)
        fila_acciones.addStretch()

        self._botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._botones.accepted.connect(self._aceptar)
        self._botones.rejected.connect(self.reject)

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(fila_acciones)
        distribucion.addWidget(self._lista, stretch=1)
        distribucion.addWidget(self._botones)
        self.resize(420, 480)

        self._cargar_lista()
        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    def _cargar_lista(self) -> None:
        self._lista.clear()
        patrones = repo_patron.listar(self._con, organizacion_id=self._organizacion_id)
        for patron in patrones:
            texto = t(patron.clave_i18n) if patron.clave_i18n else patron.nombre
            grupo = (
                t("patrones.grupo.sistema")
                if patron.es_sistema
                else t("patrones.grupo.organizacion")
            )
            item = QListWidgetItem(f"[{grupo}] {texto}")
            item.setData(Qt.ItemDataRole.UserRole, patron.id)
            self._lista.addItem(item)
            if patron.id == self.patron_id_elegido:
                item.setSelected(True)
                self._lista.setCurrentItem(item)
        self._actualizar_botones()

    def _patron_seleccionado(self) -> Patron | None:
        item = self._lista.currentItem()
        if item is None:
            return None
        return repo_patron.obtener(self._con, item.data(Qt.ItemDataRole.UserRole))

    def _actualizar_botones(self) -> None:
        patron = self._patron_seleccionado()
        self._boton_duplicar.setEnabled(patron is not None)
        self._boton_editar.setEnabled(patron is not None and not patron.es_sistema)

    def _nuevo(self) -> None:
        dialogo = EditorPatronDialog(self._con, self._organizacion_id, None, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted and dialogo.patron_guardado:
            self.patron_id_elegido = dialogo.patron_guardado.id
            self._cargar_lista()

    def _duplicar(self) -> None:
        patron = self._patron_seleccionado()
        if patron is None:
            return
        nombre_sugerido = t("patrones.editor.nombre_duplicado_sugerido", nombre=patron.nombre)
        nombre, ok = QInputDialog.getText(
            self, "", t("patrones.campo.nombre"), text=nombre_sugerido
        )
        if not ok or not nombre.strip():
            return
        try:
            copia = servicio_patrones.duplicar_patron(
                self._con, patron.id, nombre.strip(), self._organizacion_id
            )
        except ErrorBingo as error:
            QMessageBox.warning(self, "", t(error.clave_i18n, **error.parametros))
            return
        self.patron_id_elegido = copia.id
        self._cargar_lista()

    def _editar(self) -> None:
        patron = self._patron_seleccionado()
        if patron is None or patron.es_sistema:
            return
        dialogo = EditorPatronDialog(self._con, self._organizacion_id, patron, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self._cargar_lista()

    def _aceptar(self) -> None:
        patron = self._patron_seleccionado()
        self.patron_id_elegido = patron.id if patron else None
        self.accept()

    def retraducir(self) -> None:
        self.setWindowTitle(t("rondas.patron.elegir"))
        self._boton_nuevo.setText(t("rondas.patron.accion.nuevo"))
        self._boton_duplicar.setText(t("rondas.patron.accion.duplicar"))
        self._boton_editar.setText(t("rondas.patron.accion.editar"))


class VistaRondas(QWidget):
    def __init__(self, con: Any, evento: Evento, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento
        self._ronda_actual: Ronda | None = None
        self._patron_id_formulario: int | None = None
        self._actualizando_formulario = False

        self._franja = FranjaError()

        self._lista = QListWidget()
        self._lista.currentRowChanged.connect(self._seleccion_cambiada)
        self._boton_nueva = QPushButton()
        self._boton_nueva.clicked.connect(self._nueva_ronda)
        self._boton_subir = QPushButton()
        self._boton_subir.clicked.connect(lambda: self._mover(-1))
        self._boton_bajar = QPushButton()
        self._boton_bajar.clicked.connect(lambda: self._mover(1))
        self._boton_eliminar = QPushButton()
        self._boton_eliminar.clicked.connect(self._eliminar_ronda)

        fila_botones_lista = QHBoxLayout()
        fila_botones_lista.addWidget(self._boton_nueva)
        fila_botones_lista.addWidget(self._boton_subir)
        fila_botones_lista.addWidget(self._boton_bajar)
        fila_botones_lista.addWidget(self._boton_eliminar)

        panel_lista = QWidget()
        distribucion_lista = QVBoxLayout(panel_lista)
        distribucion_lista.addLayout(fila_botones_lista)
        distribucion_lista.addWidget(self._lista, stretch=1)

        self._panel_formulario = self._construir_formulario()
        self._panel_formulario.setEnabled(False)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(panel_lista)
        self._splitter.addWidget(self._panel_formulario)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 2)

        self._grupo_pendientes = QGroupBox()
        self._etiqueta_pendientes = QLabel()
        self._etiqueta_pendientes.setWordWrap(True)
        distribucion_pendientes = QVBoxLayout()
        distribucion_pendientes.addWidget(self._etiqueta_pendientes)
        self._grupo_pendientes.setLayout(distribucion_pendientes)

        distribucion = QVBoxLayout(self)
        distribucion.addWidget(self._franja)
        distribucion.addWidget(self._splitter, stretch=1)
        distribucion.addWidget(self._grupo_pendientes)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self.cargar()

    def _construir_formulario(self) -> QWidget:
        panel = QWidget()
        formulario = QFormLayout(panel)

        self._campo_nombre = QLineEdit()
        self._campo_nombre.textChanged.connect(self._marcar_cambio)
        self._boton_patron = QPushButton()
        self._boton_patron.clicked.connect(self._elegir_patron)
        self._rejilla_previa = RejillaPatron(solo_lectura=True)
        self._campo_premio_nombre = QLineEdit()
        self._campo_premio_nombre.textChanged.connect(self._marcar_cambio)
        self._combo_premio_tipo = QComboBox()
        self._combo_premio_tipo.currentIndexChanged.connect(self._tipo_premio_cambiado)
        self._campo_premio_valor = QLineEdit()
        self._campo_premio_valor.setPlaceholderText("0.00")
        self._campo_premio_valor.textChanged.connect(self._marcar_cambio)
        self._campo_premio_descripcion = QLineEdit()
        self._campo_premio_descripcion.textChanged.connect(self._marcar_cambio)
        self._boton_premio_imagen = QPushButton()
        self._boton_premio_imagen.clicked.connect(self._cargar_imagen_premio)
        self._etiqueta_premio_imagen = QLabel("—")

        self._etiqueta_nombre = QLabel()
        self._etiqueta_patron = QLabel()
        self._etiqueta_premio_nombre = QLabel()
        self._etiqueta_premio_tipo = QLabel()
        self._etiqueta_premio_valor = QLabel()
        self._etiqueta_premio_descripcion = QLabel()
        self._etiqueta_premio_imagen = QLabel()

        fila_imagen = QHBoxLayout()
        fila_imagen.addWidget(self._boton_premio_imagen)
        fila_imagen.addWidget(self._etiqueta_premio_imagen)

        formulario.addRow(self._etiqueta_nombre, self._campo_nombre)
        formulario.addRow(self._etiqueta_patron, self._boton_patron)
        formulario.addRow(self._rejilla_previa)
        formulario.addRow(self._etiqueta_premio_nombre, self._campo_premio_nombre)
        formulario.addRow(self._etiqueta_premio_tipo, self._combo_premio_tipo)
        formulario.addRow(self._etiqueta_premio_valor, self._campo_premio_valor)
        formulario.addRow(self._etiqueta_premio_descripcion, self._campo_premio_descripcion)
        formulario.addRow(self._etiqueta_premio_imagen, fila_imagen)
        return panel

    # --- Carga ---

    def cargar(self) -> None:
        self._franja.ocultar()
        try:
            rondas = repo_ronda.listar_por_evento(self._con, self._evento.id)
        except ErrorBingo as error:
            self._franja.mostrar_error(error, on_reintentar=self.cargar)
            return
        fila_actual = self._lista.currentRow()
        self._lista.blockSignals(True)
        self._lista.clear()
        for ronda in rondas:
            item = QListWidgetItem(ronda.nombre)
            item.setData(Qt.ItemDataRole.UserRole, ronda.id)
            self._lista.addItem(item)
        self._lista.blockSignals(False)
        if rondas:
            nueva_fila = min(max(fila_actual, 0), len(rondas) - 1)
            self._lista.setCurrentRow(nueva_fila)
        else:
            self._seleccion_cambiada(-1)
        self._actualizar_pendientes()

    def _actualizar_pendientes(self) -> None:
        try:
            pendientes = servicio_rondas.validar_evento_listo(self._con, self._evento.id)
        except ErrorBingo:
            return
        bloqueantes = [p for p in pendientes if p.bloqueante]
        avisos = [p for p in pendientes if not p.bloqueante]
        if not bloqueantes and not avisos:
            self._etiqueta_pendientes.setText("✔ " + t("rondas.pendientes.listo"))
        else:
            lineas = [f"• {t(p.clave_i18n, **p.parametros)}" for p in bloqueantes + avisos]
            self._etiqueta_pendientes.setText("\n".join(lineas))

    # --- Selección y formulario ---

    def _seleccion_cambiada(self, fila: int) -> None:
        if fila < 0:
            self._ronda_actual = None
            self._panel_formulario.setEnabled(False)
            return
        item = self._lista.item(fila)
        if item is None:
            return
        ronda_id = item.data(Qt.ItemDataRole.UserRole)
        self._ronda_actual = repo_ronda.obtener(self._con, ronda_id)
        self._panel_formulario.setEnabled(True)
        self._cargar_formulario(self._ronda_actual)

    def _cargar_formulario(self, ronda: Ronda) -> None:
        self._actualizando_formulario = True
        try:
            self._campo_nombre.setText(ronda.nombre)
            self._patron_id_formulario = ronda.patron_id
            self._actualizar_boton_patron()
            self._campo_premio_nombre.setText(ronda.premio_nombre or "")
            indice = self._combo_premio_tipo.findData(ronda.premio_tipo)
            self._combo_premio_tipo.setCurrentIndex(indice if indice >= 0 else 0)
            if ronda.premio_valor_centavos is not None:
                self._campo_premio_valor.setText(f"{ronda.premio_valor_centavos / 100:.2f}")
            else:
                self._campo_premio_valor.clear()
            self._campo_premio_descripcion.setText(ronda.premio_descripcion or "")
            if ronda.premio_imagen and Path(ronda.premio_imagen).exists():
                self._etiqueta_premio_imagen.setText(Path(ronda.premio_imagen).name)
            else:
                self._etiqueta_premio_imagen.setText("—")
            self._campo_premio_valor.setVisible(ronda.premio_tipo == "efectivo")
            self._etiqueta_premio_valor.setVisible(ronda.premio_tipo == "efectivo")
        finally:
            self._actualizando_formulario = False

    def _actualizar_boton_patron(self) -> None:
        if self._patron_id_formulario is None:
            self._boton_patron.setText(t("rondas.patron.elegir"))
            self._rejilla_previa.establecer_mascara(0)
            return
        patron = repo_patron.obtener(self._con, self._patron_id_formulario)
        if patron is None:
            return
        texto = t(patron.clave_i18n) if patron.clave_i18n else patron.nombre
        self._boton_patron.setText(texto)
        self._rejilla_previa.establecer_mascara(patron.mascaras[0])

    def _elegir_patron(self) -> None:
        dialogo = SelectorPatronDialog(
            self._con, self._evento.organizacion_id, self._patron_id_formulario, parent=self
        )
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            self._patron_id_formulario = dialogo.patron_id_elegido
            self._actualizar_boton_patron()
            self._marcar_cambio()

    def _tipo_premio_cambiado(self) -> None:
        tipo = self._combo_premio_tipo.currentData()
        self._campo_premio_valor.setVisible(tipo == "efectivo")
        self._etiqueta_premio_valor.setVisible(tipo == "efectivo")
        self._marcar_cambio()

    def _marcar_cambio(self, *_args: object) -> None:
        if self._actualizando_formulario or self._ronda_actual is None:
            return
        self._guardar_formulario()

    def _leer_valor_centavos(self) -> int | None:
        texto = self._campo_premio_valor.text().strip().replace(",", ".")
        if not texto:
            return None
        try:
            from decimal import Decimal, InvalidOperation

            return a_centavos(Decimal(texto))
        except InvalidOperation:
            return None

    def _guardar_formulario(self) -> None:
        if self._ronda_actual is None or self._patron_id_formulario is None:
            return
        actualizada = dataclasses.replace(
            self._ronda_actual,
            nombre=self._campo_nombre.text().strip() or self._ronda_actual.nombre,
            patron_id=self._patron_id_formulario,
            premio_nombre=self._campo_premio_nombre.text().strip() or None,
            premio_tipo=self._combo_premio_tipo.currentData(),
            premio_valor_centavos=self._leer_valor_centavos(),
            premio_descripcion=self._campo_premio_descripcion.text().strip() or None,
        )
        try:
            servicio_rondas.actualizar_ronda(self._con, actualizada)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._ronda_actual = actualizada
        self._franja.ocultar()
        self._actualizar_pendientes()
        self._refrescar_nombre_en_lista()

    def _refrescar_nombre_en_lista(self) -> None:
        item = self._lista.currentItem()
        if item is not None and self._ronda_actual is not None:
            item.setText(self._ronda_actual.nombre)

    # --- Acciones de lista ---

    def _nueva_ronda(self) -> None:
        patrones = repo_patron.listar(self._con, organizacion_id=self._evento.organizacion_id)
        if not patrones:
            self._franja.mostrar(t("rondas.vacio.titulo"))
            return
        try:
            creada = servicio_rondas.crear_ronda(
                self._con,
                Ronda(
                    evento_id=self._evento.id,
                    nombre=t("rondas.accion.nueva"),
                    patron_id=patrones[0].id,
                ),
            )
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self.cargar()
        for fila in range(self._lista.count()):
            if self._lista.item(fila).data(Qt.ItemDataRole.UserRole) == creada.id:
                self._lista.setCurrentRow(fila)
                break
        self._franja.mostrar_exito(t("rondas.exito.guardada"))

    def _eliminar_ronda(self) -> None:
        if self._ronda_actual is None:
            return
        if not confirmar(
            self,
            t("rondas.confirmar_eliminar.titulo"),
            t("rondas.confirmar_eliminar.mensaje", nombre=self._ronda_actual.nombre),
        ):
            return
        try:
            servicio_rondas.eliminar_ronda(self._con, self._ronda_actual.id)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self.cargar()

    def _mover(self, delta: int) -> None:
        fila_actual = self._lista.currentRow()
        nueva_fila = fila_actual + delta
        if fila_actual < 0 or not (0 <= nueva_fila < self._lista.count()):
            return
        ids_en_orden = [
            self._lista.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self._lista.count())
        ]
        ids_en_orden[fila_actual], ids_en_orden[nueva_fila] = (
            ids_en_orden[nueva_fila],
            ids_en_orden[fila_actual],
        )
        try:
            servicio_rondas.reordenar(self._con, self._evento.id, ids_en_orden)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        ronda_id_seleccionada = self._lista.item(fila_actual).data(Qt.ItemDataRole.UserRole)
        self.cargar()
        # DS15: la ronda movida se mantiene seleccionada y con foco, para que
        # Subir-Subir-Subir funcione a repetición sin recuperar el ratón.
        for fila in range(self._lista.count()):
            if self._lista.item(fila).data(Qt.ItemDataRole.UserRole) == ronda_id_seleccionada:
                self._lista.setCurrentRow(fila)
                break
        self._lista.setFocus()

    def _cargar_imagen_premio(self) -> None:
        if self._ronda_actual is None:
            return
        ruta, _ = QFileDialog.getOpenFileName(
            self, t("rondas.accion.cargar_imagen_premio"), "", "Imágenes (*.png *.jpg *.jpeg)"
        )
        if not ruta:
            return
        try:
            resultado = servicio_rondas.guardar_imagen_premio(
                self._con, self._evento.id, self._ronda_actual.id, Path(ruta)
            )
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._etiqueta_premio_imagen.setText(Path(resultado).name)
        self._ronda_actual = dataclasses.replace(self._ronda_actual, premio_imagen=resultado)

    # --- i18n ---

    def retraducir(self) -> None:
        self._boton_nueva.setText(t("rondas.accion.nueva"))
        self._boton_subir.setText(t("rondas.accion.subir"))
        self._boton_bajar.setText(t("rondas.accion.bajar"))
        self._boton_eliminar.setText(t("rondas.accion.eliminar"))
        self._grupo_pendientes.setTitle(t("rondas.pendientes.titulo"))

        self._etiqueta_nombre.setText(t("rondas.campo.nombre"))
        self._etiqueta_patron.setText(t("rondas.campo.patron"))
        self._etiqueta_premio_nombre.setText(t("rondas.campo.premio_nombre"))
        self._etiqueta_premio_tipo.setText(t("rondas.campo.premio_tipo"))
        self._etiqueta_premio_valor.setText(t("rondas.campo.premio_valor"))
        self._etiqueta_premio_descripcion.setText(t("rondas.campo.premio_descripcion"))
        self._etiqueta_premio_imagen.setText(t("rondas.campo.premio_imagen"))
        self._boton_premio_imagen.setText(t("rondas.accion.cargar_imagen_premio"))
        if self._patron_id_formulario is None:
            self._boton_patron.setText(t("rondas.patron.elegir"))

        actual = self._combo_premio_tipo.currentData() if self._combo_premio_tipo.count() else None
        self._combo_premio_tipo.blockSignals(True)
        self._combo_premio_tipo.clear()
        for valor, clave in _TIPOS_PREMIO:
            self._combo_premio_tipo.addItem(t(clave), valor)
        indice = self._combo_premio_tipo.findData(actual)
        self._combo_premio_tipo.setCurrentIndex(indice if indice >= 0 else 0)
        self._combo_premio_tipo.blockSignals(False)

        self._actualizar_pendientes()
