"""Fechas y horas: todo lo que va a la base es ISO 8601 en texto, en UTC.

La conversión a hora local ocurre solo al mostrar. `evento.fecha` es una
excepción deliberada: es una fecha de calendario (`YYYY-MM-DD`), el día del
bingo, no un instante con zona horaria — la hora del evento es hora local del
lugar donde se juega y no tiene sentido convertirla a UTC.
"""

from __future__ import annotations

from datetime import UTC, datetime


def ahora_iso() -> str:
    """Momento actual en UTC, ISO 8601 con sufijo `Z`."""
    return a_iso(datetime.now(UTC))


def a_iso(momento: datetime) -> str:
    """Convierte un `datetime` (con o sin zona) a ISO 8601 UTC con sufijo `Z`."""
    if momento.tzinfo is None:
        momento = momento.replace(tzinfo=UTC)
    return momento.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def desde_iso(texto: str) -> datetime:
    """Parsea un texto ISO 8601 (con `Z` o desfase explícito) a `datetime` en UTC."""
    return datetime.fromisoformat(texto.replace("Z", "+00:00")).astimezone(UTC)


def formatear_para_ui(texto_iso: str, idioma: str) -> str:
    """Formatea un instante ISO 8601 a texto local legible según el idioma."""
    momento = desde_iso(texto_iso).astimezone()
    if idioma == "en":
        return momento.strftime("%Y-%m-%d %H:%M")
    return momento.strftime("%d/%m/%Y %H:%M")
