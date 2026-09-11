"""Prueba de humo del binario empaquetado (tarea 4.14, hallazgo E-12).

Todo el resto del plan de pruebas corre sobre el árbol de fuentes con
`python`; ninguna prueba automática cubre el criterio de aceptación real
del contrato: "el instalador deja la aplicación funcionando en un equipo
limpio sin Python". Este script sí — arranca `dist/bingo/bingo.exe`
(el que produce `bingo.spec`) con `BINGO_HOME` en una carpeta temporal y
comprueba, contra el binario de verdad:

1. `bingo.exe --comprobar-empaquetado` sale con código 0 (los módulos de
   PySide6 que se cargan por nombre, y los recursos embebidos, están donde
   deben) — la parte que puede fallar en silencio dentro de un `.exe`
   aunque funcione perfecto corriendo desde el árbol de fuentes.
2. `bingo.exe --forzar-instancia` arranca, deja la base en la última
   versión de esquema conocida y un log de arranque, y termina limpio
   cuando se le pide cerrar.

Va en la SEMANA 1 del plan de empaquetado, no en la última: PyInstaller con
`QtMultimedia`/`QtTextToSpeech` es célebre por fallar tarde.

Uso, tras construir con PyInstaller desde la raíz del repo:
    .venv\\Scripts\\pyinstaller.exe empaquetado\\bingo.spec --noconfirm
    .venv\\Scripts\\python.exe empaquetado\\humo.py

Sale con 0 si todo pasó, distinto de 0 si algo falló (mensaje en stderr).
No usa pytest a propósito: corre contra un `.exe` que pytest no construye
ni conoce, y necesita apagar el proceso con una señal, no con un `assert`.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXE = RAIZ / "dist" / "bingo" / "bingo.exe"
# Debe coincidir con la migración más reciente de
# `src/bingo/persistencia/migraciones/*.sql` — se recalcula solo si hay
# `python` disponible (siempre lo hay: este script corre con él), así que
# nunca hace falta actualizar un número a mano aquí.
SEGUNDOS_ESPERA_ARRANQUE = 8


def _version_maxima_disponible() -> int:
    sys.path.insert(0, str(RAIZ / "src"))
    from bingo.persistencia.migraciones import version_maxima_disponible

    return version_maxima_disponible()


def _fallar(mensaje: str) -> None:
    print(f"[humo] FALLO: {mensaje}", file=sys.stderr)
    sys.exit(1)


def _comprobar_autocomprobacion(bingo_home: Path) -> None:
    resultado = subprocess.run(
        [str(EXE), "--comprobar-empaquetado"],
        # `env` REEMPLAZA el entorno entero, no lo extiende — sin el resto
        # de `os.environ` (PATH, SYSTEMROOT...), el proceso puede ni
        # siquiera arrancar en Windows.
        env={**os.environ, "BINGO_HOME": str(bingo_home)},
        capture_output=True,
        text=True,
        timeout=30,
    )
    if resultado.returncode != 0:
        _fallar(
            "bingo.exe --comprobar-empaquetado salió con código "
            f"{resultado.returncode}:\n{resultado.stdout}\n{resultado.stderr}"
        )
    print("[humo] --comprobar-empaquetado: OK")


def _comprobar_arranque_completo(bingo_home: Path) -> None:
    proceso = subprocess.Popen(
        [str(EXE), "--forzar-instancia"],
        env={**os.environ, "BINGO_HOME": str(bingo_home)},
    )
    try:
        time.sleep(SEGUNDOS_ESPERA_ARRANQUE)
        if proceso.poll() is not None:
            _fallar(
                f"bingo.exe terminó solo durante el arranque, código {proceso.returncode} "
                f"— revisa {bingo_home / 'logs' / 'aplicacion.log'}"
            )
    finally:
        if proceso.poll() is None:
            proceso.terminate()
            try:
                proceso.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proceso.kill()
                proceso.wait(timeout=10)

    ruta_bd = bingo_home / "datos" / "bingo.db"
    if not ruta_bd.exists():
        _fallar(f"no se creó {ruta_bd}")

    con = sqlite3.connect(ruta_bd)
    try:
        fila = con.execute("SELECT MAX(version) FROM schema_version").fetchone()
    finally:
        con.close()
    version_bd = fila[0] if fila else None
    esperada = _version_maxima_disponible()
    if version_bd != esperada:
        _fallar(f"schema_version={version_bd!r}, se esperaba {esperada}")

    ruta_log = bingo_home / "logs" / "aplicacion.log"
    if not ruta_log.exists():
        _fallar(f"no se creó {ruta_log}")

    print(f"[humo] arranque completo: OK (schema_version={version_bd})")


def main() -> int:
    if not EXE.exists():
        _fallar(
            f"no existe {EXE} — construye primero con "
            "'.venv\\Scripts\\pyinstaller.exe empaquetado\\bingo.spec --noconfirm'"
        )

    with tempfile.TemporaryDirectory(prefix="bingo-humo-") as carpeta_temporal:
        bingo_home = Path(carpeta_temporal)
        _comprobar_autocomprobacion(bingo_home)
        # Carpeta nueva para el arranque completo: `--comprobar-empaquetado`
        # no toca `BINGO_HOME`, pero mejor no compartir estado entre las dos
        # comprobaciones.
        bingo_home_arranque = bingo_home / "arranque"
        bingo_home_arranque.mkdir()
        _comprobar_arranque_completo(bingo_home_arranque)

    print("[humo] TODO OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
