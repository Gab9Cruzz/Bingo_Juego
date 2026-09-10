"""Grilla 5x5 clicable para el editor de patrones (contrato de la fase 4,
§4.6). Enciende/apaga celdas y expone `mascara()`/`establecer_mascara()`.

Deliberadamente no se reutiliza ni se modifica
`ui/widgets/cuadricula_carton.py` (decisión del plan de la fase 4): ese
widget dibuja una cara de cartón con números — comparte la geometría 5x5 y
nada más. Un widget con dos modos (números vs. mascara editable) se
estorbaría a sí mismo.

Accesible por teclado (decisión DS19): `StrongFocus`, flechas para mover el
cursor, Espacio para alternar la celda bajo el cursor, Inicio/Fin para saltar
a la primera/última celda. El contorno de foco usa `_ANILLO_FOCO`, y cada
celda mide al menos `OBJETIVO_PULSACION_MINIMO_PX` de lado.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from bingo import i18n
from bingo.dominio.carton import BIT_LIBRE, indice_bit
from bingo.dominio.patron import celdas_desde_mascara, mascara
from bingo.i18n import t
from bingo.ui.atajos import OBJETIVO_PULSACION_MINIMO_PX

_LADO_CELDA = max(OBJETIVO_PULSACION_MINIMO_PX, 44)
_MARGEN = 6

_COLOR_BORDE = QColor("#33334a")
_COLOR_FONDO = QColor("#1f1f2e")
_COLOR_MARCADO = QColor("#5b8def")
_COLOR_TEXTO_MARCADO = QColor("#ffffff")
_COLOR_TEXTO = QColor("#a5a5c0")
_COLOR_ANILLO_FOCO = QColor("#8ab4ff")
_COLOR_LIBRE_BORDE = QColor("#e2a33d")


class RejillaPatron(QWidget):
    """Modo editable (clicable) por defecto; `solo_lectura=True` la vuelve
    una vista previa estática, usada por el selector de patrón de rondas.
    """

    cambiado = Signal()

    def __init__(
        self,
        *,
        mascara_inicial: int = 0,
        solo_lectura: bool = False,
        color_marcado: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._mascara = mascara_inicial
        self._solo_lectura = solo_lectura
        self._color_marcado = QColor(color_marcado) if color_marcado else _COLOR_MARCADO
        self._celda_foco = 0

        lado = _LADO_CELDA * 5 + _MARGEN * 2
        self.setFixedSize(lado, lado)
        if not solo_lectura:
            self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        i18n.registrar_para_retraduccion(self)

    # --- API pública ---

    def mascara(self) -> int:
        return self._mascara

    def establecer_mascara(self, valor: int) -> None:
        self._mascara = valor
        self.update()

    def establecer_color_marcado(self, color_hex: str) -> None:
        self._color_marcado = QColor(color_hex)
        self.update()

    def contador_celdas(self) -> int:
        return len(celdas_desde_mascara(self._mascara))

    # --- Interacción ---

    def _alternar(self, bit: int) -> None:
        if self._solo_lectura:
            return
        self._mascara ^= 1 << bit
        self.update()
        self.cambiado.emit()

    def mousePressEvent(self, evento: QMouseEvent) -> None:  # noqa: N802 - override Qt
        if self._solo_lectura:
            return
        x = evento.position().x() - _MARGEN
        y = evento.position().y() - _MARGEN
        if x < 0 or y < 0:
            return
        columna, fila = int(x // _LADO_CELDA), int(y // _LADO_CELDA)
        if 0 <= fila < 5 and 0 <= columna < 5:
            self._celda_foco = indice_bit(fila, columna)
            self._alternar(self._celda_foco)

    def keyPressEvent(self, evento: QKeyEvent) -> None:  # noqa: N802 - override Qt
        if self._solo_lectura:
            super().keyPressEvent(evento)
            return
        fila, columna = self._celda_foco // 5, self._celda_foco % 5
        if evento.key() == Qt.Key.Key_Left:
            columna = max(0, columna - 1)
        elif evento.key() == Qt.Key.Key_Right:
            columna = min(4, columna + 1)
        elif evento.key() == Qt.Key.Key_Up:
            fila = max(0, fila - 1)
        elif evento.key() == Qt.Key.Key_Down:
            fila = min(4, fila + 1)
        elif evento.key() == Qt.Key.Key_Home:
            fila, columna = 0, 0
        elif evento.key() == Qt.Key.Key_End:
            fila, columna = 4, 4
        elif evento.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._alternar(indice_bit(fila, columna))
            return
        else:
            super().keyPressEvent(evento)
            return
        self._celda_foco = indice_bit(fila, columna)
        self.update()

    # --- Pintado ---

    def paintEvent(self, _evento: object) -> None:  # noqa: N802 - override Qt
        pintor = QPainter(self)
        pintor.setRenderHint(QPainter.RenderHint.Antialiasing)
        try:
            fuente = QFont()
            fuente.setPointSize(fuente.pointSize() + 2)
            pintor.setFont(fuente)
            tiene_foco = self.hasFocus()
            for fila in range(5):
                for columna in range(5):
                    bit = indice_bit(fila, columna)
                    rect = QRectF(
                        _MARGEN + columna * _LADO_CELDA,
                        _MARGEN + fila * _LADO_CELDA,
                        _LADO_CELDA,
                        _LADO_CELDA,
                    )
                    marcado = (self._mascara >> bit) & 1
                    pintor.fillRect(rect, self._color_marcado if marcado else _COLOR_FONDO)
                    pintor.setPen(QPen(_COLOR_BORDE))
                    pintor.drawRect(rect)

                    if bit == BIT_LIBRE:
                        lapiz = QPen(_COLOR_LIBRE_BORDE)
                        lapiz.setWidth(2)
                        pintor.setPen(lapiz)
                        pintor.drawRect(rect.adjusted(2, 2, -2, -2))
                        pintor.setPen(QPen(_COLOR_TEXTO_MARCADO if marcado else _COLOR_TEXTO))
                        pintor.drawText(rect, Qt.AlignmentFlag.AlignCenter, t("carton.libre"))
                    else:
                        pintor.setPen(QPen(_COLOR_TEXTO_MARCADO if marcado else _COLOR_TEXTO))

                    if not self._solo_lectura and tiene_foco and bit == self._celda_foco:
                        anillo = QPen(_COLOR_ANILLO_FOCO)
                        anillo.setWidth(3)
                        pintor.setPen(anillo)
                        pintor.drawRect(rect.adjusted(2, 2, -2, -2))
        finally:
            pintor.end()

    def retraducir(self) -> None:
        self.update()


def mascara_desde_celdas(celdas: list[tuple[int, int]]) -> int:
    """Reexportado por conveniencia de `dominio.patron.mascara` para quien
    solo importe este widget."""
    return mascara(celdas)
