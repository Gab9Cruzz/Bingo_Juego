"""Sección "Cartones" del espacio de trabajo del evento (contrato de la fase
2, §2.5). Layout maestro-detalle fijado por la revisión de diseño de
`docs/Fase_2/Plan_Implementacion_Fase2.md`: panel de resumen siempre visible
arriba, listado paginado a la izquierda, visor a la derecha, separados por un
`QSplitter` (redimensionable: la ventana de escritorio no tiene breakpoints,
pero sí monitores de tamaños distintos).
"""

from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from bingo import i18n
from bingo.config.ajustes import LIMITE_CARTONES_POR_LOTE, LONGITUD_MAXIMA_PREFIJO_CODIGO
from bingo.dominio.carton import carton_desde_orden_canonico
from bingo.dominio.modelos import Carton, Evento
from bingo.i18n import t
from bingo.persistencia import repo_carton, repo_lote
from bingo.persistencia.conexion import abrir_conexion, cerrar_conexion
from bingo.servicios import servicio_cartones
from bingo.ui.dialogos import FranjaError
from bingo.ui.tarea import Tarea
from bingo.ui.widgets.cuadricula_carton import CuadriculaCarton
from bingo.utilidades.errores import ErrorBingo

_ESTADOS_CARTON = ("generado", "impreso", "entregado", "vendido", "anulado")
_FILAS_POR_PAGINA = 200


def _generar_lote_en_hilo(
    evento_id: int,
    cantidad: int,
    prefijo: str,
    *,
    al_progresar: Any,
    debe_cancelar: Any,
) -> None:
    """El invocable de `Tarea` abre y cierra su propia conexión (convenio de
    `docs/convenciones-codigo.md`): una conexión SQLite no es segura entre
    hilos, y esta función corre en el hilo de `Tarea`, nunca en el de la UI.
    """
    con = abrir_conexion()
    try:
        servicio_cartones.generar_lote(
            con,
            evento_id,
            cantidad,
            prefijo,
            al_progresar=al_progresar,
            debe_cancelar=debe_cancelar,
        )
    finally:
        cerrar_conexion(con)


