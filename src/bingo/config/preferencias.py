"""Preferencias locales, fuera de la base de datos a propósito.

El idioma debe poder leerse antes de abrir la base (los mensajes de error de
migración también van traducidos), y las preferencias deben sobrevivir a
restaurar un respaldo hecho en otro equipo.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field

from bingo.config.rutas import ruta_preferencias

logger = logging.getLogger("bingo.config.preferencias")

IDIOMA_POR_DEFECTO = "es"


@dataclass
class VentanaPreferencias:
    geometria: str | None = None
    maximizada: bool = False
    monitor_transmision: int | None = None  # reservado para la fase 5


@dataclass
class Preferencias:
    idioma: str = IDIOMA_POR_DEFECTO
    ultimo_evento_abierto_id: int | None = None
    ultima_carpeta_exportacion: str | None = None
    avisos_descartados: list[str] = field(default_factory=list)
    ventana: VentanaPreferencias = field(default_factory=VentanaPreferencias)


def _por_defecto() -> Preferencias:
    return Preferencias()


def cargar() -> Preferencias:
    """Carga las preferencias. Ante un archivo ausente o corrupto, nunca falla."""
    ruta = ruta_preferencias()
    if not ruta.exists():
        return _por_defecto()

    try:
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        ventana = VentanaPreferencias(**datos.get("ventana", {}))
        return Preferencias(
            idioma=datos.get("idioma", IDIOMA_POR_DEFECTO),
            ultimo_evento_abierto_id=datos.get("ultimo_evento_abierto_id"),
            ultima_carpeta_exportacion=datos.get("ultima_carpeta_exportacion"),
            avisos_descartados=list(datos.get("avisos_descartados", [])),
            ventana=ventana,
        )
    except (json.JSONDecodeError, TypeError, ValueError) as error:
        logger.warning("preferencias.json corrupto (%s); se usan valores por defecto", error)
        try:
            ruta.rename(ruta.with_suffix(ruta.suffix + ".corrupto"))
        except OSError as error_mover:
            logger.warning("No se pudo renombrar preferencias.json corrupto: %s", error_mover)
        return _por_defecto()


def guardar(prefs: Preferencias) -> None:
    """Escritura atómica: archivo temporal + `os.replace`."""
    ruta = ruta_preferencias()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_suffix(ruta.suffix + ".tmp")
    contenido = asdict(prefs)
    temporal.write_text(json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporal, ruta)
