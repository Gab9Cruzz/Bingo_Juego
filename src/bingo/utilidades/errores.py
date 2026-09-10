"""Jerarquía de errores de la aplicación y manejador global de excepciones.

Reglas (ver `docs/convenciones-codigo.md`):

- La vista pinta ``t(e.clave_i18n, **e.parametros)``; el log escribe
  ``e.detalle`` y la traza; ``str(e)`` no se le enseña nunca a un usuario.
- ``ErrorValidacion`` se pinta junto al campo (``e.campo``), nunca en un modal.
- ``ErrorTransicionInvalida`` no es un error de validación: es un fallo de
  programa o una condición de carrera, y va a la franja no modal.
- El manejador global es el único lugar con un ``except Exception`` desnudo en
  toda la aplicación. Nadie más lo necesita: lo que no es ``ErrorBingo`` es un
  fallo de programa.
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from collections.abc import Callable

logger = logging.getLogger("bingo")

TipoRestriccion = Literal["unique", "foreign_key", "check", "not_null"]


class ErrorBingo(Exception):
    """Base de todos los errores propios de la aplicación."""

    def __init__(
        self,
        clave_i18n: str,
        *,
        detalle: str = "",
        parametros: dict[str, object] | None = None,
    ) -> None:
        super().__init__(detalle or clave_i18n)
        self.clave_i18n = clave_i18n
        self.parametros: dict[str, object] = parametros or {}
        self.detalle = detalle


class ErrorPersistencia(ErrorBingo):
    """Fallo de la capa de acceso a datos que no es culpa del usuario."""


class ErrorMigracion(ErrorPersistencia):
    """Fallo al aplicar el sistema de migraciones."""


class ErrorIntegridad(ErrorPersistencia):
    """Violación de una restricción de la base (FK, UNIQUE, CHECK, NOT NULL)."""

    def __init__(
        self,
        clave_i18n: str,
        *,
        tipo: TipoRestriccion,
        restriccion: str | None = None,
        detalle: str = "",
        parametros: dict[str, object] | None = None,
    ) -> None:
        super().__init__(clave_i18n, detalle=detalle, parametros=parametros)
        self.tipo = tipo
        self.restriccion = restriccion


class ErrorBaseBloqueada(ErrorPersistencia):
    """SQLITE_BUSY / SQLITE_LOCKED: condición recuperable, reintentable."""


class ErrorBaseCorrupta(ErrorPersistencia):
    """SQLITE_CORRUPT / SQLITE_NOTADB."""


class ErrorValidacion(ErrorBingo):
    """Error de entrada del usuario: se pinta junto al campo, nunca modal."""

    def __init__(
        self,
        clave_i18n: str,
        *,
        campo: str | None = None,
        detalle: str = "",
        parametros: dict[str, object] | None = None,
    ) -> None:
        super().__init__(clave_i18n, detalle=detalle, parametros=parametros)
        self.campo = campo


class ErrorImagen(ErrorValidacion):
    """Imagen inexistente, corrupta, con formato no soportado o demasiado grande."""


class ErrorDominio(ErrorBingo):
    """Regla de negocio violada; no es un error de tecleo del usuario."""


class ErrorTransicionInvalida(ErrorDominio):
    """Transición de estado no permitida por la máquina de estados."""


class ErrorNoEncontrado(ErrorDominio):
    """Un servicio esperaba una entidad existente y el repositorio devolvió None."""


class ErrorReanudacion(ErrorDominio):
    """Fase 5, decisión D13. La reproducción en memoria de una ronda
    (`extraccion` + cartones elegibles) no coincide, tras normalizar
    anulados y rechazados, con lo que la base tiene registrado en
    `ganador`. Es una incoherencia real, no un caso normal de anulación —
    modal terminal incluso en `modo_vivo` (decisión DU-12/4.27): un modal
    feo en cámara es mejor que seguir jugando sobre datos que no cuadran.
    """


class ErrorConfiguracion(ErrorBingo):
    """Fallo de configuración del entorno (rutas, preferencias, etc.)."""


def _en_hilo_principal() -> bool:
    return threading.current_thread() is threading.main_thread()


def instalar_manejador_global(
    *,
    mostrar_dialogo: Callable[[BaseException], None] | None = None,
) -> None:
    """Instala los manejadores de excepciones no controladas.

    Secuencia real ante una excepción no capturada en un *slot* invocado desde
    el bucle de eventos de Qt: registrar -> volcar a disco -> mostrar el modal
    -> el proceso termina (PySide6 aborta tras `sys.excepthook`). No hay
    "seguir usando la app" después de esto.

    Un `QThread` de PySide6 NO es un `threading.Thread`: una excepción que se
    escapa de `QThread.run()` llega a `sys.excepthook` **en el hilo
    trabajador**, no a `threading.excepthook`. Por eso el manejador
    comprueba en qué hilo está antes de intentar construir cualquier diálogo.
    """

    def _manejador(tipo: type[BaseException], valor: BaseException, tb: object) -> None:
        logger.critical("Excepción no controlada", exc_info=(tipo, valor, tb))
        for handler in logger.handlers:
            handler.flush()
        if _en_hilo_principal() and mostrar_dialogo is not None:
            mostrar_dialogo(valor)
        # En un hilo que no es el principal (incluye QThread) solo se registra:
        # construir un QMessageBox fuera del hilo de la interfaz es
        # comportamiento indefinido en Qt.

    def _manejador_hilo(args: threading.ExceptHookArgs) -> None:
        logger.critical(
            "Excepción no controlada en hilo %s",
            args.thread.name if args.thread else "?",
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )
        for handler in logger.handlers:
            handler.flush()

    sys.excepthook = _manejador
    threading.excepthook = _manejador_hilo
