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
    # (con, evento, espacio) -> QWidget. `espacio` es el `EspacioEvento`
    # dueño de la sección (decisión D9/S5-3, fase 5): la sección Sorteo lo
    # necesita para pedir "Modo en vivo" y para llegar al `MotorSorteo`, que
    # vive en `espacio.motor_sorteo` — no en la vista, para sobrevivir a un
    # cambio de sección a mitad de ronda. Las demás secciones lo ignoran.
    # `None` = sección todavía no implementada ("llega en una versión
    # próxima").
    fabrica: Callable[[Any, Any, Any], QWidget] | None
    # Decisión D10: el riel se agrupa en dos bloques con encabezado no
    # seleccionable. "preparacion" | "evento".
    grupo: str = "preparacion"


def _vista_eventos(con: Any) -> QWidget:
    from bingo.ui.vistas.vista_eventos import VistaEventos

    return VistaEventos(con)


def _vista_organizaciones(con: Any) -> QWidget:
    from bingo.ui.vistas.vista_organizaciones import VistaOrganizaciones

    return VistaOrganizaciones(con)


def _vista_ajustes(con: Any) -> QWidget:
    from bingo.ui.vistas.vista_ajustes import VistaAjustes

    return VistaAjustes(con)


def _vista_datos_evento(con: Any, evento: Any, _espacio: Any) -> QWidget:
    from bingo.ui.vistas.vista_datos_evento import VistaDatosEvento

    return VistaDatosEvento(con, evento)


def _vista_cartones(con: Any, evento: Any, _espacio: Any) -> QWidget:
    from bingo.ui.vistas.vista_cartones import VistaCartones

    return VistaCartones(con, evento)


def _vista_plantilla(con: Any, evento: Any, _espacio: Any) -> QWidget:
    from bingo.ui.vistas.vista_plantilla import VistaPlantilla

    return VistaPlantilla(con, evento)


def _vista_compradores(con: Any, evento: Any, _espacio: Any) -> QWidget:
    from bingo.ui.vistas.vista_compradores import VistaCompradores

    return VistaCompradores(con, evento)


def _vista_rondas(con: Any, evento: Any, _espacio: Any) -> QWidget:
    from bingo.ui.vistas.vista_rondas import VistaRondas

    return VistaRondas(con, evento)


def _vista_tema(con: Any, evento: Any, _espacio: Any) -> QWidget:
    from bingo.ui.vistas.vista_tema import VistaTema

    return VistaTema(con, evento)


def _vista_sorteo(con: Any, evento: Any, espacio: Any) -> QWidget:
    from bingo.ui.sorteo.vista_sorteo import VistaSorteo

    return VistaSorteo(con, evento, espacio)


def _vista_auditoria(con: Any, evento: Any, _espacio: Any) -> QWidget:
    from bingo.ui.vistas.vista_auditoria import VistaAuditoria

    return VistaAuditoria(con, evento)


REGISTRO_NAVEGACION_GLOBAL: list[EntradaNavegacionGlobal] = [
    EntradaNavegacionGlobal("nav.eventos", _vista_eventos),
    EntradaNavegacionGlobal("nav.organizaciones", _vista_organizaciones),
    EntradaNavegacionGlobal("nav.ajustes", _vista_ajustes),
]

# Orden del riel (decisión D10/DU-16, plan de la fase 5): dos grupos.
# "Preparación" no se toca durante el evento; "Evento" es la noche del
# bingo. Sorteo va antes de Auditoría (tarea 4.19) a propósito: bajando con
# las flechas se llega a Sorteo sin pasar por encima de una sección de solo
# lectura — Auditoría queda la última justo porque nunca hace falta cruzarla
# para llegar a nada más.
SECCIONES_ESPACIO_EVENTO: list[EntradaSeccionEvento] = [
    EntradaSeccionEvento("espacio_evento.seccion.datos", _vista_datos_evento, grupo="preparacion"),
    EntradaSeccionEvento("espacio_evento.seccion.cartones", _vista_cartones, grupo="preparacion"),
    EntradaSeccionEvento("espacio_evento.seccion.plantilla", _vista_plantilla, grupo="preparacion"),
    EntradaSeccionEvento("espacio_evento.seccion.tema", _vista_tema, grupo="preparacion"),
    EntradaSeccionEvento("espacio_evento.seccion.compradores", _vista_compradores, grupo="evento"),
    EntradaSeccionEvento("espacio_evento.seccion.rondas", _vista_rondas, grupo="evento"),
    EntradaSeccionEvento("espacio_evento.seccion.sorteo", _vista_sorteo, grupo="evento"),
    EntradaSeccionEvento("espacio_evento.seccion.auditoria", _vista_auditoria, grupo="evento"),
]
