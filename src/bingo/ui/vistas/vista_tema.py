"""Sección "Tema" del espacio de trabajo del evento (contrato de la fase 4,
§4.8; decisión D9 y D.2 del plan de la fase 4).

Vista previa deliberadamente **no WYSIWYG** (decisión D9, riesgo aceptado
explícitamente): un `QWidget` pintado a escala de un lienzo de referencia
1920x1080 dibuja rectángulos etiquetados en la posición/escala/color de cada
bloque. Muestra fielmente *dónde* va cada cosa y de qué color, no el
contenido en vivo (bombo animado, tablero real) — eso lo dibuja la ventana de
transmisión de la fase 5, que puede sustituir estos rectángulos por los
widgets reales sin tocar el modelo ni este editor.

Mismo patrón de guardado que `vista_plantilla.py`: cada cambio de campo
actualiza el tema en memoria y reinicia un temporizador de un solo disparo
(`RETARDO_VISTA_PREVIA_MS`); al vencer, se valida y se guarda con
`repo_evento.actualizar_tema` (ya existe desde antes de esta fase).
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
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

from bingo import i18n
from bingo.config.ajustes import LADO_MAX_LOGO, RETARDO_VISTA_PREVIA_MS
from bingo.config.rutas import dir_medios_evento
from bingo.dominio.modelos import Evento
from bingo.dominio.tema import ConfigBloque, TemaDashboard, validar
from bingo.i18n import t
from bingo.persistencia import repo_evento
from bingo.ui.dialogos import FranjaError
from bingo.ui.vistas.vista_organizaciones import BotonColor
from bingo.utilidades.errores import ErrorBingo, ErrorValidacion
from bingo.utilidades.imagenes import validar_y_normalizar

_ANCHO_REFERENCIA = 1920
_ALTO_REFERENCIA = 1080
_FILTRO_IMAGENES = "Imágenes (*.png *.jpg *.jpeg *.bmp)"

_BLOQUES = (
    ("bombo", "tema.bloque.bombo", 0.28, 0.5),
    ("tablero_75", "tema.bloque.tablero_75", 0.5, 0.35),
    ("contador_bolas", "tema.bloque.contador_bolas", 0.12, 0.15),
    ("reloj", "tema.bloque.reloj", 0.12, 0.08),
)


class _LienzoPrevia(QWidget):
    """Rectángulos etiquetados a escala del lienzo 1920x1080 (decisión D9).
    No dibuja nada "en vivo": es deliberadamente estático."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._tema = TemaDashboard.por_defecto()
        self.setMinimumSize(480, 270)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def actualizar(self, tema: TemaDashboard) -> None:
        self._tema = tema
        self.update()

    def paintEvent(self, _evento: object) -> None:  # noqa: N802 - override Qt
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            ancho_disponible, alto_disponible = self.width(), self.height()
            escala = min(ancho_disponible / _ANCHO_REFERENCIA, alto_disponible / _ALTO_REFERENCIA)
            ancho_lienzo, alto_lienzo = _ANCHO_REFERENCIA * escala, _ALTO_REFERENCIA * escala
            origen_x = (ancho_disponible - ancho_lienzo) / 2
            origen_y = (alto_disponible - alto_lienzo) / 2

            pintor.fillRect(
                QRectF(origen_x, origen_y, ancho_lienzo, alto_lienzo),
                QColor(self._tema.colores.fondo),
            )
            pintor.setPen(QPen(QColor("#33334a")))
            pintor.drawRect(QRectF(origen_x, origen_y, ancho_lienzo, alto_lienzo))

            for clave, clave_i18n, ancho_frac, alto_frac in _BLOQUES:
                bloque: ConfigBloque = getattr(self._tema, clave)
                if not bloque.visible:
                    continue
                ancho = _ANCHO_REFERENCIA * ancho_frac * bloque.escala * escala
                alto = _ALTO_REFERENCIA * alto_frac * bloque.escala * escala
                x = origen_x + bloque.pos_x * ancho_lienzo
                y = origen_y + bloque.pos_y * alto_lienzo
                rect = QRectF(x, y, ancho, alto)
                pintor.fillRect(rect, QColor(self._tema.colores.acento).lighter(150))
                pintor.setPen(QPen(QColor(self._tema.colores.acento)))
                pintor.drawRect(rect)
                pintor.setPen(QPen(QColor(self._tema.colores.texto)))
                pintor.drawText(rect, Qt.AlignmentFlag.AlignCenter, t(clave_i18n))

            if self._tema.banner_texto.visible:
                rect_banner = QRectF(
                    origen_x, origen_y + alto_lienzo - 24 * escala, ancho_lienzo, 24 * escala
                )
                pintor.fillRect(rect_banner, QColor(self._tema.colores.acento))
                pintor.setPen(QPen(QColor("#ffffff")))
                texto = self._tema.banner_texto.texto or t("tema.bloque.banner_texto")
                pintor.drawText(rect_banner, Qt.AlignmentFlag.AlignCenter, texto)
        finally:
            pintor.end()


