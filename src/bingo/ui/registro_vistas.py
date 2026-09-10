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


def _vista_plantilla(con: Any, evento: Any) -> QWidget:
    from bingo.ui.vistas.vista_plantilla import VistaPlantilla

    return VistaPlantilla(con, evento)


def _vista_compradores(con: Any, evento: Any) -> QWidget:
    from bingo.ui.vistas.vista_compradores import VistaCompradores

    return VistaCompradores(con, evento)


def _vista_rondas(con: Any, evento: Any) -> QWidget:
    from bingo.ui.vistas.vista_rondas import VistaRondas

    return VistaRondas(con, evento)


def _vista_tema(con: Any, evento: Any) -> QWidget:
    from bingo.ui.vistas.vista_tema import VistaTema

    return VistaTema(con, evento)


REGISTRO_NAVEGACION_GLOBAL: list[EntradaNavegacionGlobal] = [
    EntradaNavegacionGlobal("nav.eventos", _vista_eventos),
    EntradaNavegacionGlobal("nav.organizaciones", _vista_organizaciones),
    EntradaNavegacionGlobal("nav.ajustes", _vista_ajustes),
]

# Orden del riel (decisión de gusto TD-1, docs/Fase_4/Plan_Implementacion_Fase4.md
# ANEXO D.4): Compradores sube al tercer puesto por urgencia operativa —
# Plantilla no se toca nunca más una vez impresos los cartones, y Compradores
# es la sección de la noche del evento.
SECCIONES_ESPACIO_EVENTO: list[EntradaSeccionEvento] = [
    EntradaSeccionEvento("espacio_evento.seccion.datos", _vista_datos_evento),
    EntradaSeccionEvento("espacio_evento.seccion.cartones", _vista_cartones),
    EntradaSeccionEvento("espacio_evento.seccion.compradores", _vista_compradores),
    EntradaSeccionEvento("espacio_evento.seccion.rondas", _vista_rondas),
    EntradaSeccionEvento("espacio_evento.seccion.plantilla", _vista_plantilla),
    EntradaSeccionEvento("espacio_evento.seccion.tema", _vista_tema),
]
