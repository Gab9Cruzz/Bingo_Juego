"""Único módulo responsable de decir dónde está cada cosa en el equipo.

Nadie más construye rutas a mano. `raiz_datos()` lee `BINGO_HOME` **en cada
llamada**, sin cachear en una constante de módulo: si se cachea,
`monkeypatch.setenv` después del primer import deja de tener efecto y las
pruebas terminan escribiendo en el `%LOCALAPPDATA%` real del desarrollador.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from bingo.config.ajustes import SEGMENTOS_SINCRONIZADOS


def raiz_datos() -> Path:
    """Raíz de todos los datos de la aplicación.

    `BINGO_HOME` la sobreescribe (usado por las pruebas). Sin ella, en Windows
    es `%LOCALAPPDATA%\\Bingo`; fuera de Windows, `~/.local/share/Bingo`.
    """
    override = os.environ.get("BINGO_HOME")
    if override:
        return Path(override)
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        base = Path(local_app_data) if local_app_data else Path.home() / "AppData" / "Local"
        return base / "Bingo"
    return Path.home() / ".local" / "share" / "Bingo"


def dir_datos() -> Path:
    return raiz_datos() / "datos"


def dir_logs() -> Path:
    return raiz_datos() / "logs"


def dir_respaldos() -> Path:
    return raiz_datos() / "respaldos"


def dir_medios() -> Path:
    return raiz_datos() / "medios"


def dir_medios_organizacion(organizacion_id: int) -> Path:
    """Carpeta de medios de una organización, indexada por id, no por nombre.

    El nombre de la organización puede llevar barras, dos puntos o acentos, y
    renombrar la organización dejaría carpetas huérfanas.
    """
    return dir_medios() / str(organizacion_id)


def dir_logs_evento(evento_id: int) -> Path:
    """Carpeta de logs de partida de un evento (usada desde la fase 5)."""
    return dir_logs() / str(evento_id)


def dir_medios_evento(evento_id: int) -> Path:
    """Logo(s) propios de un evento (fase 3): si el operador sube uno distinto
    al de la organización para este evento en particular, vive aquí, indexado
    por id por la misma razón que `dir_medios_organizacion`.
    """
    return dir_medios() / "eventos" / str(evento_id)


def dir_impresos_evento(evento_id: int) -> Path:
    """PDFs de cartones generados para un evento (fase 3, servicio_impresion)."""
    return raiz_datos() / "impresos" / str(evento_id)


def ruta_bd() -> Path:
    return dir_datos() / "bingo.db"


def ruta_preferencias() -> Path:
    return raiz_datos() / "preferencias.json"


def ruta_log_aplicacion() -> Path:
    return dir_logs() / "aplicacion.log"


def asegurar_estructura() -> None:
    """Crea toda la estructura de carpetas si falta. Idempotente."""
    for carpeta in (dir_datos(), dir_logs(), dir_respaldos(), dir_medios()):
        carpeta.mkdir(parents=True, exist_ok=True)


def advertencia_ubicacion_bd() -> str | None:
    """Devuelve una clave de aviso si la base vive en un sitio peligroso para SQLite.

    Detecta un segmento de carpeta sincronizada conocido, o una ruta UNC
    (`\\\\servidor\\recurso`). No bloquea: el llamante decide cómo avisar.
    """
    ruta = str(ruta_bd())
    if ruta.startswith("\\\\") or ruta.startswith("//"):
        return "ajustes.aviso_ubicacion_sincronizada"
    partes = Path(ruta).parts
    for segmento in SEGMENTOS_SINCRONIZADOS:
        if any(segmento.lower() in parte.lower() for parte in partes):
            return "ajustes.aviso_ubicacion_sincronizada"
    return None
