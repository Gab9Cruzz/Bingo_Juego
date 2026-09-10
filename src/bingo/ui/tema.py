"""Tema visual: dos funciones con dos públicos distintos (enmienda E15, DU-1).

`aplicar_tema_operador` instala un tema oscuro neutro **fijo**: los colores de
marca de la organización NO repintan la interfaz del operador. Un color de
marca no es un color semántico (si la organización es roja, el color de acción
primaria y el de peligro serían el mismo rojo), y un operador que corre el
mismo programa para media docena de clientes necesita memoria muscular estable
entre eventos. La marca sí aparece como identidad (logo, franja, tarjeta), y
`paleta_organizacion` es la que consumen la vista previa del cartón (fase 3),
el motor de PDF (fase 3) y la ventana de transmisión (fase 5) — nunca esta
ventana. Decisión confirmada por Gabriel; ver `docs/decisiones.md` (DU-1).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Reexportada por compatibilidad (decisión DU-6, fase 5): `contraste()` es
# matemática pura, sin nada de Qt, y se movió a `dominio/tema.py`. Quien ya
# hacía `from bingo.ui.tema import contraste` sigue funcionando igual.
from bingo.dominio.tema import contraste  # noqa: F401

_PATRON_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")

DEFECTO_PRIMARIO = "#1a1a2e"
DEFECTO_SECUNDARIO = "#e94560"
DEFECTO_TEXTO = "#ffffff"
# Umbral de identidad de marca (WCAG AA estándar) — distinto del umbral más
# estricto de la transmisión (`dominio.tema.UMBRAL_CONTRASTE_TRANSMISION`,
# 7:1, decisión DU-6): esta pantalla no la ve el público en un móvil.
UMBRAL_CONTRASTE_AA = 4.5


def _validar_color(color: str | None, defecto: str) -> str:
    if color and _PATRON_HEX.match(color):
        return color
    return defecto


@dataclass(frozen=True, slots=True)
class PaletaMarca:
    color_primario: str
    color_secundario: str
    color_texto: str
    contraste_texto_sobre_primario: float
    contraste_ok: bool


def paleta_organizacion(org: object) -> PaletaMarca:
    """Valida y devuelve la paleta de marca de una organización. No la aplica a nada.

    `org` es cualquier objeto con `color_primario`/`color_secundario`/
    `color_texto` (normalmente `dominio.modelos.Organizacion`); un color que no
    calce con `#RRGGBB` cae al valor por defecto, con registro.
    """
    primario = _validar_color(getattr(org, "color_primario", None), DEFECTO_PRIMARIO)
    secundario = _validar_color(getattr(org, "color_secundario", None), DEFECTO_SECUNDARIO)
    texto = _validar_color(getattr(org, "color_texto", None), DEFECTO_TEXTO)
    ratio = contraste(texto, primario)
    return PaletaMarca(
        color_primario=primario,
        color_secundario=secundario,
        color_texto=texto,
        contraste_texto_sobre_primario=ratio,
        contraste_ok=ratio >= UMBRAL_CONTRASTE_AA,
    )


# Fichas semánticas del tema neutro del operador. Pensado para sala en
# penumbra con un segundo monitor brillante y una cámara al lado.
_SUPERFICIE = "#161622"
_SUPERFICIE_ELEVADA = "#1f1f2e"
_BORDE = "#33334a"
_TEXTO_PRIMARIO = "#f2f2f7"
_TEXTO_SECUNDARIO = "#a5a5c0"
_TEXTO_DESHABILITADO = "#5c5c73"
_ACENTO = "#5b8def"
_ANILLO_FOCO = "#8ab4ff"
_HOVER = "#26263a"
_PULSADO = "#2f2f47"
_PELIGRO = "#e5484d"
_AVISO = "#e2a33d"
_EXITO = "#3fb27f"

_HOJA_DE_ESTILO = f"""
QWidget {{
    background-color: {_SUPERFICIE};
    color: {_TEXTO_PRIMARIO};
    font-size: 13px;
}}

QMainWindow, QDialog {{
    background-color: {_SUPERFICIE};
}}

QPushButton {{
    background-color: {_SUPERFICIE_ELEVADA};
    border: 1px solid {_BORDE};
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 20px;
}}
QPushButton:hover {{ background-color: {_HOVER}; }}
QPushButton:pressed {{ background-color: {_PULSADO}; }}
QPushButton:disabled {{ color: {_TEXTO_DESHABILITADO}; border-color: {_BORDE}; }}
QPushButton:focus {{ border: 2px solid {_ANILLO_FOCO}; }}
QPushButton#primario {{ background-color: {_ACENTO}; border: none; color: white; }}
QPushButton#primario:hover {{ background-color: #6f9bf2; }}
QPushButton#peligro {{ background-color: transparent; border: 1px solid {_PELIGRO}; \
color: {_PELIGRO}; }}

