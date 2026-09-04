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


def configurar_log(ruta_log: Path) -> logging.Logger:
    """Configura el logger raíz `bingo`. Idempotente dentro del mismo proceso.

    No escribe la línea de arranque: eso lo hace `registrar_arranque()`,
    llamado por separado una vez que se conoce la ruta de la base (después de
    aplicar migraciones). Separar las dos cosas evita escribir la línea de
    arranque dos veces si el llamante configura el log más de una vez.
    """
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

    return logger


def registrar_arranque(ruta_bd: Path) -> None:
    """Escribe la versión de la app, la de Python y la ruta de la base en la
    primera línea de cada arranque. Sin esto, un reporte de error a tres
    semanas vista no se puede reconstruir. No va a `auditoria` (enmienda
    E7b): eso es el rastro del negocio, esto es ciclo de vida de la app.
    """
    logging.getLogger("bingo").info(
        "Arranque · bingo %s · Python %s · base=%s",
        __version__,
        platform.python_version(),
        ruta_bd,
    )


def reiniciar_para_pruebas() -> None:
    """Quita todos los manejadores del logger raíz. Solo para `tests/conftest.py`."""
    global _configurado
    logger = logging.getLogger("bingo")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    _configurado = False
