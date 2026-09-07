"""Registro de vistas: una tupla por vista, no una edición de `ventana_principal.py`.

Las fases 2 a 5 añaden secciones al espacio de trabajo del evento apendeando a
`SECCIONES_ESPACIO_EVENTO`, sin tocar la cáscara de `ventana_principal.py` ni
`espacio_evento.py`.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from PySide6.QtWidgets import QWidget


@dataclass(frozen=True)
class EntradaNavegacionGlobal:
    clave_i18n: str
    fabrica: Callable[[Any], QWidget]  # (con) -> QWidget


@dataclass(frozen=True)
class EntradaSeccionEvento:
    clave_i18n: str
    # (con, evento) -> QWidget. None = sección todavía no implementada
    # ("llega en una versión próxima").
    fabrica: Callable[[Any, Any], QWidget] | None


def _vista_eventos(con: Any) -> QWidget:
    from bingo.ui.vistas.vista_eventos import VistaEventos

    return VistaEventos(con)


def _vista_organizaciones(con: Any) -> QWidget:
    from bingo.ui.vistas.vista_organizaciones import VistaOrganizaciones

    return VistaOrganizaciones(con)


def _vista_ajustes(con: Any) -> QWidget:
    from bingo.ui.vistas.vista_ajustes import VistaAjustes

    return VistaAjustes(con)


def _vista_datos_evento(con: Any, evento: Any) -> QWidget:
    from bingo.ui.vistas.vista_datos_evento import VistaDatosEvento

    return VistaDatosEvento(con, evento)


def _vista_cartones(con: Any, evento: Any) -> QWidget:
    from bingo.ui.vistas.vista_cartones import VistaCartones

    return VistaCartones(con, evento)


REGISTRO_NAVEGACION_GLOBAL: list[EntradaNavegacionGlobal] = [
    EntradaNavegacionGlobal("nav.eventos", _vista_eventos),
    EntradaNavegacionGlobal("nav.organizaciones", _vista_organizaciones),
    EntradaNavegacionGlobal("nav.ajustes", _vista_ajustes),
]

SECCIONES_ESPACIO_EVENTO: list[EntradaSeccionEvento] = [
    EntradaSeccionEvento("espacio_evento.seccion.datos", _vista_datos_evento),
    EntradaSeccionEvento("espacio_evento.seccion.cartones", _vista_cartones),
    EntradaSeccionEvento("espacio_evento.seccion.plantilla", None),
    EntradaSeccionEvento("espacio_evento.seccion.compradores", None),
    EntradaSeccionEvento("espacio_evento.seccion.rondas", None),
]
