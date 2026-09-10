"""Sistema de idiomas: `t(clave, **parametros)` y retraducción en caliente.

Ninguna cadena visible se escribe directamente en el código: todo pasa por
`t()`. El registro de widgets para `retraducir()` vive aquí (no en la ventana
principal) para que alcance también a una segunda ventana de nivel superior
(la ventana de transmisión de la fase 5) y a los widgets creados al vuelo.
"""

from __future__ import annotations

import json
import logging
import weakref
from pathlib import Path
from typing import Protocol, runtime_checkable

logger = logging.getLogger("bingo.i18n")

IDIOMA_REFERENCIA = "es"
MARCA_FALTANTE = "⟦{clave}⟧"

_RUTA_BASE = Path(__file__).parent
_traducciones: dict[str, dict[str, str]] = {}
_idioma_actual = IDIOMA_REFERENCIA
_widgets_registrados: weakref.WeakSet = weakref.WeakSet()


@runtime_checkable
class Retraducible(Protocol):
    def retraducir(self) -> None: ...


def idiomas_disponibles() -> list[str]:
    return sorted(p.stem for p in _RUTA_BASE.glob("*.json"))


def _cargar_archivo(idioma: str) -> dict[str, str]:
    ruta = _RUTA_BASE / f"{idioma}.json"
    with ruta.open(encoding="utf-8") as archivo:
        return json.load(archivo)


def cargar(idioma: str) -> None:
    """Carga (con caché) el idioma pedido y lo vuelve el idioma activo."""
    global _idioma_actual
    if IDIOMA_REFERENCIA not in _traducciones:
        _traducciones[IDIOMA_REFERENCIA] = _cargar_archivo(IDIOMA_REFERENCIA)
    if idioma not in _traducciones:
        _traducciones[idioma] = _cargar_archivo(idioma)
    _idioma_actual = idioma
    _retraducir_todo()


def idioma_actual() -> str:
    return _idioma_actual


class _DiccionarioTolerante(dict):
    """Un parámetro que falta se pinta `⟦nombre⟧` en vez de lanzar `KeyError`."""

    def __missing__(self, clave: str) -> str:
        return MARCA_FALTANTE.format(clave=clave)


def _resolver(idioma: str, clave: str, parametros: dict[str, object]) -> str:
    plantilla = _traducciones.get(idioma, {}).get(clave)
    if plantilla is None:
        # Respaldo: el español es el idioma de referencia.
        plantilla = _traducciones.get(IDIOMA_REFERENCIA, {}).get(clave)
    if plantilla is None:
        logger.warning("Clave i18n faltante: %s", clave)
        return MARCA_FALTANTE.format(clave=clave)

    try:
        return plantilla.format_map(_DiccionarioTolerante(parametros))
    except ValueError:
        logger.warning("Plantilla i18n mal formada para la clave %s", clave)
        return plantilla


def t(clave: str, **parametros: object) -> str:
    """Resuelve una clave de traducción contra el idioma activo de la
    interfaz. Nunca lanza, nunca devuelve vacío."""
    if not _traducciones:
        cargar(IDIOMA_REFERENCIA)
    return _resolver(_idioma_actual, clave, parametros)


def t_en(idioma: str, clave: str, **parametros: object) -> str:
    """Como `t()`, pero contra un `idioma` explícito, no el activo de la
    interfaz (decisión DU-13, fase 5): la ventana de transmisión tiene su
    propio idioma (`tema_json.idioma_publico`) — si el operador pone la
    interfaz en inglés para probar algo, el público no debe ver "WINNER"
    donde antes decía "¡BINGO!". Carga el idioma pedido si no está en caché."""
    if idioma not in _traducciones:
        _traducciones[idioma] = _cargar_archivo(idioma)
    if IDIOMA_REFERENCIA not in _traducciones:
        _traducciones[IDIOMA_REFERENCIA] = _cargar_archivo(IDIOMA_REFERENCIA)
    return _resolver(idioma, clave, parametros)


def registrar_para_retraduccion(widget: Retraducible) -> None:
    """Suscribe un widget (con método `retraducir()`) a los cambios de idioma.

    `WeakSet` más baja explícita en `destroyed`: PySide6 puede dejar un
    envoltorio Python vivo apuntando a un `QObject` de C++ ya destruido, y
    llamar a un método sobre eso lanza `RuntimeError`. La sola `WeakSet` no lo
    detecta porque el objeto Python sigue con vida.
    """
    _widgets_registrados.add(widget)
    destroyed = getattr(widget, "destroyed", None)
    if destroyed is not None:
        destroyed.connect(lambda *_args, w=widget: _widgets_registrados.discard(w))
    widget.retraducir()


def _retraducir_todo() -> None:
    for widget in list(_widgets_registrados):
        try:
            widget.retraducir()
        except RuntimeError:
            # Objeto C++ ya destruido; se limpiará por la señal `destroyed`.
            continue


def reiniciar_para_pruebas() -> None:
    """Vacía el estado global de idioma. Solo para `tests/conftest.py`."""
    global _idioma_actual
    _traducciones.clear()
    _idioma_actual = IDIOMA_REFERENCIA
    _widgets_registrados.clear()
