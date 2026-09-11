"""Sección "Compradores" del espacio de trabajo del evento (contrato de la
fase 4, §4.1, §4.2, §4.3, §4.4). Maestro-detalle como `VistaCartones`: tabla
de compradores con búsqueda, barra de acciones (exportar plantilla, importar
Excel, registrar manual, venta por rango, anular venta) y la fila de
conciliación (decisión DS2 del plan de la fase 4) con exportación a PDF/Excel.

Convenio del trabajador `QThread` (hallazgo C5 del plan de la fase 4): los
envoltorios de módulo `_validar_importacion_en_hilo`/`_aplicar_importacion_en_hilo`
abren y cierran su propia conexión, calcados de `vista_cartones.
_generar_lote_en_hilo` — nunca se comparte `self._con` con el hilo de la Tarea.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from bingo import i18n
from bingo.dominio.modelos import Comprador, Evento
from bingo.i18n import t
from bingo.persistencia import repo_carton, repo_comprador, repo_evento
from bingo.persistencia.conexion import abrir_conexion, cerrar_conexion
from bingo.servicios import servicio_compradores, servicio_conciliacion
from bingo.servicios.servicio_compradores import InformeImportacion, ResultadoImportacion
from bingo.ui.dialogos import FranjaError, confirmar
from bingo.ui.tarea import Tarea
from bingo.utilidades.errores import ErrorBingo

_FILAS_POR_PAGINA = 200
_CATEGORIAS_INFORME = (
    "correctas",
    "completa_provisional",
    "ya_registrado_igual",
    "codigo_inexistente",
    "codigo_ambiguo",
    "duplicado_en_archivo",
    "ya_asignado",
    "sin_nombre",
)


def _validar_importacion_en_hilo(
    evento_id: int, ruta: Path, *, al_progresar: Any, debe_cancelar: Any
) -> InformeImportacion:
    con = abrir_conexion()
    try:
        return servicio_compradores.validar_importacion(
            con, evento_id, ruta, al_progresar=al_progresar, debe_cancelar=debe_cancelar
        )
    finally:
        cerrar_conexion(con)


def _aplicar_importacion_en_hilo(
    evento_id: int, informe: InformeImportacion, *, al_progresar: Any, debe_cancelar: Any
) -> ResultadoImportacion:
    con = abrir_conexion()
    try:
        return servicio_compradores.aplicar_importacion(
            con, evento_id, informe, al_progresar=al_progresar, debe_cancelar=debe_cancelar
        )
    finally:
        cerrar_conexion(con)


class FormularioCompradorDialog(QDialog):
    """Alta manual (contrato §4.1). El foco arranca en el código y `Ctrl+Enter`
    (botón por defecto) guarda — el arranque de la "ráfaga" de la noche del
    evento (decisión DS10), sin la variante completa de "guardar y limpiar"."""

    def __init__(self, *, codigo_fijo: str | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.resultado: tuple[str, Comprador] | None = None

        self._campo_codigo = QLineEdit(codigo_fijo or "")
        self._campo_codigo.setEnabled(codigo_fijo is None)
        self._campo_nombre = QLineEdit()
        self._campo_telefono = QLineEdit()
        self._campo_cedula = QLineEdit()
        self._campo_correo = QLineEdit()

        self._etiqueta_codigo = QLabel()
        self._etiqueta_nombre = QLabel()
        self._etiqueta_telefono = QLabel()
        self._etiqueta_cedula = QLabel()
        self._etiqueta_correo = QLabel()

        formulario = QFormLayout()
        formulario.addRow(self._etiqueta_codigo, self._campo_codigo)
        formulario.addRow(self._etiqueta_nombre, self._campo_nombre)
        formulario.addRow(self._etiqueta_telefono, self._campo_telefono)
        formulario.addRow(self._etiqueta_cedula, self._campo_cedula)
        formulario.addRow(self._etiqueta_correo, self._campo_correo)

        self._botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._botones.accepted.connect(self._aceptar)
        self._botones.rejected.connect(self.reject)

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(formulario)
        distribucion.addWidget(self._botones)

        self.setTabOrder(self._campo_codigo, self._campo_nombre)
        self.setTabOrder(self._campo_nombre, self._campo_telefono)
        self.setTabOrder(self._campo_telefono, self._campo_cedula)
        self.setTabOrder(self._campo_cedula, self._campo_correo)
        (self._campo_nombre if codigo_fijo else self._campo_codigo).setFocus()

        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    def cargar(self, comprador: Comprador, codigo: str) -> None:
        self._campo_codigo.setText(codigo)
        self._campo_codigo.setEnabled(False)
        self._campo_nombre.setText(comprador.nombre)
        self._campo_telefono.setText(comprador.telefono or "")
        self._campo_cedula.setText(comprador.cedula or "")
        self._campo_correo.setText(comprador.correo or "")

    def _aceptar(self) -> None:
        codigo = self._campo_codigo.text().strip()
        nombre = self._campo_nombre.text().strip()
        if not codigo or not nombre:
            QMessageBox.warning(self, "", t("compradores.error.nombre_vacio"))
            return
        comprador = Comprador(
            carton_id=0,
            nombre=nombre,
            telefono=self._campo_telefono.text().strip() or None,
            cedula=self._campo_cedula.text().strip() or None,
            correo=self._campo_correo.text().strip() or None,
        )
        self.resultado = (codigo, comprador)
        self.accept()

    def retraducir(self) -> None:
        self._etiqueta_codigo.setText(t("compradores.campo.codigo"))
        self._etiqueta_nombre.setText(t("compradores.campo.nombre"))
        self._etiqueta_telefono.setText(t("compradores.campo.telefono"))
        self._etiqueta_cedula.setText(t("compradores.campo.cedula"))
        self._etiqueta_correo.setText(t("compradores.campo.correo"))


class VentaPorRangoDialog(QDialog):
    def __init__(self, con: Any, evento_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento_id = evento_id
        self.aplicado = False

        self._campo_desde = QLineEdit()
        self._campo_hasta = QLineEdit()
        self._campo_generico = QLineEdit()
        self._etiqueta_desde = QLabel()
        self._etiqueta_hasta = QLabel()
        self._etiqueta_generico = QLabel()

        formulario = QFormLayout()
        formulario.addRow(self._etiqueta_desde, self._campo_desde)
        formulario.addRow(self._etiqueta_hasta, self._campo_hasta)
        formulario.addRow(self._etiqueta_generico, self._campo_generico)

        self._boton_previsualizar = QPushButton()
        self._boton_previsualizar.clicked.connect(self._previsualizar)
        self._etiqueta_resumen = QLabel()
        self._etiqueta_resumen.setWordWrap(True)

        self._botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._boton_confirmar = QPushButton()
        self._boton_confirmar.setEnabled(False)
        self._boton_confirmar.clicked.connect(self._confirmar)
        self._botones.addButton(self._boton_confirmar, QDialogButtonBox.ButtonRole.AcceptRole)
        self._botones.rejected.connect(self.reject)

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(formulario)
        distribucion.addWidget(self._boton_previsualizar)
        distribucion.addWidget(self._etiqueta_resumen)
        distribucion.addWidget(self._botones)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    def _previsualizar(self) -> None:
        desde = self._campo_desde.text().strip()
        hasta = self._campo_hasta.text().strip()
        if not desde or not hasta:
            return
        try:
            resultado = servicio_compradores.previsualizar_venta_por_rango(
                self._con, self._evento_id, desde, hasta
            )
        except ErrorBingo as error:
            QMessageBox.warning(self, "", t(error.clave_i18n, **error.parametros))
            return
        self._etiqueta_resumen.setText(
            t("compradores.rango.resumen", marcados=resultado.marcados)
            + "\n"
            + t(
                "compradores.rango.resumen.detalle",
                ya_vendidos=resultado.ya_vendidos,
                omitidos_anulados=resultado.omitidos_anulados,
                omitidos_sin_imprimir=resultado.omitidos_sin_imprimir,
            )
        )
        self._boton_confirmar.setEnabled(resultado.marcados > 0)

    def _confirmar(self) -> None:
        desde = self._campo_desde.text().strip()
        hasta = self._campo_hasta.text().strip()
        generico = self._campo_generico.text().strip() or t(
            "compradores.rango.nombre_generico_defecto"
        )
        try:
            resultado = servicio_compradores.marcar_vendidos_por_rango(
                self._con, self._evento_id, desde, hasta, nombre_generico=generico
            )
        except ErrorBingo as error:
            QMessageBox.warning(self, "", t(error.clave_i18n, **error.parametros))
            return
        self.aplicado = True
        self.mensaje_exito = t("compradores.rango.exito", marcados=resultado.marcados)
        self.accept()

    def retraducir(self) -> None:
        self.setWindowTitle(t("compradores.rango.titulo"))
        self._etiqueta_desde.setText(t("compradores.rango.campo.desde"))
        self._etiqueta_hasta.setText(t("compradores.rango.campo.hasta"))
        self._etiqueta_generico.setText(t("compradores.rango.campo.nombre_generico"))
        self._campo_generico.setPlaceholderText(t("compradores.rango.nombre_generico_defecto"))
        self._boton_previsualizar.setText(t("compradores.rango.previsualizar"))
        self._boton_confirmar.setText(t("compradores.rango.confirmar"))


class ImportarComprasDialog(QDialog):
    """Modal de dos pasos (decisión D6/DS3): elegir archivo -> `Tarea(validar_
    importacion)` -> pantalla de informe -> `Tarea(aplicar_importacion)`.
    La escritura no es cancelable (decisión R15): el botón Cancelar se oculta
    (no se deshabilita) en cuanto empieza a aplicar.
    """

    def __init__(self, con: Any, evento: Evento, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento
        self._ruta: Path | None = None
        self._informe: InformeImportacion | None = None
        self._tarea: Tarea | None = None
        self.resultado_final: ResultadoImportacion | None = None
        self.setWindowTitle(t("compradores.importar.titulo"))
        self.resize(760, 540)

        # --- Paso 1 ---
        self._campo_ruta = QLineEdit()
        self._campo_ruta.setReadOnly(True)
        self._boton_elegir = QPushButton()
        self._boton_elegir.clicked.connect(self._elegir_archivo)
        self._boton_validar = QPushButton()
        self._boton_validar.setEnabled(False)
        self._boton_validar.clicked.connect(self._iniciar_validacion)
        fila_archivo = QHBoxLayout()
        fila_archivo.addWidget(self._campo_ruta, stretch=1)
        fila_archivo.addWidget(self._boton_elegir)

        self._panel_paso1 = QWidget()
        distribucion_paso1 = QVBoxLayout(self._panel_paso1)
        self._titulo_paso1 = QLabel()
        distribucion_paso1.addWidget(self._titulo_paso1)
        distribucion_paso1.addLayout(fila_archivo)
        distribucion_paso1.addWidget(self._boton_validar)

        # --- Progreso (compartido entre validar y aplicar) ---
        self._barra_progreso = QProgressBar()
        self._barra_progreso.setVisible(False)
        self._etiqueta_progreso = QLabel()
        self._etiqueta_progreso.setVisible(False)

        # --- Paso 2: informe ---
        self._panel_informe = QWidget()
        self._panel_informe.setVisible(False)
        distribucion_informe = QVBoxLayout(self._panel_informe)
        self._titulo_paso2 = QLabel()
        self._etiqueta_veredicto = QLabel()
        self._etiqueta_veredicto.setWordWrap(True)
        self._combo_filtro = QComboBox()
        self._combo_filtro.currentIndexChanged.connect(self._refrescar_tabla)
        self._tabla = QTableWidget(0, 6)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._boton_revalidar = QPushButton()
        self._boton_revalidar.clicked.connect(self._revalidar_seleccionada)
        self._boton_exportar_informe = QPushButton()
        self._boton_exportar_informe.clicked.connect(self._exportar_informe)
        fila_informe_acciones = QHBoxLayout()
        fila_informe_acciones.addWidget(self._combo_filtro)
        fila_informe_acciones.addStretch()
        fila_informe_acciones.addWidget(self._boton_revalidar)
        fila_informe_acciones.addWidget(self._boton_exportar_informe)
        distribucion_informe.addWidget(self._titulo_paso2)
        distribucion_informe.addWidget(self._etiqueta_veredicto)
        distribucion_informe.addLayout(fila_informe_acciones)
        distribucion_informe.addWidget(self._tabla, stretch=1)

        self._botones = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self._boton_confirmar = QPushButton()
        self._boton_confirmar.setEnabled(False)
        self._boton_confirmar.clicked.connect(self._confirmar_e_importar)
        self._botones.addButton(self._boton_confirmar, QDialogButtonBox.ButtonRole.AcceptRole)
        self._boton_cancelar_dialogo = self._botones.button(QDialogButtonBox.StandardButton.Cancel)
        self._botones.rejected.connect(self._cancelar_o_cerrar)

        distribucion = QVBoxLayout(self)
        distribucion.addWidget(self._panel_paso1)
        distribucion.addWidget(self._barra_progreso)
        distribucion.addWidget(self._etiqueta_progreso)
        distribucion.addWidget(self._panel_informe, stretch=1)
        distribucion.addWidget(self._botones)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)

    # --- Paso 1 ---

    def _elegir_archivo(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self, "", "", "Excel (*.xlsx)")
        if not ruta:
            return
        self._ruta = Path(ruta)
        self._campo_ruta.setText(str(self._ruta))
        self._boton_validar.setEnabled(True)

    def _iniciar_validacion(self) -> None:
        if self._ruta is None:
            return
        self._boton_validar.setEnabled(False)
        self._boton_elegir.setEnabled(False)
        self._barra_progreso.setRange(0, 0)  # indeterminada hasta conocer el conteo (D7)
        self._barra_progreso.setVisible(True)
        self._etiqueta_progreso.setText(t("compradores.importar.validando"))
        self._etiqueta_progreso.setVisible(True)

        self._tarea = Tarea(_validar_importacion_en_hilo, self._evento.id, self._ruta)
        self._tarea.progreso.connect(self._progreso_validacion)
        self._tarea.terminado.connect(self._validacion_terminada)
        self._tarea.fallado.connect(self._validacion_fallada)
        self._tarea.start()

    def _progreso_validacion(self, procesadas: int, _total: int) -> None:
        self._etiqueta_progreso.setText(t("compradores.importar.validando") + f" ({procesadas})")

    def _validacion_terminada(self, resultado: object) -> None:
        self._barra_progreso.setVisible(False)
        self._etiqueta_progreso.setVisible(False)
        self._boton_elegir.setEnabled(True)
        informe = resultado if isinstance(resultado, InformeImportacion) else None
        if informe is None:
            return
        if informe.columnas_faltantes:
            QMessageBox.warning(
                self,
                "",
                t(
                    "compradores.importar.informe.columnas_faltantes",
                    columnas=", ".join(informe.columnas_faltantes),
                ),
            )
            self._boton_validar.setEnabled(True)
            return
        self._informe = informe
        self._panel_paso1.setVisible(False)
        self._panel_informe.setVisible(True)
        self._llenar_filtro()
        self._refrescar_veredicto()
        self._refrescar_tabla()

    def _validacion_fallada(self, error: ErrorBingo) -> None:
        self._barra_progreso.setVisible(False)
        self._etiqueta_progreso.setVisible(False)
        self._boton_elegir.setEnabled(True)
        self._boton_validar.setEnabled(True)
        QMessageBox.warning(self, "", t(error.clave_i18n, **error.parametros))

    # --- Paso 2: informe ---

    def _llenar_filtro(self) -> None:
        actual = self._combo_filtro.currentData()
        self._combo_filtro.blockSignals(True)
        self._combo_filtro.clear()
        self._combo_filtro.addItem(t("compradores.importar.informe.filtro_todas"), None)
        assert self._informe is not None
        for clave in _CATEGORIAS_INFORME:
            filas = getattr(self._informe, clave)
            if filas:
                texto = t(f"compradores.importar.informe.categoria.{clave}")
                self._combo_filtro.addItem(f"{texto} ({len(filas)})", clave)
        indice = self._combo_filtro.findData(actual)
        self._combo_filtro.setCurrentIndex(indice if indice >= 0 else 0)
        self._combo_filtro.blockSignals(False)

    def _refrescar_veredicto(self) -> None:
        assert self._informe is not None
        correctas = len(self._informe.correctas) + len(self._informe.completa_provisional)
        problemas = sum(len(getattr(self._informe, c)) for c in _CATEGORIAS_INFORME) - correctas
        if correctas == 0:
            self._etiqueta_veredicto.setText(t("compradores.importar.informe.veredicto_vacio"))
        elif problemas == 0:
            self._etiqueta_veredicto.setText(
                t("compradores.importar.informe.veredicto_ok", cantidad=correctas)
            )
        else:
            self._etiqueta_veredicto.setText(
                t(
                    "compradores.importar.informe.veredicto_problemas",
                    correctas=correctas,
                    problemas=problemas,
                )
            )
        self._boton_confirmar.setEnabled(correctas > 0)

    def _filas_visibles(self) -> list[tuple[str, Any]]:
        assert self._informe is not None
        categoria_filtro = self._combo_filtro.currentData()
        filas: list[tuple[str, Any]] = []
        categorias = [categoria_filtro] if categoria_filtro else list(_CATEGORIAS_INFORME)
        for clave in categorias:
            for item in getattr(self._informe, clave):
                filas.append((clave, item))
        return filas

    def _refrescar_tabla(self) -> None:
        if self._informe is None:
            return
        filas = self._filas_visibles()
        self._tabla.setRowCount(len(filas))
        for indice, (categoria, item) in enumerate(filas):
            valores = (
                str(item.numero_fila),
                item.codigo,
                item.nombre,
                item.telefono or "",
                item.cedula or "",
                t(f"compradores.importar.informe.categoria.{categoria}"),
            )
            for columna, valor in enumerate(valores):
                celda = QTableWidgetItem(valor)
                if columna != 1:
                    celda.setFlags(celda.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self._tabla.setItem(indice, columna, celda)
        self._tabla.setHorizontalHeaderLabels(
            [
                t("compradores.columna.codigo") + " #",
                t("compradores.columna.codigo"),
                t("compradores.columna.nombre"),
                t("compradores.columna.telefono"),
                t("compradores.columna.cedula"),
                t("compradores.importar.informe.columna_problema"),
            ]
        )

    def _revalidar_seleccionada(self) -> None:
        """Decisión de gusto TD-2: editar el código en la propia tabla del
        informe y revalidar esa fila, sin volver a exportar/reimportar."""
        if self._informe is None:
            return
        fila = self._tabla.currentRow()
        if fila < 0:
            return
        filas_visibles = self._filas_visibles()
        if fila >= len(filas_visibles):
            return
        categoria_original, item = filas_visibles[fila]
        codigo_nuevo = self._tabla.item(fila, 1).text().strip()
        if not codigo_nuevo:
            return

        categoria_nueva, item_actualizado = servicio_compradores.revalidar_fila(
            self._con, self._evento.id, item, codigo_nuevo
        )
        lista_original = getattr(self._informe, categoria_original)
        lista_original.remove(item)
        getattr(self._informe, categoria_nueva).append(item_actualizado)

        self._llenar_filtro()
        self._refrescar_veredicto()
        self._refrescar_tabla()

    def _exportar_informe(self) -> None:
        if self._informe is None:
            return
        ruta, _ = QFileDialog.getSaveFileName(
            self, "", "informe_importacion.xlsx", "Excel (*.xlsx)"
        )
        if not ruta:
            return
        textos = {
            f"categoria_{c}": t(f"compradores.importar.informe.categoria.{c}")
            for c in _CATEGORIAS_INFORME
        }
        try:
            servicio_compradores.exportar_informe(self._informe, Path(ruta), textos)
        except ErrorBingo as error:
            QMessageBox.warning(self, "", t(error.clave_i18n, **error.parametros))

    # --- Confirmar e importar ---

    def _confirmar_e_importar(self) -> None:
        if self._informe is None:
            return
        self._boton_confirmar.setEnabled(False)  # A2/doble clic: un solo disparo
        self._boton_cancelar_dialogo.setVisible(False)  # R15: la escritura no es cancelable
        self._barra_progreso.setRange(
            0, len(self._informe.correctas) + len(self._informe.completa_provisional)
        )
        self._barra_progreso.setValue(0)
        self._barra_progreso.setVisible(True)
        self._etiqueta_progreso.setText(t("compradores.importar.aplicando"))
        self._etiqueta_progreso.setVisible(True)

        self._tarea = Tarea(_aplicar_importacion_en_hilo, self._evento.id, self._informe)
        self._tarea.progreso.connect(self._barra_progreso.setValue)
        self._tarea.terminado.connect(self._importacion_terminada)
        self._tarea.fallado.connect(self._importacion_fallada)
        self._tarea.start()

    def _importacion_terminada(self, resultado: object) -> None:
        if isinstance(resultado, ResultadoImportacion):
            self.resultado_final = resultado
        self.accept()

    def _importacion_fallada(self, error: ErrorBingo) -> None:
        self._barra_progreso.setVisible(False)
        self._etiqueta_progreso.setVisible(False)
        QMessageBox.critical(self, "", t(error.clave_i18n, **error.parametros))
        self.reject()

    def _cancelar_o_cerrar(self) -> None:
        if self._tarea is not None and self._tarea.isRunning():
            self._tarea.cancelar()
            return
        self.reject()

    def retraducir(self) -> None:
        self.setWindowTitle(t("compradores.importar.titulo"))
        self._titulo_paso1.setText(t("compradores.importar.paso1.titulo"))
        self._boton_elegir.setText(t("compradores.importar.elegir_archivo"))
        self._boton_validar.setText(t("compradores.importar.validar_archivo"))
        self._titulo_paso2.setText(t("compradores.importar.informe.titulo"))
        self._boton_revalidar.setText(t("compradores.importar.revalidar"))
        self._boton_exportar_informe.setText(t("compradores.importar.exportar_informe"))
        self._boton_confirmar.setText(t("compradores.importar.confirmar"))
        if self._boton_cancelar_dialogo is not None:
            self._boton_cancelar_dialogo.setText(t("compradores.importar.cancelar"))
        if self._informe is not None:
            self._refrescar_veredicto()
            self._refrescar_tabla()


class VistaCompradores(QWidget):
    def __init__(self, con: Any, evento: Evento, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento

        self._franja = FranjaError()

        # --- Resumen / conciliación (decisión DS2) ---
        self._etiqueta_resumen = QLabel()
        self._boton_exportar_pdf = QPushButton()
        self._boton_exportar_pdf.clicked.connect(self._exportar_pdf)
        self._boton_exportar_excel = QPushButton()
        self._boton_exportar_excel.clicked.connect(self._exportar_excel)
        fila_resumen = QHBoxLayout()
        fila_resumen.addWidget(self._etiqueta_resumen, stretch=1)
        fila_resumen.addWidget(self._boton_exportar_pdf)
        fila_resumen.addWidget(self._boton_exportar_excel)

        # --- Barra de acciones ---
        self._boton_exportar_plantilla = QPushButton()
        self._boton_exportar_plantilla.clicked.connect(self._exportar_plantilla)
        self._boton_importar = QPushButton()
        self._boton_importar.clicked.connect(self._abrir_importar)
        self._boton_nuevo = QPushButton()
        self._boton_nuevo.clicked.connect(self._registrar_manual)
        self._boton_rango = QPushButton()
        self._boton_rango.clicked.connect(self._abrir_venta_por_rango)
        self._boton_anular = QPushButton()
        self._boton_anular.setEnabled(False)
        self._boton_anular.clicked.connect(self._anular_seleccionado)
        # Tarea 4.25 (corrección C4, LOPDP): `servicio_compradores.
        # eliminar_todos_del_evento` existía desde la fase 4 sin ningún
        # botón que lo llamara — mientras eso siguiera así, la política de
        # retención de `TODOS.md` P1 era inejecutable por diseño.
        # Deshabilitado salvo con el evento `finalizado`: no tiene sentido
        # borrar datos de compradores de un evento que todavía puede vender.
        self._boton_eliminar_datos = QPushButton()
        self._boton_eliminar_datos.setEnabled(False)
        self._boton_eliminar_datos.clicked.connect(self._eliminar_datos_compradores)
        fila_acciones = QHBoxLayout()
        fila_acciones.addWidget(self._boton_exportar_plantilla)
        fila_acciones.addWidget(self._boton_importar)
        fila_acciones.addWidget(self._boton_nuevo)
        fila_acciones.addWidget(self._boton_rango)
        fila_acciones.addWidget(self._boton_anular)
        fila_acciones.addStretch()
        fila_acciones.addWidget(self._boton_eliminar_datos)

        # --- Búsqueda + tabla ---
        self._campo_busqueda = QLineEdit()
        self._campo_busqueda.textChanged.connect(self.cargar)
        self._tabla = QTableWidget(0, 4)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tabla.itemDoubleClicked.connect(lambda _i: self._editar_seleccionado())
        self._tabla.itemSelectionChanged.connect(self._seleccion_cambiada)

        panel_tabla = QWidget()
        distribucion_tabla = QVBoxLayout(panel_tabla)
        distribucion_tabla.addWidget(self._campo_busqueda)
        distribucion_tabla.addWidget(self._tabla, stretch=1)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(panel_tabla)

        distribucion = QVBoxLayout(self)
        distribucion.addWidget(self._franja)
        distribucion.addLayout(fila_resumen)
        distribucion.addLayout(fila_acciones)
        distribucion.addWidget(self._splitter, stretch=1)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self.cargar()

    # --- Carga ---

    def cargar(self) -> None:
        self._franja.ocultar()
        texto = self._campo_busqueda.text().strip() or None
        try:
            compradores = repo_comprador.listar_por_evento(
                self._con, self._evento.id, texto_busqueda=texto, limite=_FILAS_POR_PAGINA
            )
            conciliacion = servicio_conciliacion.calcular(self._con, self._evento.id)
        except ErrorBingo as error:
            self._franja.mostrar_error(error, on_reintentar=self.cargar)
            return

        self._tabla.setRowCount(len(compradores))
        for fila, comprador in enumerate(compradores):
            carton = repo_carton.obtener(self._con, comprador.carton_id)
            codigo = carton.codigo if carton else "?"
            estado = t(f"estado_carton.{carton.estado}") if carton else "?"
            nombre = comprador.nombre + (
                f" ({t('compradores.columna.provisional')})" if comprador.provisional else ""
            )
            for columna, valor in enumerate((codigo, nombre, comprador.telefono or "", estado)):
                item = QTableWidgetItem(valor)
                item.setData(Qt.ItemDataRole.UserRole, comprador.id)
                self._tabla.setItem(fila, columna, item)

        from bingo.dominio.dinero import formatear

        self._etiqueta_resumen.setText(
            t(
                "compradores.resumen.texto",
                vendidos=conciliacion.vendidos,
                total=conciliacion.total_cartones,
                provisionales=conciliacion.compradores_provisionales,
                teorica=formatear(conciliacion.recaudacion_teorica_centavos, i18n.idioma_actual()),
            )
        )
        if conciliacion.discrepancia:
            self._franja.mostrar_info(t("conciliacion.advertencia_discrepancia"))
        self._seleccion_cambiada()

        evento_actual = repo_evento.obtener(self._con, self._evento.id)
        self._boton_eliminar_datos.setEnabled(
            evento_actual is not None and evento_actual.estado == "finalizado"
        )

    def _comprador_id_seleccionado(self) -> int | None:
        indices = (
            self._tabla.selectionModel().selectedRows() if self._tabla.selectionModel() else []
        )
        if not indices:
            return None
        item = self._tabla.item(indices[0].row(), 0)
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _seleccion_cambiada(self) -> None:
        self._boton_anular.setEnabled(self._comprador_id_seleccionado() is not None)

    # --- Exportación de plantilla ---

    def _textos_plantilla(self) -> dict[str, str]:
        claves = (
            "columna_codigo",
            "columna_nombre",
            "columna_telefono",
            "columna_cedula",
            "columna_correo",
            "hoja_instrucciones",
            "instrucciones_titulo",
            "instrucciones_no_mover_codigo",
            "instrucciones_columnas_reconocidas",
            "instrucciones_cedula_opcional",
            "instrucciones_finalidad",
            "instrucciones_plazo",
            "instrucciones_responsable",
        )
        return {clave: t(f"compradores.plantilla.{clave}") for clave in claves}

    def _exportar_plantilla(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(
            self, "", "plantilla_compradores.xlsx", "Excel (*.xlsx)"
        )
        if not ruta:
            return
        try:
            servicio_compradores.exportar_plantilla(
                self._con, self._evento.id, Path(ruta), self._textos_plantilla()
            )
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._franja.mostrar_exito(t("compradores.accion.exportar_plantilla"))

    # --- Importación ---

    def _abrir_importar(self) -> None:
        dialogo = ImportarComprasDialog(self._con, self._evento, parent=self)
        dialogo.exec()
        self.cargar()
        if dialogo.resultado_final is not None:
            resultado = dialogo.resultado_final
            total_pendientes = resultado.detenida_en_fila
            if total_pendientes is None:
                self._franja.mostrar_exito(
                    t(
                        "compradores.importar.resultado",
                        aplicadas=resultado.aplicadas,
                        completadas=resultado.completadas_provisionales,
                    )
                )
            else:
                self._franja.mostrar_info(
                    t(
                        "compradores.importar.resultado.con_pendientes",
                        aplicadas=resultado.aplicadas,
                        pendientes=total_pendientes,
                    )
                )

    # --- Alta / edición manual ---

    def _registrar_manual(self) -> None:
        dialogo = FormularioCompradorDialog(parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted or dialogo.resultado is None:
            return
        codigo, comprador = dialogo.resultado
        try:
            servicio_compradores.registrar_manual(self._con, self._evento.id, codigo, comprador)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self.cargar()
        self._franja.mostrar_exito(t("compradores.exito.registrado"))

    def _editar_seleccionado(self) -> None:
        comprador_id = self._comprador_id_seleccionado()
        if comprador_id is None:
            return
        comprador = repo_comprador.obtener(self._con, comprador_id)
        if comprador is None:
            return
        carton = repo_carton.obtener(self._con, comprador.carton_id)
        dialogo = FormularioCompradorDialog(
            codigo_fijo=carton.codigo if carton else "", parent=self
        )
        dialogo.cargar(comprador, carton.codigo if carton else "")
        if dialogo.exec() != QDialog.DialogCode.Accepted or dialogo.resultado is None:
            return
        _codigo, datos = dialogo.resultado
        import dataclasses

        actualizado = dataclasses.replace(
            comprador,
            nombre=datos.nombre,
            telefono=datos.telefono,
            cedula=datos.cedula,
            correo=datos.correo,
        )
        try:
            servicio_compradores.actualizar_comprador(self._con, actualizado)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self.cargar()
        self._franja.mostrar_exito(t("compradores.exito.actualizado"))

    # --- Anulación ---

    def _anular_seleccionado(self) -> None:
        comprador_id = self._comprador_id_seleccionado()
        if comprador_id is None:
            return
        comprador = repo_comprador.obtener(self._con, comprador_id)
        if comprador is None:
            return
        carton = repo_carton.obtener(self._con, comprador.carton_id)
        estado_previo = comprador.estado_carton_previo or "entregado"
        if not confirmar(
            self,
            t("compradores.confirmar_anular.titulo"),
            t(
                "compradores.confirmar_anular.mensaje",
                codigo=carton.codigo if carton else "?",
                estado_previo=t(f"estado_carton.{estado_previo}"),
            ),
        ):
            return
        try:
            servicio_compradores.anular_venta(self._con, comprador_id)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self.cargar()
        self._franja.mostrar_exito(t("compradores.exito.anulado"))

    # --- Borrado de datos (tarea 4.25, corrección C4, LOPDP) ---

    def _eliminar_datos_compradores(self) -> None:
        # Defensivo: el botón ya se deshabilita si no está `finalizado`,
        # pero nada garantiza que este método corra después de ese refresco
        # (mismo criterio que 4.13 con "Finalizar evento").
        evento_actual = repo_evento.obtener(self._con, self._evento.id)
        if evento_actual is None or evento_actual.estado != "finalizado":
            return
        texto, ok = QInputDialog.getText(
            self,
            t("compradores.eliminar_datos.confirmar.titulo"),
            t("compradores.eliminar_datos.confirmar.mensaje", nombre=self._evento.nombre),
        )
        if not ok or texto != self._evento.nombre:
            return
        try:
            eliminados = servicio_compradores.eliminar_todos_del_evento(self._con, self._evento.id)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self.cargar()
        self._franja.mostrar_exito(t("compradores.eliminar_datos.exito", cantidad=eliminados))

    # --- Venta por rango ---

    def _abrir_venta_por_rango(self) -> None:
        dialogo = VentaPorRangoDialog(self._con, self._evento.id, parent=self)
        if dialogo.exec() == QDialog.DialogCode.Accepted and dialogo.aplicado:
            self.cargar()
            self._franja.mostrar_exito(getattr(dialogo, "mensaje_exito", ""))

    # --- Conciliación ---

    def _textos_conciliacion(self) -> dict[str, str]:
        claves_etiqueta = (
            "generados",
            "impresos",
            "entregados",
            "vendidos",
            "anulados",
            "total_cartones",
            "compradores_registrados",
            "compradores_provisionales",
            "recaudacion_teorica",
            "recaudado_real",
            "diferencia",
        )
        claves_columna = ("codigo", "estado", "comprador", "telefono", "cedula", "correo")
        textos = {f"etiqueta_{c}": t(f"conciliacion.etiqueta.{c}") for c in claves_etiqueta}
        textos.update({f"columna_{c}": t(f"conciliacion.columna.{c}") for c in claves_columna})
        textos["titulo"] = t("conciliacion.titulo_pdf")
        textos["hoja_resumen"] = t("conciliacion.hoja_resumen")
        textos["hoja_detalle"] = t("conciliacion.hoja_detalle")
        textos["advertencia_discrepancia"] = t("conciliacion.advertencia_discrepancia")
        return textos

    def _exportar_pdf(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(self, "", "conciliacion.pdf", "PDF (*.pdf)")
        if not ruta:
            return
        try:
            servicio_conciliacion.generar_reporte_pdf(
                self._con,
                self._evento.id,
                Path(ruta),
                self._textos_conciliacion(),
                idioma=i18n.idioma_actual(),
            )
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._franja.mostrar_exito(t("conciliacion.accion.exportar_pdf"))

    def _exportar_excel(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(self, "", "conciliacion.xlsx", "Excel (*.xlsx)")
        if not ruta:
            return
        incluir_contacto = confirmar(self, "", t("conciliacion.incluir_contacto"))
        try:
            servicio_conciliacion.generar_reporte_excel(
                self._con,
                self._evento.id,
                Path(ruta),
                self._textos_conciliacion(),
                idioma=i18n.idioma_actual(),
                incluir_contacto=incluir_contacto,
            )
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._franja.mostrar_exito(t("conciliacion.accion.exportar_excel"))

    # --- i18n ---

    def retraducir(self) -> None:
        self._boton_exportar_plantilla.setText(t("compradores.accion.exportar_plantilla"))
        self._boton_importar.setText(t("compradores.accion.importar"))
        self._boton_nuevo.setText(t("compradores.accion.nuevo"))
        self._boton_rango.setText(t("compradores.accion.venta_por_rango"))
        self._boton_anular.setText(t("compradores.accion.anular_venta"))
        self._boton_eliminar_datos.setText(t("compradores.accion.eliminar_datos"))
        self._boton_exportar_pdf.setText(t("conciliacion.accion.exportar_pdf"))
        self._boton_exportar_excel.setText(t("conciliacion.accion.exportar_excel"))
        self._campo_busqueda.setPlaceholderText(t("compradores.buscar"))
        self._tabla.setHorizontalHeaderLabels(
            [
                t("compradores.columna.codigo"),
                t("compradores.columna.nombre"),
                t("compradores.columna.telefono"),
                t("compradores.columna.estado"),
            ]
        )
