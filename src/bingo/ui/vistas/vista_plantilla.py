"""Sección "Plantilla" del espacio de trabajo del evento (contrato de la fase
3, §3.4). Editor agrupado por secciones (marca, textos, identificación,
estructura, hoja) a la izquierda; vista previa a la derecha, en un
`QSplitter` — mismo esquema maestro-detalle que `vista_cartones.py`.

La vista previa **no** es una aproximación dibujada con Qt: usa el mismo
`MotorRenderCarton` que produce el PDF final, renderiza un PDF de una sola
carta en memoria y lo rasteriza con `PySide6.QtPdf.QPdfDocument` (decisión D4,
`docs/Fase_3/Plan_Implementacion_Fase3.md` §3) — así lo que se ve en pantalla
es literalmente una página del PDF que se imprimiría.

Cada cambio de campo actualiza la plantilla en memoria y reinicia un
temporizador de un solo disparo (`RETARDO_VISTA_PREVIA_MS`): al vencer, se
valida, se guarda (`repo_evento.actualizar_plantilla`, ya existe desde la
fase 1) y se refresca la vista previa. Guardar y refrescar comparten el mismo
temporizador para no escribir en la base ni re-renderizar en cada tecla.
"""

from __future__ import annotations

import io
from pathlib import Path
from random import Random
from typing import Any

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QSize, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from reportlab.pdfgen.canvas import Canvas

from bingo import i18n
from bingo.config.ajustes import (
    CARTONES_POR_HOJA_SOPORTADOS,
    LADO_MAX_LOGO,
    RETARDO_VISTA_PREVIA_MS,
    TAMANOS_HOJA_SOPORTADOS,
)
from bingo.config.rutas import dir_medios_evento
from bingo.dominio.carton import generar_carton
from bingo.dominio.modelos import Evento
from bingo.i18n import t
from bingo.impresion.plantilla import (
    PlantillaCarton,
    restablecer_marca_desde_organizacion,
    validar,
)
from bingo.impresion.render_pdf import MotorRenderCarton
from bingo.persistencia import repo_evento, repo_organizacion
from bingo.servicios import servicio_eventos
from bingo.ui.dialogos import FranjaError
from bingo.ui.vistas.vista_organizaciones import BotonColor
from bingo.utilidades.errores import ErrorBingo, ErrorValidacion
from bingo.utilidades.imagenes import validar_y_normalizar

_DPI_VISTA_PREVIA = 150
_CODIGO_EJEMPLO = "EJEMPLO-000001"
_SEMILLA_EJEMPLO = "vista-previa-plantilla"

_ORIENTACIONES = (
    ("vertical", "plantilla.orientacion.vertical"),
    ("horizontal", "plantilla.orientacion.horizontal"),
)
_LOGO_POSICIONES = (
    ("superior_izquierda", "plantilla.pos.superior_izquierda"),
    ("superior_centro", "plantilla.pos.superior_centro"),
    ("superior_derecha", "plantilla.pos.superior_derecha"),
)
_IDENTIFICACION_POSICIONES = (
    ("inferior_izquierda", "plantilla.pos.inferior_izquierda"),
    ("inferior_centro", "plantilla.pos.inferior_centro"),
    ("inferior_derecha", "plantilla.pos.inferior_derecha"),
)
_LIBRE_TIPOS = (
    ("texto", "plantilla.libre_tipo.texto"),
    ("estrella", "plantilla.libre_tipo.estrella"),
    ("logo", "plantilla.libre_tipo.logo"),
)
_FUENTES_DISPONIBLES = ("Helvetica-Bold", "Merriweather", "Open Sans")
_FILTRO_IMAGENES = "Imágenes (*.png *.jpg *.jpeg *.bmp)"


def _llenar_combo(combo: QComboBox, opciones: tuple[tuple[str, str], ...]) -> None:
    actual = combo.currentData() if combo.count() else None
    combo.blockSignals(True)
    combo.clear()
    for valor, clave in opciones:
        combo.addItem(t(clave), valor)
    indice = combo.findData(actual)
    combo.setCurrentIndex(indice if indice >= 0 else 0)
    combo.blockSignals(False)


