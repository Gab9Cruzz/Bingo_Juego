"""Visor de un cartón: dibuja la cuadrícula 5x5 con sus números y el espacio
libre (contrato de la fase 2, §2.5). `marcados` y `patron_resaltado` son la
API que la fase 5 necesita para reutilizar este mismo widget al validar
ganadores; en la fase 2 nadie los pasa — se guardan y se pintan si vienen,
sin ninguna lógica de "qué cuenta como marcado" (eso es dominio de la fase 5).

Tema neutro fijo (DU-1, `docs/decisiones.md`): los colores de aquí son los del
tema del operador, nunca los de la organización — este widget también lo
usará la ventana de operador de la fase 5, que jamás debe tomar el color de
marca de un cliente.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from bingo import i18n
from bingo.dominio.carton import BIT_LIBRE, MatrizCarton, indice_bit
from bingo.i18n import t

_LETRAS = ("B", "I", "N", "G", "O")
_LADO_CELDA = 56
_ALTO_ENCABEZADO = 32
_MARGEN = 8

_COLOR_BORDE = QColor("#33334a")
_COLOR_ENCABEZADO_FONDO = QColor("#1f1f2e")
_COLOR_TEXTO = QColor("#f2f2f7")
_COLOR_TEXTO_SECUNDARIO = QColor("#a5a5c0")
_COLOR_MARCADO_FONDO = QColor("#5b8def")
_COLOR_MARCADO_TEXTO = QColor("#ffffff")
_COLOR_RESALTADO_BORDE = QColor("#e2a33d")


class CuadriculaCarton(QWidget):
    """Dibuja un cartón, opcionalmente con números marcados y un patrón resaltado.

    `carton=None` dibuja el placeholder "sin selección" (estado por defecto
    al abrir la vista de cartones, y tras perder la selección por un filtro).
    """

    def __init__(
        self,
        carton: MatrizCarton | None = None,
        *,
        marcados: set[int] | None = None,
        patron_resaltado: int | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._carton = carton
        self._marcados = marcados or set()
        self._patron_resaltado = patron_resaltado
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setMinimumSize(
            _LADO_CELDA * 5 + _MARGEN * 2, _LADO_CELDA * 5 + _ALTO_ENCABEZADO + _MARGEN * 2
        )
        i18n.registrar_para_retraduccion(self)

    def actualizar(
        self,
        carton: MatrizCarton | None,
        *,
        marcados: set[int] | None = None,
        patron_resaltado: int | None = None,
    ) -> None:
        self._carton = carton
        self._marcados = marcados or set()
        self._patron_resaltado = patron_resaltado
        self.update()

    def limpiar(self) -> None:
        self.actualizar(None)

    def retraducir(self) -> None:
        self.update()

    def sizeHint(self) -> QSize:  # noqa: N802 - override Qt
        return QSize(
            _LADO_CELDA * 5 + _MARGEN * 2, _LADO_CELDA * 5 + _ALTO_ENCABEZADO + _MARGEN * 2
        )

    def paintEvent(self, _evento: object) -> None:  # noqa: N802 - override Qt
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            if self._carton is None:
                self._pintar_placeholder(pintor)
            else:
                self._pintar_carton(pintor)
        finally:
            pintor.end()

    def _pintar_placeholder(self, pintor: QPainter) -> None:
        pintor.setPen(QPen(_COLOR_BORDE))
        pintor.drawRect(self.rect().adjusted(1, 1, -1, -1))
        pintor.setPen(QPen(_COLOR_TEXTO_SECUNDARIO))
        pintor.drawText(
            self.rect(), Qt.AlignmentFlag.AlignCenter, t("cartones.visor.sin_seleccion")
        )

    def _pintar_carton(self, pintor: QPainter) -> None:
        assert self._carton is not None
        origen_x, origen_y = _MARGEN, _MARGEN

        fuente_encabezado = QFont()
        fuente_encabezado.setBold(True)
        fuente_encabezado.setPointSize(fuente_encabezado.pointSize() + 4)
        pintor.setFont(fuente_encabezado)
        for columna, letra in enumerate(_LETRAS):
            rect = QRectF(origen_x + columna * _LADO_CELDA, origen_y, _LADO_CELDA, _ALTO_ENCABEZADO)
            pintor.fillRect(rect, _COLOR_ENCABEZADO_FONDO)
            pintor.setPen(QPen(_COLOR_TEXTO))
            pintor.drawText(rect, Qt.AlignmentFlag.AlignCenter, letra)

        fuente_numeros = QFont()
        fuente_numeros.setPointSize(fuente_numeros.pointSize() + 2)
        pintor.setFont(fuente_numeros)

        for fila in range(5):
            for columna in range(5):
                valor = self._carton[fila][columna]
                bit = indice_bit(fila, columna)
                rect = QRectF(
                    origen_x + columna * _LADO_CELDA,
                    origen_y + _ALTO_ENCABEZADO + fila * _LADO_CELDA,
                    _LADO_CELDA,
                    _LADO_CELDA,
                )

                if bit in self._marcados:
                    pintor.fillRect(rect, _COLOR_MARCADO_FONDO)
                    color_texto = _COLOR_MARCADO_TEXTO
                else:
                    color_texto = _COLOR_TEXTO

                pintor.setPen(QPen(_COLOR_BORDE))
                pintor.drawRect(rect)

                if self._patron_resaltado is not None and (self._patron_resaltado >> bit) & 1:
                    lapiz = QPen(_COLOR_RESALTADO_BORDE)
                    lapiz.setWidth(3)
                    pintor.setPen(lapiz)
                    pintor.drawRect(rect.adjusted(2, 2, -2, -2))

                pintor.setPen(QPen(color_texto))
                if bit == BIT_LIBRE and valor is None:
                    fuente_libre = QFont()
                    fuente_libre.setPointSize(max(fuente_numeros.pointSize() - 4, 7))
                    pintor.setFont(fuente_libre)
                    pintor.drawText(rect, Qt.AlignmentFlag.AlignCenter, t("carton.libre"))
                    pintor.setFont(fuente_numeros)
                else:
                    pintor.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(valor))