QLineEdit, QComboBox, QDateEdit, QTimeEdit, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
    background-color: {_SUPERFICIE_ELEVADA};
    border: 1px solid {_BORDE};
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: {_ACENTO};
}}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus,
QDoubleSpinBox:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 2px solid {_ANILLO_FOCO};
}}
QLineEdit:disabled, QComboBox:disabled {{ color: {_TEXTO_DESHABILITADO}; }}
QLineEdit[error="true"] {{ border: 2px solid {_PELIGRO}; }}

QListWidget, QTableWidget, QTreeWidget {{
    background-color: {_SUPERFICIE_ELEVADA};
    border: 1px solid {_BORDE};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item:selected, QTableWidget::item:selected {{
    background-color: {_ACENTO};
    color: white;
}}

QLabel#etiquetaSecundaria {{ color: {_TEXTO_SECUNDARIO}; }}
QLabel#chipBorrador {{ background-color: {_TEXTO_SECUNDARIO}; color: {_SUPERFICIE}; \
border-radius: 4px; padding: 2px 8px; }}
QLabel#chipPreparado {{ background-color: {_AVISO}; color: {_SUPERFICIE}; \
border-radius: 4px; padding: 2px 8px; }}
QLabel#chipEnCurso {{ background-color: {_ACENTO}; color: white; \
border-radius: 4px; padding: 2px 8px; }}
QLabel#chipFinalizado {{ background-color: {_EXITO}; color: white; \
border-radius: 4px; padding: 2px 8px; }}

QFrame#franjaError {{
    background-color: rgba(229, 72, 77, 0.15);
    border: 1px solid {_PELIGRO};
    border-radius: 6px;
}}
QFrame#franjaExito {{
    background-color: rgba(63, 178, 127, 0.15);
    border: 1px solid {_EXITO};
    border-radius: 6px;
}}
QFrame#franjaInfo {{
    background-color: rgba(91, 141, 239, 0.15);
    border: 1px solid {_ACENTO};
    border-radius: 6px;
}}
QFrame#tarjetaOrganizacion {{
    background-color: {_SUPERFICIE_ELEVADA};
    border: 1px solid {_BORDE};
    border-radius: 8px;
}}
QFrame#tarjetaOrganizacion:hover {{ border-color: {_ACENTO}; }}

QListWidget#navegacionGlobal, QListWidget#navegacionEvento {{
    background-color: {_SUPERFICIE};
    border: none;
}}
QListWidget#navegacionGlobal::item, QListWidget#navegacionEvento::item {{
    padding: 10px 12px;
    border-radius: 6px;
}}
QListWidget#navegacionGlobal::item:selected, QListWidget#navegacionEvento::item:selected {{
    background-color: {_SUPERFICIE_ELEVADA};
    color: {_ACENTO};
}}

QStatusBar {{
    background-color: {_SUPERFICIE_ELEVADA};
    border-top: 1px solid {_BORDE};
}}
"""


def aplicar_tema_operador(app: QApplication) -> None:
    """Instala el tema neutro fijo del operador. No recibe ni depende de ninguna organización."""
    paleta = QPalette()
    paleta.setColor(QPalette.ColorRole.Window, QColor(_SUPERFICIE))
    paleta.setColor(QPalette.ColorRole.WindowText, QColor(_TEXTO_PRIMARIO))
    paleta.setColor(QPalette.ColorRole.Base, QColor(_SUPERFICIE_ELEVADA))
    paleta.setColor(QPalette.ColorRole.Text, QColor(_TEXTO_PRIMARIO))
    paleta.setColor(QPalette.ColorRole.Button, QColor(_SUPERFICIE_ELEVADA))
    paleta.setColor(QPalette.ColorRole.ButtonText, QColor(_TEXTO_PRIMARIO))
    paleta.setColor(QPalette.ColorRole.Highlight, QColor(_ACENTO))
    paleta.setColor(QPalette.ColorRole.HighlightedText, QColor("white"))
    paleta.setColor(QPalette.ColorRole.PlaceholderText, QColor(_TEXTO_SECUNDARIO))
    paleta.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(_TEXTO_DESHABILITADO)
    )
    paleta.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(_TEXTO_DESHABILITADO)
    )
    app.setPalette(paleta)
    app.setStyleSheet(_HOJA_DE_ESTILO)
