"""Trabajador `QThread` reutilizable (enmienda E29). Sin consumidor en la fase
1: las fases 2, 3 y 5 lo necesitan para generación de cartones, render de PDF y
sorteo — si no está escrito aquí, se reinventa tres veces.

Convenio del lado del servicio, indisociable de esta clase: el invocable que
se le pasa a `Tarea` acepta `al_progresar: Callable[[int, int], None] | None`
y `debe_cancelar: Callable[[], bool] | None`, y **nunca importa Qt** (así
`servicios/` se mantiene libre de PySide6, que verifica
`tests/arquitectura/test_arquitectura.py`). El invocable, no `Tarea`, abre y
cierra su propia conexión SQLite dentro de la llamada: una conexión no es
segura entre hilos, y este código corre en el hilo de `Tarea`, no en el de la
interfaz.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal

from bingo.utilidades.errores import ErrorBingo


class Tarea(QThread):
    progreso = Signal(int, int)
    terminado = Signal(object)
    fallado = Signal(object)  # ErrorBingo

    def __init__(
        self,
        funcion: Callable[..., Any],
        *args: object,
        **kwargs: object,
    ) -> None:
        super().__init__()
        self._funcion = funcion
        self._args = args
        self._kwargs = kwargs
        self._cancelada = False

    def cancelar(self) -> None:
        """Cooperativo: solo levanta la bandera que `debe_cancelar()` expone."""
        self._cancelada = True

    def _debe_cancelar(self) -> bool:
        return self._cancelada

    def run(self) -> None:
        try:
            resultado = self._funcion(
                *self._args,
                al_progresar=self.progreso.emit,
                debe_cancelar=self._debe_cancelar,
                **self._kwargs,
            )
        except ErrorBingo as error:
            self.fallado.emit(error)
        except Exception as error:  # noqa: BLE001 - frontera de hilo: no puede escapar
            self.fallado.emit(ErrorBingo("error.desconocido", detalle=str(error), parametros={}))
        else:
            self.terminado.emit(resultado)