class VistaTema(QWidget):
    def __init__(self, con: Any, evento: Evento, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._con = con
        self._evento = evento
        self._actualizando_formulario = False

        self._franja = FranjaError()
        self._temporizador = QTimer(self)
        self._temporizador.setSingleShot(True)
        self._temporizador.setInterval(RETARDO_VISTA_PREVIA_MS)
        self._temporizador.timeout.connect(self._guardar)

        self._aviso_no_wysiwyg = QLabel()
        self._aviso_no_wysiwyg.setWordWrap(True)
        self._aviso_no_wysiwyg.setObjectName("etiquetaSecundaria")

        self._construir_formulario()

        self._lienzo = _LienzoPrevia()
        self._titulo_previa = QLabel()
        contenedor_previa = QWidget()
        distribucion_previa = QVBoxLayout(contenedor_previa)
        distribucion_previa.addWidget(self._titulo_previa)
        distribucion_previa.addWidget(self._lienzo, stretch=1)

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
        distribucion.addWidget(self._aviso_no_wysiwyg)
        distribucion.addWidget(self._splitter, stretch=1)

        tema_inicial = TemaDashboard.desde_json(evento.tema_json)
        self._cargar_en_formulario(tema_inicial)
        self.retraducir()
        i18n.registrar_para_retraduccion(self)
        self._lienzo.actualizar(self._tema)

    # --- Construcción del formulario ---

    def _fila_color(self, boton: BotonColor) -> QHBoxLayout:
        fila = QHBoxLayout()
        fila.addWidget(boton)
        fila.addStretch()
        return fila

    def _construir_formulario(self) -> None:
        self._panel_formulario = QWidget()
        distribucion = QVBoxLayout(self._panel_formulario)

        self._grupo_colores = QGroupBox()
        formulario_colores = QFormLayout()
        self._color_fondo = BotonColor("#0b0b14")
        self._color_fondo.clicked.connect(self._marcar_cambio)
        self._color_texto = BotonColor("#f2f2f7")
        self._color_texto.clicked.connect(self._marcar_cambio)
        self._color_acento = BotonColor("#5b8def")
        self._color_acento.clicked.connect(self._marcar_cambio)
        self._color_tablero_marcado = BotonColor("#5b8def")
        self._color_tablero_marcado.clicked.connect(self._marcar_cambio)
        self._etiqueta_color_fondo = QLabel()
        self._etiqueta_color_texto = QLabel()
        self._etiqueta_color_acento = QLabel()
        self._etiqueta_color_tablero_marcado = QLabel()
        formulario_colores.addRow(self._etiqueta_color_fondo, self._fila_color(self._color_fondo))
        formulario_colores.addRow(self._etiqueta_color_texto, self._fila_color(self._color_texto))
        formulario_colores.addRow(self._etiqueta_color_acento, self._fila_color(self._color_acento))
        formulario_colores.addRow(
            self._etiqueta_color_tablero_marcado, self._fila_color(self._color_tablero_marcado)
        )
        self._boton_imagen_fondo = QPushButton()
        self._boton_imagen_fondo.clicked.connect(self._cargar_imagen_fondo)
        self._etiqueta_imagen_fondo = QLabel("—")
        fila_imagen_fondo = QHBoxLayout()
        fila_imagen_fondo.addWidget(self._boton_imagen_fondo)
        fila_imagen_fondo.addWidget(self._etiqueta_imagen_fondo, stretch=1)
        self._etiqueta_campo_imagen_fondo = QLabel()
        formulario_colores.addRow(self._etiqueta_campo_imagen_fondo, fila_imagen_fondo)
        self._grupo_colores.setLayout(formulario_colores)

        self._grupo_bloques = QGroupBox()
        distribucion_bloques = QVBoxLayout()
        self._campos_bloque: dict[str, dict[str, QWidget]] = {}
        for clave, clave_i18n, _aw, _ah in _BLOQUES:
            self._campos_bloque[clave] = self._agregar_bloque(distribucion_bloques, clave_i18n)
        self._campos_banner = self._agregar_banner(distribucion_bloques)
        self._grupo_bloques.setLayout(distribucion_bloques)

        self._grupo_juego = QGroupBox()
        formulario_juego = QFormLayout()
        self._spin_ultimas_bolas = QSpinBox()
        self._spin_ultimas_bolas.setRange(0, 20)
        self._spin_ultimas_bolas.valueChanged.connect(self._marcar_cambio)
        self._check_sonido = QCheckBox()
        self._check_sonido.toggled.connect(self._marcar_cambio)
        self._etiqueta_ultimas_bolas = QLabel()
        formulario_juego.addRow(self._etiqueta_ultimas_bolas, self._spin_ultimas_bolas)
        formulario_juego.addRow(self._check_sonido)
        self._grupo_juego.setLayout(formulario_juego)

        distribucion.addWidget(self._grupo_colores)
        distribucion.addWidget(self._grupo_bloques)
        distribucion.addWidget(self._grupo_juego)
        distribucion.addStretch()

    def _agregar_bloque(self, distribucion: QVBoxLayout, clave_i18n: str) -> dict[str, QWidget]:
        grupo = QGroupBox(t(clave_i18n))
        grupo.setProperty("clave_i18n_titulo", clave_i18n)
        formulario = QFormLayout()
        check_visible = QCheckBox()
        check_visible.toggled.connect(self._marcar_cambio)
        spin_x = QDoubleSpinBox()
        spin_x.setRange(0.0, 1.0)
        spin_x.setSingleStep(0.05)
        spin_x.valueChanged.connect(self._marcar_cambio)
        spin_y = QDoubleSpinBox()
        spin_y.setRange(0.0, 1.0)
        spin_y.setSingleStep(0.05)
        spin_y.valueChanged.connect(self._marcar_cambio)
        spin_escala = QDoubleSpinBox()
        spin_escala.setRange(0.1, 3.0)
        spin_escala.setSingleStep(0.05)
        spin_escala.valueChanged.connect(self._marcar_cambio)
        etiqueta_visible = check_visible
        etiqueta_x = QLabel()
        etiqueta_y = QLabel()
        etiqueta_escala = QLabel()
        formulario.addRow(etiqueta_visible)
        formulario.addRow(etiqueta_x, spin_x)
        formulario.addRow(etiqueta_y, spin_y)
        formulario.addRow(etiqueta_escala, spin_escala)
        grupo.setLayout(formulario)
        distribucion.addWidget(grupo)
        return {
            "grupo": grupo,
            "visible": check_visible,
            "pos_x": spin_x,
            "pos_y": spin_y,
            "escala": spin_escala,
            "etiqueta_x": etiqueta_x,
            "etiqueta_y": etiqueta_y,
            "etiqueta_escala": etiqueta_escala,
        }

    def _agregar_banner(self, distribucion: QVBoxLayout) -> dict[str, QWidget]:
        grupo = QGroupBox()
        formulario = QFormLayout()
        check_visible = QCheckBox()
        check_visible.toggled.connect(self._marcar_cambio)
        campo_texto = QLineEdit()
        campo_texto.textChanged.connect(self._marcar_cambio)
        etiqueta_texto = QLabel()
        formulario.addRow(check_visible)
        formulario.addRow(etiqueta_texto, campo_texto)
        grupo.setLayout(formulario)
        distribucion.addWidget(grupo)
        return {
            "grupo": grupo,
            "visible": check_visible,
            "texto": campo_texto,
            "etiqueta": etiqueta_texto,
        }

    # --- Formulario <-> TemaDashboard ---

    def _leer_bloque(self, campos: dict[str, QWidget]) -> ConfigBloque:
        return ConfigBloque(
            visible=campos["visible"].isChecked(),
            pos_x=campos["pos_x"].value(),
            pos_y=campos["pos_y"].value(),
            escala=campos["escala"].value(),
        )

    def _leer_formulario(self) -> TemaDashboard:
        from bingo.dominio.tema import ConfigBannerTexto, ConfigColores, ConfigJuego

        tema = TemaDashboard(
            colores=ConfigColores(
                fondo=self._color_fondo.color,
                texto=self._color_texto.color,
                acento=self._color_acento.color,
                tablero_marcado=self._color_tablero_marcado.color,
            ),
            imagen_fondo=self._imagen_fondo_actual,
            bombo=self._leer_bloque(self._campos_bloque["bombo"]),
            tablero_75=self._leer_bloque(self._campos_bloque["tablero_75"]),
            contador_bolas=self._leer_bloque(self._campos_bloque["contador_bolas"]),
            reloj=self._leer_bloque(self._campos_bloque["reloj"]),
            banner_texto=ConfigBannerTexto(
                visible=self._campos_banner["visible"].isChecked(),
                texto=self._campos_banner["texto"].text(),
            ),
            juego=ConfigJuego(
                mostrar_ultimas_bolas=self._spin_ultimas_bolas.value(),
                sonido_activado=self._check_sonido.isChecked(),
            ),
        )
        return tema

    def _cargar_bloque(self, campos: dict[str, QWidget], bloque: ConfigBloque) -> None:
        campos["visible"].setChecked(bloque.visible)
        campos["pos_x"].setValue(bloque.pos_x)
        campos["pos_y"].setValue(bloque.pos_y)
        campos["escala"].setValue(bloque.escala)

    def _cargar_en_formulario(self, tema: TemaDashboard) -> None:
        self._actualizando_formulario = True
        try:
            self._color_fondo.establecer_color(tema.colores.fondo)
            self._color_texto.establecer_color(tema.colores.texto)
            self._color_acento.establecer_color(tema.colores.acento)
            self._color_tablero_marcado.establecer_color(tema.colores.tablero_marcado)
            self._imagen_fondo_actual = tema.imagen_fondo
            self._actualizar_etiqueta_imagen()

            self._cargar_bloque(self._campos_bloque["bombo"], tema.bombo)
            self._cargar_bloque(self._campos_bloque["tablero_75"], tema.tablero_75)
            self._cargar_bloque(self._campos_bloque["contador_bolas"], tema.contador_bolas)
            self._cargar_bloque(self._campos_bloque["reloj"], tema.reloj)
            self._campos_banner["visible"].setChecked(tema.banner_texto.visible)
            self._campos_banner["texto"].setText(tema.banner_texto.texto)

            self._spin_ultimas_bolas.setValue(tema.juego.mostrar_ultimas_bolas)
            self._check_sonido.setChecked(tema.juego.sonido_activado)
        finally:
            self._actualizando_formulario = False
        self._tema = tema

    def _actualizar_etiqueta_imagen(self) -> None:
        from pathlib import Path

        if self._imagen_fondo_actual and Path(self._imagen_fondo_actual).exists():
            self._etiqueta_imagen_fondo.setText(Path(self._imagen_fondo_actual).name)
        else:
            self._etiqueta_imagen_fondo.setText("—")

    # --- Cambios ---

    def _marcar_cambio(self, *_args: object) -> None:
        if self._actualizando_formulario:
            return
        self._tema = self._leer_formulario()
        self._lienzo.actualizar(self._tema)
        self._temporizador.start()

    def _cargar_imagen_fondo(self) -> None:
        from pathlib import Path

        ruta, _ = QFileDialog.getOpenFileName(
            self, t("tema.accion.cargar_imagen_fondo"), "", _FILTRO_IMAGENES
        )
        if not ruta:
            return
        destino = dir_medios_evento(self._evento.id) / "tema_fondo.png"
        try:
            resultado = validar_y_normalizar(Path(ruta), destino, lado_max=LADO_MAX_LOGO)
        except ErrorBingo as error:
            self._franja.mostrar_error(error)
            return
        self._imagen_fondo_actual = str(resultado)
        self._actualizar_etiqueta_imagen()
        self._marcar_cambio()

    # --- Guardado ---

    def _guardar(self) -> None:
        try:
            validar(self._tema)
        except ErrorValidacion as error:
            self._franja.mostrar(t(error.clave_i18n, **error.parametros))
            return
        try:
            repo_evento.actualizar_tema(self._con, self._evento.id, self._tema.a_json())
        except ErrorBingo as error:
            self._franja.mostrar_error(error, on_reintentar=self._guardar)
            return
        self._franja.mostrar_exito(t("tema.exito.guardado"))

    # --- i18n ---

    def retraducir(self) -> None:
        self._aviso_no_wysiwyg.setText(t("tema.aviso.no_es_wysiwyg"))
        self._titulo_previa.setText(t("tema.vista_previa.titulo"))
        self._grupo_colores.setTitle(t("tema.seccion.colores"))
        self._grupo_bloques.setTitle(t("tema.seccion.bloques"))
        self._grupo_juego.setTitle(t("tema.seccion.juego"))

        self._etiqueta_color_fondo.setText(t("tema.campo.color_fondo"))
        self._etiqueta_color_texto.setText(t("tema.campo.color_texto"))
        self._etiqueta_color_acento.setText(t("tema.campo.color_acento"))
        self._etiqueta_color_tablero_marcado.setText(t("tema.campo.color_tablero_marcado"))
        self._etiqueta_campo_imagen_fondo.setText(t("tema.campo.imagen_fondo"))
        self._boton_imagen_fondo.setText(t("tema.accion.cargar_imagen_fondo"))

        for campos in self._campos_bloque.values():
            grupo = campos["grupo"]
            grupo.setTitle(t(grupo.property("clave_i18n_titulo")))
            campos["visible"].setText(t("tema.campo.visible"))
            campos["etiqueta_x"].setText(t("tema.campo.pos_x"))
            campos["etiqueta_y"].setText(t("tema.campo.pos_y"))
            campos["etiqueta_escala"].setText(t("tema.campo.escala"))

        self._campos_banner["grupo"].setTitle(t("tema.bloque.banner_texto"))
        self._campos_banner["visible"].setText(t("tema.campo.visible"))
        self._campos_banner["etiqueta"].setText(t("tema.campo.banner_texto_valor"))

        self._etiqueta_ultimas_bolas.setText(t("tema.campo.mostrar_ultimas_bolas"))
        self._check_sonido.setText(t("tema.campo.sonido_activado"))
        self._lienzo.update()
