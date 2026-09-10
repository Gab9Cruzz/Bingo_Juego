"""Escala del lienzo lógico 1920x1080 al tamaño real de la ventana de
transmisión (decisión D14). El público no ve el lienzo lógico: ve la
ventana a la resolución real del monitor (o de la webcam/OBS que la
captura), así que todo se pinta en coordenadas 0..1920 / 0..1080 y se
escala una sola vez por fotograma con una `QTransform`.

Con barras (`letterbox`) si la relación de aspecto real no es 16:9 — nunca
se estira el contenido de forma desigual en `x`/`y`.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QTransform

ANCHO_LOGICO = 1920
ALTO_LOGICO = 1080


@dataclass(frozen=True, slots=True)
class Escala:
    transform: QTransform
    factor: float
    desplazamiento_x: float
    desplazamiento_y: float


def calcular_escala(ancho_real: int, alto_real: int) -> Escala:
    if ancho_real <= 0 or alto_real <= 0:
        return Escala(QTransform(), 1.0, 0.0, 0.0)
    factor = min(ancho_real / ANCHO_LOGICO, alto_real / ALTO_LOGICO)
    ancho_escalado = ANCHO_LOGICO * factor
    alto_escalado = ALTO_LOGICO * factor
    desplazamiento_x = (ancho_real - ancho_escalado) / 2
    desplazamiento_y = (alto_real - alto_escalado) / 2
    transform = QTransform()
    transform.translate(desplazamiento_x, desplazamiento_y)
    transform.scale(factor, factor)
    return Escala(transform, factor, desplazamiento_x, desplazamiento_y)