class FormularioGenerarLote(QDialog):
    """Modal de un paso (dos campos): decisión de gusto D3 del gate final de
    la fase 2, resuelta a favor de un modal (acción puntual, no una sección
    permanente de la pantalla).
    """

    def __init__(self, con: Any, evento_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento_id = evento_id
        self.setMinimumWidth(360)
        self.resultado: tuple[int, str] | None = None

        self._campo_cantidad = QSpinBox()
        self._campo_cantidad.setRange(1, LIMITE_CARTONES_POR_LOTE)
        self._campo_cantidad.setValue(100)

        self._campo_prefijo = QLineEdit()
        self._campo_prefijo.setMaxLength(LONGITUD_MAXIMA_PREFIJO_CODIGO)
        self._aviso_prefijo = QLabel()
        self._aviso_prefijo.setStyleSheet("color: #e2a33d;")
        self._aviso_prefijo.setVisible(False)
        self._error_prefijo = QLabel()
        self._error_prefijo.setStyleSheet("color: #e5484d;")
        self._error_prefijo.setVisible(False)
        self._campo_prefijo.textChanged.connect(self._revisar_prefijo)

        self._formulario = QFormLayout()
        self._etiqueta_cantidad = QLabel()
        self._etiqueta_prefijo = QLabel()
        self._formulario.addRow(self._etiqueta_cantidad, self._campo_cantidad)
        self._formulario.addRow(self._etiqueta_prefijo, self._campo_prefijo)
        self._formulario.addRow(self._error_prefijo)
        self._formulario.addRow(self._aviso_prefijo)

        self._botones = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        self._botones.accepted.connect(self._guardar)
        self._botones.rejected.connect(self.reject)

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(self._formulario)
        distribucion.addWidget(self._botones)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self._campo_cantidad.setFocus()

    def _revisar_prefijo(self) -> None:
        prefijo = self._campo_prefijo.text().strip()
        self._error_prefijo.setVisible(False)
        if prefijo and repo_lote.existe_prefijo(self._con, self._evento_id, prefijo):
            self._aviso_prefijo.setText(t("cartones.error.prefijo_repetido", prefijo=prefijo))
            self._aviso_prefijo.setVisible(True)
        else:
            self._aviso_prefijo.setVisible(False)

    def _guardar(self) -> None:
        prefijo = self._campo_prefijo.text().strip()
        if not prefijo:
            self._error_prefijo.setText(t("cartones.error.prefijo_vacio"))
            self._error_prefijo.setVisible(True)
            self._campo_prefijo.setFocus()
            return
        # El resto de la validación (charset, longitud, duplicado) corre de
        # todos modos dentro de `generar_lote`, en el hilo de la Tarea: si por
        # una carrera improbable falla ahí, se ve en la franja de la vista, no
        # aquí (el modal ya se cerró para entonces).
        self.resultado = (self._campo_cantidad.value(), prefijo)
        self.accept()

    def retraducir(self) -> None:
        self.setWindowTitle(t("cartones.formulario.titulo"))
        self._etiqueta_cantidad.setText(t("cartones.campo.cantidad"))
        self._etiqueta_prefijo.setText(t("cartones.campo.prefijo"))
        self._botones.button(QDialogButtonBox.StandardButton.Save).setText(t("comun.guardar"))
        self._botones.button(QDialogButtonBox.StandardButton.Cancel).setText(t("comun.cancelar"))


class _ModeloCartones(QAbstractTableModel):
    """Modelo de tabla mínimo: dos columnas (código, estado), sin caché más
    allá de la lista ya cargada — el listado de un evento cabe cómodo en
    memoria (miles de filas, no millones).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cartones: list[Carton] = []

    def establecer_cartones(self, cartones: list[Carton]) -> None:
        self.beginResetModel()
        self._cartones = cartones
        self.endResetModel()

    def carton_en(self, fila: int) -> Carton | None:
        if 0 <= fila < len(self._cartones):
            return self._cartones[fila]
        return None

    def rowCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802 - override Qt
        indice = parent if parent is not None else QModelIndex()
        return 0 if indice.isValid() else len(self._cartones)

    def columnCount(self, parent: QModelIndex | None = None) -> int:  # noqa: N802 - override Qt
        indice = parent if parent is not None else QModelIndex()
        return 0 if indice.isValid() else 2

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        carton = self._cartones[index.row()]
        if index.column() == 0:
            return carton.codigo
        return t(f"estado_carton.{carton.estado}")

    def headerData(  # noqa: N802 - override Qt
        self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole
    ) -> Any:
        if orientation != Qt.Orientation.Horizontal or role != Qt.ItemDataRole.DisplayRole:
            return None
        return t("cartones.columna.codigo") if section == 0 else t("cartones.filtro.estado")


class VistaCartones(QWidget):
    def __init__(self, con: Any, evento: Evento, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento
        self._tarea: Tarea | None = None
        self._marca_de_tiempo_progreso: float | None = None

        # --- Cabecera: resumen + acción ---
        self._etiquetas_resumen: dict[str | None, QLabel] = {}
        self._fila_resumen = QHBoxLayout()

        self._boton_generar = QPushButton()
        self._boton_generar.setObjectName("primario")
        self._boton_generar.clicked.connect(self._abrir_formulario_generar)
        self._boton_cancelar_tarea = QPushButton()
        self._boton_cancelar_tarea.setVisible(False)
        self._boton_cancelar_tarea.clicked.connect(self._cancelar_generacion)

        self._barra_progreso = QProgressBar()
        self._barra_progreso.setVisible(False)
        self._etiqueta_velocidad = QLabel()
        self._etiqueta_velocidad.setObjectName("etiquetaSecundaria")
        self._etiqueta_velocidad.setVisible(False)

        fila_accion = QHBoxLayout()
        fila_accion.addWidget(self._boton_generar)
        fila_accion.addWidget(self._barra_progreso, stretch=1)
        fila_accion.addWidget(self._etiqueta_velocidad)
        fila_accion.addWidget(self._boton_cancelar_tarea)

        self._franja = FranjaError()

        # --- Filtro + búsqueda ---
        self._combo_estado = QComboBox()
        self._combo_estado.currentIndexChanged.connect(self.cargar)
        self._campo_busqueda = QLineEdit()
        self._campo_busqueda.textChanged.connect(self.cargar)

        fila_filtro = QHBoxLayout()
        fila_filtro.addWidget(self._combo_estado)
        fila_filtro.addWidget(self._campo_busqueda, stretch=1)

        # --- Maestro-detalle ---
        self._modelo = _ModeloCartones(self)
        self._tabla = QTableView()
        self._tabla.setModel(self._modelo)
        self._tabla.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._tabla.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._tabla.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tabla.verticalHeader().setVisible(False)
        self._tabla.selectionModel().selectionChanged.connect(self._seleccion_cambiada)

        panel_izquierdo = QWidget()
        distribucion_izquierda = QVBoxLayout(panel_izquierdo)
        distribucion_izquierda.setContentsMargins(0, 0, 0, 0)
        distribucion_izquierda.addLayout(fila_filtro)
        distribucion_izquierda.addWidget(self._tabla, stretch=1)

        self._visor = CuadriculaCarton()

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(panel_izquierdo)
        self._splitter.addWidget(self._visor)
        self._splitter.setStretchFactor(0, 1)

        # --- Estado vacío ---
        self._etiqueta_vacio = QLabel()
        self._etiqueta_vacio.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._boton_vacio = QPushButton()
        self._boton_vacio.setObjectName("primario")
        self._boton_vacio.clicked.connect(self._abrir_formulario_generar)
        self._panel_vacio = QWidget()
        distribucion_vacio = QVBoxLayout(self._panel_vacio)
        distribucion_vacio.addStretch()
        distribucion_vacio.addWidget(self._etiqueta_vacio)
        distribucion_vacio.addWidget(self._boton_vacio, alignment=Qt.AlignmentFlag.AlignCenter)
        distribucion_vacio.addStretch()

        distribucion = QVBoxLayout(self)
        distribucion.addLayout(self._fila_resumen)
        distribucion.addLayout(fila_accion)
        distribucion.addWidget(self._franja)
        distribucion.addWidget(self._panel_vacio, stretch=1)
        distribucion.addWidget(self._splitter, stretch=1)

        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self.cargar()

    # --- Carga y filtro ---

    def cargar(self) -> None:
        self._franja.ocultar()
        try:
            conteo = repo_carton.contar_por_estado(self._con, self._evento.id)
            texto_busqueda = self._campo_busqueda.text().strip() or None
            estado = self._combo_estado.currentData()
            cartones = repo_carton.listar_por_evento(
                self._con,
                self._evento.id,
                estado=estado,
                texto_busqueda=texto_busqueda,
                limite=_FILAS_POR_PAGINA,
            )
        except ErrorBingo as error:
            self._franja.mostrar_error(error, on_reintentar=self.cargar)
            return

        self._actualizar_resumen(conteo)
        self._modelo.establecer_cartones(cartones)
        self._visor.limpiar()

        sin_cartones_en_total = sum(conteo.values()) == 0
        sin_resultados_por_filtro = not sin_cartones_en_total and len(cartones) == 0

        self._panel_vacio.setVisible(sin_cartones_en_total or sin_resultados_por_filtro)
        self._splitter.setVisible(not (sin_cartones_en_total or sin_resultados_por_filtro))
        if sin_cartones_en_total:
            self._etiqueta_vacio.setText(t("cartones.vacio.titulo"))
            self._boton_vacio.setVisible(True)
        elif sin_resultados_por_filtro:
            self._etiqueta_vacio.setText(t("cartones.vacio.filtro"))
            self._boton_vacio.setVisible(False)

    def _actualizar_resumen(self, conteo: dict[str, int]) -> None:
        total = sum(conteo.values())
        self._etiquetas_resumen[None].setText(t("cartones.resumen.total", total=total))
        for estado in _ESTADOS_CARTON:
            etiqueta = self._etiquetas_resumen[estado]
            cantidad = conteo.get(estado, 0)
            etiqueta.setText(f"{t(f'estado_carton.{estado}')} {cantidad}")
            etiqueta.setVisible(cantidad > 0)

    def _seleccion_cambiada(self) -> None:
        indices = self._tabla.selectionModel().selectedRows()
        if not indices:
            self._visor.limpiar()
            return
        carton = self._modelo.carton_en(indices[0].row())
        if carton is None:
            self._visor.limpiar()
            return
        self._visor.actualizar(carton_desde_orden_canonico(carton.numeros))

    # --- Generación de lotes ---

    def _abrir_formulario_generar(self) -> None:
        dialogo = FormularioGenerarLote(self._con, self._evento.id, parent=self)
        if dialogo.exec() != QDialog.DialogCode.Accepted or dialogo.resultado is None:
            return
        cantidad, prefijo = dialogo.resultado
        self._lanzar_tarea(cantidad, prefijo)

    def _lanzar_tarea(self, cantidad: int, prefijo: str) -> None:
        self._boton_generar.setEnabled(False)
        self._boton_generar.setVisible(False)
        self._boton_cancelar_tarea.setVisible(True)
        self._barra_progreso.setVisible(True)
        self._barra_progreso.setRange(0, cantidad)
        self._barra_progreso.setValue(0)
        self._etiqueta_velocidad.setVisible(True)
        self._marca_de_tiempo_progreso = time.monotonic()

        self._tarea = Tarea(_generar_lote_en_hilo, self._evento.id, cantidad, prefijo)
        self._tarea.progreso.connect(self._actualizar_progreso)
        self._tarea.terminado.connect(self._generacion_terminada)
        self._tarea.fallado.connect(self._generacion_fallada)
        self._tarea.start()

    def _cancelar_generacion(self) -> None:
        if self._tarea is not None:
            self._tarea.cancelar()
            self._boton_cancelar_tarea.setEnabled(False)

    def _actualizar_progreso(self, generados: int, total: int) -> None:
        self._barra_progreso.setValue(generados)
        ahora = time.monotonic()
        if self._marca_de_tiempo_progreso is not None and generados > 0:
            transcurrido = max(ahora - self._marca_de_tiempo_progreso, 0.001)
            velocidad = round(generados / transcurrido)
            self._etiqueta_velocidad.setText(
                t("cartones.progreso.velocidad", velocidad=velocidad)
                + "  ·  "
                + t("cartones.progreso", generados=generados, total=total)
            )

    def _restaurar_controles_de_generacion(self) -> None:
        self._boton_generar.setEnabled(True)
        self._boton_generar.setVisible(True)
        self._boton_cancelar_tarea.setVisible(False)
        self._boton_cancelar_tarea.setEnabled(True)
        self._barra_progreso.setVisible(False)
        self._etiqueta_velocidad.setVisible(False)
        self._tarea = None

    def _generacion_terminada(self, resultado: object) -> None:
        # `resultado` es el `Lote` que devuelve `generar_lote`: cancelado
        # (nunca llega a marcarse completo) o terminado con éxito. Se lee del
        # propio objeto en vez de inferirlo del valor de la barra de progreso
        # — la barra puede quedar a mitad si la cancelación llegó tras varios
        # bloques ya insertados.
        cancelada = getattr(resultado, "completado_en", None) is None
        self._restaurar_controles_de_generacion()
        self.cargar()
        if cancelada:
            self._franja.mostrar(t("cartones.aviso.cancelado"))
        else:
            self._franja.mostrar(t("cartones.exito.lote_generado"))

    def _generacion_fallada(self, error: ErrorBingo) -> None:
        self._restaurar_controles_de_generacion()
        self._franja.mostrar_error(error)

    # --- i18n ---

    def retraducir(self) -> None:
        self._boton_generar.setText(t("cartones.generar_lote"))
        self._boton_cancelar_tarea.setText(t("cartones.accion.cancelar"))
        self._boton_vacio.setText(t("cartones.generar_lote"))
        self._campo_busqueda.setPlaceholderText(t("cartones.buscar_codigo"))

        estado_actual = self._combo_estado.currentData() if self._combo_estado.count() else None
        self._combo_estado.blockSignals(True)
        self._combo_estado.clear()
        self._combo_estado.addItem(t("cartones.filtro.todos"), None)
        for estado in _ESTADOS_CARTON:
            self._combo_estado.addItem(t(f"estado_carton.{estado}"), estado)
        indice = self._combo_estado.findData(estado_actual)
        self._combo_estado.setCurrentIndex(indice if indice >= 0 else 0)
        self._combo_estado.blockSignals(False)

        if None not in self._etiquetas_resumen:
            self._etiquetas_resumen[None] = QLabel()
            self._fila_resumen.addWidget(self._etiquetas_resumen[None])
            for estado in _ESTADOS_CARTON:
                etiqueta = QLabel()
                etiqueta.setObjectName("etiquetaSecundaria")
                self._etiquetas_resumen[estado] = etiqueta
                self._fila_resumen.addWidget(etiqueta)
            self._fila_resumen.addStretch()
        self._modelo.headerDataChanged.emit(Qt.Orientation.Horizontal, 0, 1)
