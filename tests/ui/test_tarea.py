"""Enmienda E29: el trabajador `QThread` reutilizable, sin consumidor real en
la fase 1, probado aquí con un invocable de mentira que sí respeta el
convenio (`al_progresar`, `debe_cancelar`).
"""

from __future__ import annotations

import time

from bingo.ui.tarea import Tarea
from bingo.utilidades.errores import ErrorBingo


def _trabajo_exitoso(cantidad, *, al_progresar=None, debe_cancelar=None):
    for i in range(cantidad):
        if al_progresar:
            al_progresar(i + 1, cantidad)
    return "listo"


def _trabajo_que_falla(*, al_progresar=None, debe_cancelar=None):
    raise ErrorBingo("error.desconocido")


def _trabajo_cancelable(*, al_progresar=None, debe_cancelar=None):
    pasos = 0
    while not (debe_cancelar and debe_cancelar()):
        pasos += 1
        time.sleep(0.01)
        if pasos > 200:
            break
    return pasos


def test_emite_progreso_y_termina(qapp) -> None:
    progresos = []
    resultados = []

    tarea = Tarea(_trabajo_exitoso, 3)
    tarea.progreso.connect(lambda actual, total: progresos.append((actual, total)))
    tarea.terminado.connect(resultados.append)
    tarea.start()
    tarea.wait(2000)
    qapp.processEvents()  # las señales entre hilos se entregan en cola

    assert resultados == ["listo"]
    assert progresos == [(1, 3), (2, 3), (3, 3)]


def test_propaga_error_bingo_por_fallado(qapp) -> None:
    errores = []
    tarea = Tarea(_trabajo_que_falla)
    tarea.fallado.connect(errores.append)
    tarea.start()
    tarea.wait(2000)
    qapp.processEvents()

    assert len(errores) == 1
    assert isinstance(errores[0], ErrorBingo)


def test_cancelar_es_cooperativo(qapp) -> None:
    resultados = []
    tarea = Tarea(_trabajo_cancelable)
    tarea.terminado.connect(resultados.append)
    tarea.start()
    time.sleep(0.05)
    tarea.cancelar()
    tarea.wait(2000)
    qapp.processEvents()

    assert len(resultados) == 1
    assert resultados[0] < 200  # se detuvo antes del límite por la cancelación