class VistaPlantilla(QWidget):
    def __init__(self, con: Any, evento: Evento, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento
        self._actualizando_formulario = False
        self._doc_previa: QPdfDocument | None = None
        self._buffer_previa: QBuffer | None = None

        self._franja = FranjaError()
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.setInterval(RETARDO_VISTA_PREVIA_MS)
        self._temporizador.timeout.connect(self._guardar_y_previsualizar)

        self._construir_formulario()

        self._etiqueta_previa = QLabel()
        self._etiqueta_previa.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._etiqueta_previa.setMinimumWidth(260)
        self._etiqueta_previa.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        contenedor_previa = QWidget()
        distribucion_previa = QVBoxLayout(contenedor_previa)
        self._titulo_previa = QLabel()
        distribucion_previa.addWidget(self._titulo_previa)
        distribucion_previa.addWidget(self._etiqueta_previa, stretch=1)

        area_formulario = QScrollArea()
        area_formulario.setWidgetResizable(True)
        area_formulario.setWidget(self._panel_formulario)

        self._splitter = QSplitter(Qt.Orientation.Horizontal)
        self._splitter.addWidget(area_formulario)
        self._splitter.addWidget(contenedor_previa)
        self._splitter.setStretchFactor(0, 1)
        self._splitter.setStretchFactor(1, 1)

        distribucion = QVBoxLayout(self)
        distribucion.addWidget(self._franja)
        distribucion.addWidget(self._splitter, stretch=1)

        plantilla_inicial = (
            PlantillaCarton.desde_json(evento.plantilla_json)
            if evento.plantilla_json
            else PlantillaCarton.por_defecto(self._organizacion())
        )
        self._cargar_en_formulario(plantilla_inicial)
        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self._guardar_y_previsualizar()

    # --- Organización asociada -------------------------------------------------

    def _organizacion(self):
        return repo_organizacion.obtener(self._con, self._evento.organizacion_id)

    # --- Construcción del formulario -------------------------------------------

    def _construir_formulario(self) -> None:
        self._panel_formulario = QWidget()
        distribucion = QVBoxLayout(self._panel_formulario)

        # --- Hoja ---
        self._grupo_hoja = QGroupBox()
        formulario_hoja = QFormLayout()
        self._combo_tamano = QComboBox()
        self._combo_tamano.addItems(TAMANOS_HOJA_SOPORTADOS)
        self._combo_tamano.currentIndexChanged.connect(self._marcar_cambio)
        self._combo_orientacion = QComboBox()
        self._combo_orientacion.currentIndexChanged.connect(self._marcar_cambio)
        self._combo_cartones_por_hoja = QComboBox()
        for cantidad in CARTONES_POR_HOJA_SOPORTADOS:
            self._combo_cartones_por_hoja.addItem(str(cantidad), cantidad)
        self._combo_cartones_por_hoja.currentIndexChanged.connect(self._marcar_cambio)
        self._spin_margen = QDoubleSpinBox()
        self._spin_margen.setRange(1.0, 50.0)
        self._spin_margen.setSuffix(" mm")
        self._spin_margen.valueChanged.connect(self._marcar_cambio)
        self._check_marcas_corte = QCheckBox()
        self._check_marcas_corte.toggled.connect(self._marcar_cambio)
        self._etiqueta_tamano = QLabel()
        self._etiqueta_orientacion = QLabel()
        self._etiqueta_cartones_por_hoja = QLabel()
        self._etiqueta_margen = QLabel()
        formulario_hoja.addRow(self._etiqueta_tamano, self._combo_tamano)
        formulario_hoja.addRow(self._etiqueta_orientacion, self._combo_orientacion)
        formulario_hoja.addRow(self._etiqueta_cartones_por_hoja, self._combo_cartones_por_hoja)
        formulario_hoja.addRow(self._etiqueta_margen, self._spin_margen)
        formulario_hoja.addRow(self._check_marcas_corte)
        self._grupo_hoja.setLayout(formulario_hoja)

        # --- Marca ---
        self._grupo_marca = QGroupBox()
        formulario_marca = QFormLayout()
        self._boton_logo, self._etiqueta_logo = self._crear_selector_logo()
        self._boton_logo.clicked.connect(
            lambda: self._cargar_logo("logo_marca.png", secundario=False)
        )
        self._combo_logo_pos = QComboBox()
        self._combo_logo_pos.currentIndexChanged.connect(self._marcar_cambio)
        self._spin_logo_alto = QDoubleSpinBox()
        self._spin_logo_alto.setRange(5.0, 80.0)
        self._spin_logo_alto.setSuffix(" mm")
        self._spin_logo_alto.valueChanged.connect(self._marcar_cambio)
        self._boton_logo_secundario, self._etiqueta_logo_secundario = self._crear_selector_logo()
        self._boton_logo_secundario.clicked.connect(
            lambda: self._cargar_logo("logo_secundario.png", secundario=True)
        )
        self._campo_titulo = QLineEdit()
        self._campo_titulo.textChanged.connect(self._marcar_cambio)
        self._campo_subtitulo = QLineEdit()
        self._campo_subtitulo.textChanged.connect(self._marcar_cambio)
        self._color_encabezado = BotonColor("#1a1a2e")
        self._color_encabezado.clicked.connect(self._marcar_cambio)
        self._color_grilla = BotonColor("#333333")
        self._color_grilla.clicked.connect(self._marcar_cambio)
        self._boton_fondo, self._etiqueta_fondo = self._crear_selector_logo()
        self._boton_fondo.clicked.connect(lambda: self._cargar_logo("fondo.png", fondo=True))
        self._spin_opacidad_fondo = QDoubleSpinBox()
        self._spin_opacidad_fondo.setRange(0.0, 1.0)
        self._spin_opacidad_fondo.setSingleStep(0.05)
        self._spin_opacidad_fondo.valueChanged.connect(self._marcar_cambio)
        self._boton_restablecer = QPushButton()
        self._boton_restablecer.clicked.connect(self._restablecer_desde_organizacion)

        self._etiqueta_logo_campo = QLabel()
        self._etiqueta_logo_pos = QLabel()
        self._etiqueta_logo_alto = QLabel()
        self._etiqueta_logo_secundario_campo = QLabel()
        self._etiqueta_titulo = QLabel()
        self._etiqueta_subtitulo = QLabel()
        self._etiqueta_color_encabezado = QLabel()
        self._etiqueta_color_grilla = QLabel()
        self._etiqueta_fondo_campo = QLabel()
        self._etiqueta_opacidad_fondo = QLabel()

        fila_logo = QHBoxLayout()
        fila_logo.addWidget(self._boton_logo)
        fila_logo.addWidget(self._etiqueta_logo)
        fila_logo_secundario = QHBoxLayout()
        fila_logo_secundario.addWidget(self._boton_logo_secundario)
        fila_logo_secundario.addWidget(self._etiqueta_logo_secundario)
        fila_fondo = QHBoxLayout()
        fila_fondo.addWidget(self._boton_fondo)
        fila_fondo.addWidget(self._etiqueta_fondo)

        formulario_marca.addRow(self._etiqueta_logo_campo, fila_logo)
        formulario_marca.addRow(self._etiqueta_logo_pos, self._combo_logo_pos)
        formulario_marca.addRow(self._etiqueta_logo_alto, self._spin_logo_alto)
        formulario_marca.addRow(self._etiqueta_logo_secundario_campo, fila_logo_secundario)
        formulario_marca.addRow(self._etiqueta_titulo, self._campo_titulo)
        formulario_marca.addRow(self._etiqueta_subtitulo, self._campo_subtitulo)
        formulario_marca.addRow(self._etiqueta_color_encabezado, self._color_encabezado)
        formulario_marca.addRow(self._etiqueta_color_grilla, self._color_grilla)
        formulario_marca.addRow(self._etiqueta_fondo_campo, fila_fondo)
        formulario_marca.addRow(self._etiqueta_opacidad_fondo, self._spin_opacidad_fondo)
        formulario_marca.addRow(self._boton_restablecer)
        self._grupo_marca.setLayout(formulario_marca)

        # --- Encabezado y espacio libre ---
        self._grupo_encabezado = QGroupBox()
        formulario_encabezado = QFormLayout()
        self._check_mostrar_encabezado = QCheckBox()
        self._check_mostrar_encabezado.toggled.connect(self._marcar_cambio)
        self._campos_letras: list[QLineEdit] = []
        fila_letras = QHBoxLayout()
        for _ in range(5):
            campo = QLineEdit()
            campo.setMaxLength(2)
            campo.setFixedWidth(32)
            campo.textChanged.connect(self._marcar_cambio)
            self._campos_letras.append(campo)
            fila_letras.addWidget(campo)
        self._combo_libre_tipo = QComboBox()
        self._combo_libre_tipo.currentIndexChanged.connect(self._marcar_cambio)
        self._campo_libre_texto = QLineEdit()
        self._campo_libre_texto.textChanged.connect(self._marcar_cambio)
        self._etiqueta_encabezado_letras = QLabel()
        self._etiqueta_libre_tipo = QLabel()
        self._etiqueta_libre_texto = QLabel()
        formulario_encabezado.addRow(self._check_mostrar_encabezado)
        formulario_encabezado.addRow(self._etiqueta_encabezado_letras, fila_letras)
        formulario_encabezado.addRow(self._etiqueta_libre_tipo, self._combo_libre_tipo)
        formulario_encabezado.addRow(self._etiqueta_libre_texto, self._campo_libre_texto)
        self._grupo_encabezado.setLayout(formulario_encabezado)

        # --- Números ---
        self._grupo_numeros = QGroupBox()
        formulario_numeros = QFormLayout()
        self._combo_fuente = QComboBox()
        self._combo_fuente.addItems(_FUENTES_DISPONIBLES)
        self._combo_fuente.currentIndexChanged.connect(self._marcar_cambio)
        self._spin_tamano_numeros = QSpinBox()
        self._spin_tamano_numeros.setRange(6, 60)
        self._spin_tamano_numeros.setSuffix(" pt")
        self._spin_tamano_numeros.valueChanged.connect(self._marcar_cambio)
        self._etiqueta_fuente = QLabel()
        self._etiqueta_tamano_numeros = QLabel()
        formulario_numeros.addRow(self._etiqueta_fuente, self._combo_fuente)
        formulario_numeros.addRow(self._etiqueta_tamano_numeros, self._spin_tamano_numeros)
        self._grupo_numeros.setLayout(formulario_numeros)

        # --- Identificación ---
        self._grupo_identificacion = QGroupBox()
        formulario_identificacion = QFormLayout()
        self._check_mostrar_codigo = QCheckBox()
        self._check_mostrar_codigo.toggled.connect(self._marcar_cambio)
        self._combo_identificacion_pos = QComboBox()
        self._combo_identificacion_pos.currentIndexChanged.connect(self._marcar_cambio)
        self._check_qr = QCheckBox()
        self._check_qr.toggled.connect(self._marcar_cambio)
        self._check_marca_agua = QCheckBox()
        self._check_marca_agua.toggled.connect(self._marcar_cambio)
        self._spin_opacidad_marca_agua = QDoubleSpinBox()
        self._spin_opacidad_marca_agua.setRange(0.0, 1.0)
        self._spin_opacidad_marca_agua.setSingleStep(0.02)
        self._spin_opacidad_marca_agua.valueChanged.connect(self._marcar_cambio)
        self._etiqueta_identificacion_pos = QLabel()
        self._etiqueta_opacidad_marca_agua = QLabel()
        formulario_identificacion.addRow(self._check_mostrar_codigo)
        formulario_identificacion.addRow(
            self._etiqueta_identificacion_pos, self._combo_identificacion_pos
        )
        formulario_identificacion.addRow(self._check_qr)
        formulario_identificacion.addRow(self._check_marca_agua)
        formulario_identificacion.addRow(
            self._etiqueta_opacidad_marca_agua, self._spin_opacidad_marca_agua
        )
        self._grupo_identificacion.setLayout(formulario_identificacion)

        # --- Textos ---
        self._grupo_textos = QGroupBox()
        formulario_textos = QFormLayout()
        self._campo_texto_superior = QLineEdit()
        self._campo_texto_superior.textChanged.connect(self._marcar_cambio)
        self._campo_texto_inferior = QLineEdit()
        self._campo_texto_inferior.textChanged.connect(self._marcar_cambio)
        self._campo_contacto = QLineEdit()
        self._campo_contacto.textChanged.connect(self._marcar_cambio)
        self._etiqueta_texto_superior = QLabel()
        self._etiqueta_texto_inferior = QLabel()
        self._etiqueta_contacto = QLabel()
        formulario_textos.addRow(self._etiqueta_texto_superior, self._campo_texto_superior)
        formulario_textos.addRow(self._etiqueta_texto_inferior, self._campo_texto_inferior)
        formulario_textos.addRow(self._etiqueta_contacto, self._campo_contacto)
        self._grupo_textos.setLayout(formulario_textos)

        distribucion.addWidget(self._grupo_marca)
        distribucion.addWidget(self._grupo_textos)
        distribucion.addWidget(self._grupo_identificacion)
        distribucion.addWidget(self._grupo_encabezado)
        distribucion.addWidget(self._grupo_numeros)
        distribucion.addWidget(self._grupo_hoja)
        distribucion.addStretch()

    def _crear_selector_logo(self) -> tuple[QPushButton, QLabel]:
        boton = QPushButton()
        etiqueta = QLabel("—")
        etiqueta.setFixedSize(40, 40)
        etiqueta.setScaledContents(True)
        etiqueta.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return boton, etiqueta

    # --- Formulario <-> PlantillaCarton -----------------------------------------

    def _leer_formulario(self) -> PlantillaCarton:
        plantilla = PlantillaCarton()
        plantilla.hoja.tamano = self._combo_tamano.currentText()
        plantilla.hoja.orientacion = self._combo_orientacion.currentData() or "vertical"
        plantilla.hoja.cartones_por_hoja = self._combo_cartones_por_hoja.currentData() or 4
        plantilla.hoja.margen_mm = self._spin_margen.value()
        plantilla.hoja.marcas_corte = self._check_marcas_corte.isChecked()

        plantilla.marca.logo = self._logo_actual
        plantilla.marca.logo_secundario = self._logo_secundario_actual
        plantilla.marca.logo_pos = self._combo_logo_pos.currentData() or "superior_izquierda"
        plantilla.marca.logo_alto_mm = self._spin_logo_alto.value()
        plantilla.marca.titulo = self._campo_titulo.text().strip()
        plantilla.marca.subtitulo = self._campo_subtitulo.text().strip()
        plantilla.marca.color_encabezado = self._color_encabezado.color
        plantilla.marca.color_grilla = self._color_grilla.color
        plantilla.marca.fondo = self._fondo_actual
        plantilla.marca.opacidad_fondo = self._spin_opacidad_fondo.value()

        plantilla.encabezado.mostrar = self._check_mostrar_encabezado.isChecked()
        letras = [
            campo.text().strip().upper() or letra
            for campo, letra in zip(self._campos_letras, ("B", "I", "N", "G", "O"), strict=True)
        ]
        plantilla.encabezado.letras = letras

        plantilla.libre.tipo = self._combo_libre_tipo.currentData() or "texto"
        plantilla.libre.texto = self._campo_libre_texto.text().strip() or "LIBRE"

        plantilla.numeros.fuente = self._combo_fuente.currentText()
        plantilla.numeros.tamano_pt = float(self._spin_tamano_numeros.value())

        plantilla.identificacion.mostrar_codigo = self._check_mostrar_codigo.isChecked()
        plantilla.identificacion.pos = (
            self._combo_identificacion_pos.currentData() or "inferior_derecha"
        )
        plantilla.identificacion.qr = self._check_qr.isChecked()
        plantilla.identificacion.marca_agua = self._check_marca_agua.isChecked()
        plantilla.identificacion.opacidad_marca_agua = self._spin_opacidad_marca_agua.value()

        plantilla.textos.superior = self._campo_texto_superior.text().strip()
        plantilla.textos.inferior = self._campo_texto_inferior.text().strip()
        plantilla.textos.contacto = self._campo_contacto.text().strip()
        return plantilla

    def _cargar_en_formulario(self, plantilla: PlantillaCarton) -> None:
        self._actualizando_formulario = True
        try:
            _llenar_combo(self._combo_orientacion, _ORIENTACIONES)
            _llenar_combo(self._combo_logo_pos, _LOGO_POSICIONES)
            _llenar_combo(self._combo_identificacion_pos, _IDENTIFICACION_POSICIONES)
            _llenar_combo(self._combo_libre_tipo, _LIBRE_TIPOS)

            indice = self._combo_tamano.findText(plantilla.hoja.tamano)
            self._combo_tamano.setCurrentIndex(indice if indice >= 0 else 0)
            indice = self._combo_orientacion.findData(plantilla.hoja.orientacion)
            self._combo_orientacion.setCurrentIndex(indice if indice >= 0 else 0)
            indice = self._combo_cartones_por_hoja.findData(plantilla.hoja.cartones_por_hoja)
            self._combo_cartones_por_hoja.setCurrentIndex(indice if indice >= 0 else 0)
            self._spin_margen.setValue(plantilla.hoja.margen_mm)
            self._check_marcas_corte.setChecked(plantilla.hoja.marcas_corte)

            self._logo_actual = plantilla.marca.logo
            self._logo_secundario_actual = plantilla.marca.logo_secundario
            self._fondo_actual = plantilla.marca.fondo
            self._actualizar_previa_logo(self._etiqueta_logo, self._logo_actual)
            self._actualizar_previa_logo(
                self._etiqueta_logo_secundario, self._logo_secundario_actual
            )
            self._actualizar_previa_logo(self._etiqueta_fondo, self._fondo_actual)
            indice = self._combo_logo_pos.findData(plantilla.marca.logo_pos)
            self._combo_logo_pos.setCurrentIndex(indice if indice >= 0 else 0)
            self._spin_logo_alto.setValue(plantilla.marca.logo_alto_mm)
            self._campo_titulo.setText(plantilla.marca.titulo)
            self._campo_subtitulo.setText(plantilla.marca.subtitulo)
            self._color_encabezado.establecer_color(plantilla.marca.color_encabezado)
            self._color_grilla.establecer_color(plantilla.marca.color_grilla)
            self._spin_opacidad_fondo.setValue(plantilla.marca.opacidad_fondo)

            self._check_mostrar_encabezado.setChecked(plantilla.encabezado.mostrar)
            letras = (
                plantilla.encabezado.letras
                if len(plantilla.encabezado.letras) == 5
                else list("BINGO")
            )
            for campo, letra in zip(self._campos_letras, letras, strict=True):
                campo.setText(letra)

            indice = self._combo_libre_tipo.findData(plantilla.libre.tipo)
            self._combo_libre_tipo.setCurrentIndex(indice if indice >= 0 else 0)
            self._campo_libre_texto.setText(plantilla.libre.texto)

            indice = self._combo_fuente.findText(plantilla.numeros.fuente)
            self._combo_fuente.setCurrentIndex(indice if indice >= 0 else 0)
            self._spin_tamano_numeros.setValue(round(plantilla.numeros.tamano_pt))

            self._check_mostrar_codigo.setChecked(plantilla.identificacion.mostrar_codigo)
            indice = self._combo_identificacion_pos.findData(plantilla.identificacion.pos)
            self._combo_identificacion_pos.setCurrentIndex(indice if indice >= 0 else 0)
            self._check_qr.setChecked(plantilla.identificacion.qr)
            self._check_marca_agua.setChecked(plantilla.identificacion.marca_agua)
            self._spin_opacidad_marca_agua.setValue(plantilla.identificacion.opacidad_marca_agua)

            self._campo_texto_superior.setText(plantilla.textos.superior)
            self._campo_texto_inferior.setText(plantilla.textos.inferior)
            self._campo_contacto.setText(plantilla.textos.contacto)
        finally:
            self._actualizando_formulario = False
        self._plantilla = plantilla

    def _actualizar_previa_logo(self, etiqueta: QLabel, ruta: str | None) -> None:
        if ruta and Path(ruta).exists():
            etiqueta.setPixmap(QPixmap(ruta))
        else:
            etiqueta.setPixmap(QPixmap())
            etiqueta.setText("—")

    # --- Cambios ------------------------------------------------------------

    def _marcar_cambio(self, *_args: object) -> None:
        if self._actualizando_formulario:
            return
        self._plantilla = self._leer_formulario()
        self._temporizador.start()

    def _cargar_logo(
        self, nombre_archivo: str, *, secundario: bool = False, fondo: bool = False
    ) -> None:
        ruta, _ = QFileDialog.getOpenFileName(
            self, t("plantilla.accion.cargar_logo"), "", _FILTRO_IMAGENES
        )
        if not ruta:
            return
        destino = dir_medios_evento(self._evento.id) / nombre_archivo
        try:
            resultado = validar_y_normalizar(Path(ruta), destino, lado_max=LADO_MAX_LOGO)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return

        if fondo:
            self._fondo_actual = str(resultado)
            self._actualizar_previa_logo(self._etiqueta_fondo, self._fondo_actual)
        elif secundario:
            self._logo_secundario_actual = str(resultado)
            self._actualizar_previa_logo(
                self._etiqueta_logo_secundario, self._logo_secundario_actual
            )
        else:
            self._logo_actual = str(resultado)
            self._actualizar_previa_logo(self._etiqueta_logo, self._logo_actual)
        self._marcar_cambio()

    def _restablecer_desde_organizacion(self) -> None:
        organizacion = self._organizacion()
        if organizacion is None:
            return
        nueva = restablecer_marca_desde_organizacion(self._leer_formulario(), organizacion)
        self._cargar_en_formulario(nueva)
        self._guardar_y_previsualizar()

    # --- Guardado y vista previa ----------------------------------------------

    def _guardar_y_previsualizar(self) -> None:
        try:
            validar(self._plantilla)
        except ErrorValidacion as error:
            self._franja.mostrar(t(error.clave_i18n, **error.parametros))
            return

        try:
            repo_evento.actualizar_plantilla(self._con, self._evento.id, self._plantilla.a_json())
        except ErrorBingo as error:
            self._franja.mostrar_error(error, on_reintentar=self._guardar_y_previsualizar)
            return
        self._franja.ocultar()
        self._actualizar_vista_previa()

    def _actualizar_vista_previa(self) -> None:
        organizacion = self._organizacion()
        if organizacion is None:
            return
        try:
            clave_evento = servicio_eventos.asegurar_clave_evento(self._con, self._evento.id)
        except ErrorBingo:
            return

        motor = MotorRenderCarton(self._plantilla, organizacion, clave_evento)
        matriz = generar_carton(Random(_SEMILLA_EJEMPLO))
        _, _, ancho_celda, alto_celda = motor.calcular_disposicion()[0]

        buffer_pdf = io.BytesIO()
        canvas = Canvas(buffer_pdf, pagesize=(ancho_celda, alto_celda))
        motor.dibujar_carton(canvas, _CODIGO_EJEMPLO, matriz, 0, 0, ancho_celda, alto_celda)
        canvas.showPage()
        canvas.save()

        buffer_qt = QBuffer()
        buffer_qt.setData(QByteArray(buffer_pdf.getvalue()))
        buffer_qt.open(QIODevice.OpenModeFlag.ReadOnly)
        documento = QPdfDocument()
        documento.load(buffer_qt)
        if documento.pageCount() < 1:
            return

        tamano_punto = documento.pagePointSize(0)
        ancho_px = max(1, round(tamano_punto.width() / 72 * _DPI_VISTA_PREVIA))
        alto_px = max(1, round(tamano_punto.height() / 72 * _DPI_VISTA_PREVIA))
        imagen = documento.render(0, QSize(ancho_px, alto_px))
        self._etiqueta_previa.setPixmap(QPixmap.fromImage(imagen))
        # Se guardan como atributos para que no los recoja el recolector de
        # basura mientras Qt todavía pueda referenciarlos internamente.
        self._buffer_previa = buffer_qt
        self._doc_previa = documento

    # --- i18n -----------------------------------------------------------------

    def retraducir(self) -> None:
        self._titulo_previa.setText(t("plantilla.vista_previa.titulo"))
        self._grupo_hoja.setTitle(t("plantilla.seccion.hoja"))
        self._grupo_marca.setTitle(t("plantilla.seccion.marca"))
        self._grupo_encabezado.setTitle(t("plantilla.seccion.encabezado"))
        self._grupo_numeros.setTitle(t("plantilla.seccion.numeros"))
        self._grupo_identificacion.setTitle(t("plantilla.seccion.identificacion"))
        self._grupo_textos.setTitle(t("plantilla.seccion.textos"))

        self._etiqueta_tamano.setText(t("plantilla.campo.tamano_hoja"))
        self._etiqueta_orientacion.setText(t("plantilla.campo.orientacion"))
        self._etiqueta_cartones_por_hoja.setText(t("plantilla.campo.cartones_por_hoja"))
        self._etiqueta_margen.setText(t("plantilla.campo.margen_mm"))
        self._check_marcas_corte.setText(t("plantilla.campo.marcas_corte"))

        self._etiqueta_logo_campo.setText(t("plantilla.campo.logo"))
        self._boton_logo.setText(t("plantilla.accion.cargar_logo"))
        self._etiqueta_logo_pos.setText(t("plantilla.campo.logo_pos"))
        self._etiqueta_logo_alto.setText(t("plantilla.campo.logo_alto_mm"))
        self._etiqueta_logo_secundario_campo.setText(t("plantilla.campo.logo_secundario"))
        self._boton_logo_secundario.setText(t("plantilla.accion.cargar_logo"))
        self._etiqueta_titulo.setText(t("plantilla.campo.titulo"))
        self._etiqueta_subtitulo.setText(t("plantilla.campo.subtitulo"))
        self._etiqueta_color_encabezado.setText(t("plantilla.campo.color_encabezado"))
        self._etiqueta_color_grilla.setText(t("plantilla.campo.color_grilla"))
        self._etiqueta_fondo_campo.setText(t("plantilla.campo.fondo"))
        self._boton_fondo.setText(t("plantilla.accion.cargar_logo"))
        self._etiqueta_opacidad_fondo.setText(t("plantilla.campo.opacidad_fondo"))
        self._boton_restablecer.setText(t("plantilla.accion.restablecer_marca"))

        self._check_mostrar_encabezado.setText(t("plantilla.campo.encabezado_mostrar"))
        self._etiqueta_encabezado_letras.setText(t("plantilla.campo.encabezado_letras"))
        self._etiqueta_libre_tipo.setText(t("plantilla.campo.libre_tipo"))
        self._etiqueta_libre_texto.setText(t("plantilla.campo.libre_texto"))

        self._etiqueta_fuente.setText(t("plantilla.campo.fuente_numeros"))
        self._etiqueta_tamano_numeros.setText(t("plantilla.campo.tamano_numeros"))

        self._check_mostrar_codigo.setText(t("plantilla.campo.mostrar_codigo"))
        self._etiqueta_identificacion_pos.setText(t("plantilla.campo.identificacion_pos"))
        self._check_qr.setText(t("plantilla.campo.qr"))
        self._check_marca_agua.setText(t("plantilla.campo.marca_agua"))
        self._etiqueta_opacidad_marca_agua.setText(t("plantilla.campo.opacidad_marca_agua"))

        self._etiqueta_texto_superior.setText(t("plantilla.campo.texto_superior"))
        self._campo_texto_superior.setPlaceholderText(t("plantilla.campo.texto_superior"))
        self._etiqueta_texto_inferior.setText(t("plantilla.campo.texto_inferior"))
        self._campo_texto_inferior.setPlaceholderText(t("plantilla.campo.texto_inferior"))
        self._etiqueta_contacto.setText(t("plantilla.campo.contacto"))
        self._campo_contacto.setPlaceholderText(t("plantilla.campo.contacto"))

        actual_orientacion = self._combo_orientacion.currentData()
        actual_logo_pos = self._combo_logo_pos.currentData()
        actual_ident_pos = self._combo_identificacion_pos.currentData()
        actual_libre_tipo = self._combo_libre_tipo.currentData()
        _llenar_combo(self._combo_orientacion, _ORIENTACIONES)
        _llenar_combo(self._combo_logo_pos, _LOGO_POSICIONES)
        _llenar_combo(self._combo_identificacion_pos, _IDENTIFICACION_POSICIONES)
        _llenar_combo(self._combo_libre_tipo, _LIBRE_TIPOS)
        for combo, valor in (
            (self._combo_orientacion, actual_orientacion),
            (self._combo_logo_pos, actual_logo_pos),
            (self._combo_identificacion_pos, actual_ident_pos),
            (self._combo_libre_tipo, actual_libre_tipo),
        ):
            if valor is not None:
                indice = combo.findData(valor)
                if indice >= 0:
                    combo.blockSignals(True)
                    combo.setCurrentIndex(indice)
                    combo.blockSignals(False)
