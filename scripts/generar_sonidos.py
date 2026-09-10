"""Genera los tres efectos de sonido del sorteo (decisión D6, plan de la
fase 5): `bola.wav`, `ganador.wav`, `alerta.wav` en `recursos/sonidos/`.

Solo con la biblioteca estándar (`wave` + `math`): cero dudas de licencia,
~20 KB en total. Se corre una sola vez; los `.wav` resultantes se versionan
(no se regeneran en cada arranque) y se declaran en `package-data`.

Uso: `python scripts/generar_sonidos.py`
"""

from __future__ import annotations

import math
import wave
from pathlib import Path
from struct import pack

FRECUENCIA_MUESTREO = 44100
_CARPETA_DESTINO = Path(__file__).parent.parent / "src" / "bingo" / "recursos" / "sonidos"


def _envolvente(t: float, duracion: float) -> float:
    """Ataque y caída suaves (10% de la duración cada uno) para que el
    blip no truene al empezar o terminar."""
    borde = duracion * 0.1
    if t < borde:
        return t / borde
    if t > duracion - borde:
        return (duracion - t) / borde
    return 1.0


def _tono(frecuencia_hz: float, duracion_s: float, *, amplitud: float = 0.5) -> list[int]:
    n = int(FRECUENCIA_MUESTREO * duracion_s)
    muestras = []
    for i in range(n):
        t = i / FRECUENCIA_MUESTREO
        valor = amplitud * _envolvente(t, duracion_s) * math.sin(2 * math.pi * frecuencia_hz * t)
        muestras.append(int(valor * 32767))
    return muestras


def _escribir_wav(ruta: Path, muestras: list[int]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(ruta), "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(FRECUENCIA_MUESTREO)
        archivo.writeframes(b"".join(pack("<h", m) for m in muestras))


def generar_bola() -> list[int]:
    """Blip corto y agudo: se oye una vez por bola, cada pocos segundos —
    tiene que ser breve y no cansar."""
    return _tono(880.0, 0.12, amplitud=0.4)


def generar_ganador() -> list[int]:
    """Tres notas ascendentes: la señal de "algo importante pasó"."""
    muestras: list[int] = []
    for frecuencia in (523.25, 659.25, 783.99):  # Do-Mi-Sol
        muestras.extend(_tono(frecuencia, 0.18, amplitud=0.5))
    return muestras


def generar_alerta() -> list[int]:
    """Dos pulsos graves: distinto timbre y ritmo a `bola`/`ganador` para
    que no se confunda con ninguno de los dos (fallo de log, aviso)."""
    muestras: list[int] = []
    for _ in range(2):
        muestras.extend(_tono(220.0, 0.15, amplitud=0.45))
        muestras.extend([0] * int(FRECUENCIA_MUESTREO * 0.06))
    return muestras


def generar_todos(carpeta: Path = _CARPETA_DESTINO) -> list[Path]:
    generadas = {
        "bola.wav": generar_bola(),
        "ganador.wav": generar_ganador(),
        "alerta.wav": generar_alerta(),
    }
    rutas = []
    for nombre, muestras in generadas.items():
        ruta = carpeta / nombre
        _escribir_wav(ruta, muestras)
        rutas.append(ruta)
    return rutas


if __name__ == "__main__":
    for ruta in generar_todos():
        print(f"Generado: {ruta}")
