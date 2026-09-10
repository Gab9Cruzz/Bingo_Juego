"""Tablero de 1 a 75 para la superficie del operador (contrato §5.5).

Cinco columnas por letra (B-I-N-G-O). Una cantada se distingue por relleno
**y** peso tipográfico, no solo color (mismo principio que DU-6 exige para
la pantalla de transmisión: daltonismo, y aquí además una sala mal
iluminada). La última cantada lleva además una marca de propiedad
(`ultima`) que la hoja de estilos puede resaltar con un borde.

Widget puro del operador: no es el que pinta la pantalla de transmisión
(`ui/transmision/bloques.py`, contrato §5.4) — esa se dibuja a mano sobre un
`QPainter` en un lienzo lógico 1920x1080 (decisión D14), no con `QLabel`.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QLabel, QWidget

_LETRAS = ("B", "I", "N", "G", "O")
_RANGOS = ((1, 15), (16, 30), (31, 45), (46, 60), (61, 75))


class TableroSetentaYCinco(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._celdas: dict[int, QLabel] = {}
        self._ultima: int | None = None

        distribucion = QGridLayout(self)
        distribucion.setSpacing(2)
        for columna, (letra, rango) in enumerate(zip(_LETRAS, _RANGOS, strict=True)):
            inicio, fin = rango
            encabezado = QLabel(letra)
            encabezado.setAlignment(Qt.AlignmentFlag.AlignCenter)
            encabezado.setObjectName("tableroEncabezado")
            distribucion.addWidget(encabezado, 0, columna)
            for fila, numero in enumerate(range(inicio, fin + 1), start=1):
                celda = QLabel(str(numero))
                celda.setAlignment(Qt.AlignmentFlag.AlignCenter)
                celda.setObjectName("tableroCelda")
                celda.setMinimumSize(34, 28)
                distribucion.addWidget(celda, fila, columna)
                self._celdas[numero] = celda

    def marcar(self, numero: int, *, es_ultima: bool = False) -> None:
        celda = self._celdas.get(numero)
        if celda is None:
            return
        celda.setObjectName("tableroCeldaMarcada")
        if es_ultima:
            if self._ultima is not None and self._ultima in self._celdas:
                self._marcar_como_no_ultima(self._celdas[self._ultima])
            celda.setProperty("ultima", True)
            self._ultima = numero
        self._repolir(celda)

    def _marcar_como_no_ultima(self, celda: QLabel) -> None:
        celda.setProperty("ultima", False)
        self._repolir(celda)

    def _repolir(self, celda: QLabel) -> None:
        celda.style().unpolish(celda)
        celda.style().polish(celda)

    def reiniciar(self) -> None:
        for celda in self._celdas.values():
            celda.setObjectName("tableroCelda")
            celda.setProperty("ultima", False)
            self._repolir(celda)
        self._ultima = None

    def marcadas(self) -> set[int]:
        return {
            numero
            for numero, celda in self._celdas.items()
            if celda.objectName() == "tableroCeldaMarcada"
        }
