"""Elección de la pantalla de transmisión (contrato §5.4, hallazgo E-9,
decisión DU-17). Función **pura**, sin Qt: la vista la llama con
`[s.name() for s in QGuiApplication.screens()]`.

Sin esta costura, toda la lógica de DU-17 (una sola pantalla, el monitor
guardado que ya no existe, ningún monitor guardado todavía) quedaría sin
cubrir por pruebas automáticas — `tests/conftest.py` fija
`QT_QPA_PLATFORM=offscreen` y no hay pantallas reales que elegir en CI. Con
esta función, los cuatro casos se prueban sin un monitor de verdad.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DecisionPantalla:
    """`pantalla=None` solo ocurre si `nombres_disponibles` viene vacío —
    no debería pasar nunca en un sistema real (`QGuiApplication.screens()`
    siempre devuelve al menos una), pero la función no asume que no pase.
    `motivo` es una clave i18n para avisar una vez, no un error."""

    pantalla: str | None
    modo_ventana: bool
    motivo: str


def elegir_pantalla(
    nombres_disponibles: list[str], nombre_guardado: str | None
) -> DecisionPantalla:
    """Cuatro casos (decisión DU-17):

    1. Ninguna pantalla (defensivo, no debería ocurrir): modo ventana, sin
       pantalla que elegir.
    2. Una sola pantalla (portátil, ensayo, desarrollo): modo ventana
       siempre — pantalla completa sobre la única pantalla tapa la interfaz
       del operador sin borde, sin barra de tareas y sin salida obvia.
    3. El monitor guardado (por nombre, hallazgo V7 — Windows reordena los
       índices entre arranques) sigue entre los disponibles: pantalla
       completa ahí, sin avisar.
    4. El monitor guardado no existe o nunca se guardó uno: pantalla
       completa en el segundo monitor disponible (el primero suele ser el
       del operador), y se avisa una vez con un motivo distinto según cuál
       de los dos casos fue.
    """
    if not nombres_disponibles:
        return DecisionPantalla(None, True, "transmision.pantalla.ninguna")

    if len(nombres_disponibles) == 1:
        return DecisionPantalla(nombres_disponibles[0], True, "transmision.pantalla.una_sola")

    if nombre_guardado is not None and nombre_guardado in nombres_disponibles:
        return DecisionPantalla(nombre_guardado, False, "transmision.pantalla.guardada")

    candidato = nombres_disponibles[1]
    motivo = (
        "transmision.pantalla.no_encontrada"
        if nombre_guardado is not None
        else "transmision.pantalla.sin_elegir"
    )
    return DecisionPantalla(candidato, False, motivo)
