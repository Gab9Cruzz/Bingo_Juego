"""Log de partida: la tercera fuente de verdad de una ronda (contrato §5.9,
doc técnico §10). Si la base falla, el acta se puede reconstruir de aquí —
por eso cada línea fuerza `flush()` + `os.fsync()`, no solo un `write()`
bufferizado que puede quedarse en memoria si el proceso muere.

**Enmienda al doc técnico §6.2 (hallazgo S5-6, plan de la fase 5).** El
documento listaba la escritura del log como paso dentro de la transacción de
la bola. Se escribe **después** del commit: un `fsync` sobre un disco lleno
o una carpeta borrada lanza `OSError`, y si eso ocurriera dentro de la
transacción tumbaría el commit — el respaldo de última instancia haría caer
la fuente primaria. Esta clase no atrapa ese `OSError` (no le corresponde a
`utilidades/`, que es infraestructura sin política de error propia):
`servicios/servicio_sorteo.py` es quien la llama después del commit, registra
la advertencia y deja que el sorteo siga.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TextIO

from bingo.utilidades.fechas import ahora_iso


class LogPartida:
    """Un archivo de texto por ronda (`dir_logs_evento(evento_id)/
    ronda-<id>.log`), en modo apéndice: reanudar una ronda vuelve a abrir el
    mismo archivo y sigue añadiendo líneas, nunca lo trunca.
    """

    def __init__(self, ruta: Path) -> None:
        self._ruta = ruta
        self._archivo: TextIO | None = None

    @property
    def ruta(self) -> Path:
        return self._ruta

    def abrir(self) -> None:
        self._ruta.parent.mkdir(parents=True, exist_ok=True)
        self._archivo = self._ruta.open("a", encoding="utf-8")

    def linea(self, texto: str) -> None:
        """Escribe una línea con marca de tiempo ISO 8601 al frente. Formato
        completo de una línea de extracción: `ISO8601\\torden\\tnumero\\tevento`
        — el `texto` que recibe esta función es `orden\\tnumero\\tevento`; el
        ISO 8601 lo antepone aquí.
        """
        if self._archivo is None:
            raise ValueError("LogPartida no está abierto: llama a abrir() primero")
        self._archivo.write(f"{ahora_iso()}\t{texto}\n")
        self._archivo.flush()
        os.fsync(self._archivo.fileno())

    def cerrar(self) -> None:
        if self._archivo is not None:
            self._archivo.close()
            self._archivo = None
