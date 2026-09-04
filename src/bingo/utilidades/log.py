"""Log de aplicación con rotación.

Distinto del log de partida de la fase 5 (uno por ronda, con `flush()` forzado
tras cada bola): este es el log general de la aplicación, nombrado
`aplicacion.log`, para que nadie los confunda.
"""

from __future__ import annotations

import logging
import os
import platform
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from bingo import __version__

FORMATO = "%(asctime)s.%(msecs)03dZ %(levelname)-8s %(name)s: %(message)s"
FORMATO_FECHA = "%Y-%m-%dT%H:%M:%S"

_configurado = False


class _FormateadorUTC(logging.Formatter):
    converter = staticmethod(__import__("time").gmtime)


def configurar_log(ruta_log: Path, *, ruta_bd: Path | None = None) -> logging.Logger:
    """Configura el logger raíz `bingo`. Idempotente dentro del mismo proceso."""
    global _configurado
    logger = logging.getLogger("bingo")

    if not _configurado:
        logger.setLevel(logging.DEBUG)
        logger.handlers.clear()

        ruta_log.parent.mkdir(parents=True, exist_ok=True)
        manejador_archivo = RotatingFileHandler(
            ruta_log, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8", delay=True
        )
        manejador_archivo.setLevel(logging.INFO)
        manejador_archivo.setFormatter(_FormateadorUTC(FORMATO, FORMATO_FECHA))
        logger.addHandler(manejador_archivo)

        if os.environ.get("BINGO_DEBUG") == "1":
            manejador_consola = logging.StreamHandler(sys.stderr)
            manejador_consola.setLevel(logging.DEBUG)
            manejador_consola.setFormatter(_FormateadorUTC(FORMATO, FORMATO_FECHA))
            logger.addHandler(manejador_consola)

        _configurado = True

    logger.info(
        "Arranque · bingo %s · Python %s · base=%s",
        __version__,
        platform.python_version(),
        ruta_bd if ruta_bd is not None else "(no abierta aún)",
    )
    return logger


def reiniciar_para_pruebas() -> None:
    """Quita todos los manejadores del logger raíz. Solo para `tests/conftest.py`."""
    global _configurado
    logger = logging.getLogger("bingo")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    _configurado = False
