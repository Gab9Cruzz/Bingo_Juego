"""Prueba de actualización sobre datos, contra el binario real (tarea 4.14).

Complementa `empaquetado/humo.py`: aquella prueba arranca en limpio; esta
simula el caso que de verdad importa para una organización que ya usó la
app antes — "las migraciones se aplican bien al actualizar sobre una
instalación existente con datos", y no se puede cubrir con `pytest` sobre
el árbol de fuentes porque el criterio de aceptación es sobre el `.exe`
que un operador real reemplaza.

Pasos:
1. Con el intérprete de este repo (no el `.exe`), construye una base solo
   con las migraciones 001+002+003 — una "instalación anterior a la fase
   5" — y le inserta un puñado de filas reales (organización, evento,
   cartón, comprador).
2. Arranca `dist/bingo/bingo.exe` (el binario que ya sabe hasta la 004)
   sobre ese mismo `BINGO_HOME`.
3. Verifica: la base llegó a `version_maxima_disponible()`, las filas
   insertadas en el paso 1 siguen ahí íntegras, y quedó
   `bingo.db.pre-3` (hallazgo B5, tarea 4.22) con el contenido de ANTES de
   migrar — no una copia vacía ni la ya migrada.

Uso, tras construir con PyInstaller desde la raíz del repo:
    .venv\\Scripts\\pyinstaller.exe empaquetado\\bingo.spec --noconfirm
    .venv\\Scripts\\python.exe empaquetado\\actualizacion.py
"""

from __future__ import annotations

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
EXE = RAIZ / "dist" / "bingo" / "bingo.exe"
SEGUNDOS_ESPERA_ARRANQUE = 8


def _fallar(mensaje: str) -> None:
    print(f"[actualizacion] FALLO: {mensaje}", file=sys.stderr)
    sys.exit(1)


def _construir_base_version_3(bingo_home: Path) -> None:
    """Usa el árbol de fuentes de este repo (no el `.exe`) solo para
    preparar el escenario — lo que se está probando es lo que hace el
    `.exe` a partir de aquí, no esta parte."""
    sys.path.insert(0, str(RAIZ / "src"))
    from bingo.config import rutas

    os.environ["BINGO_HOME"] = str(bingo_home)
    rutas.asegurar_estructura()

    from bingo.persistencia import migraciones as modulo_migraciones

    directorio_real = modulo_migraciones._resolver_directorio()  # noqa: SLF001
    carpeta_solo_003 = bingo_home / "_migraciones_003"
    carpeta_solo_003.mkdir()
    for nombre in ("001_inicial.sql", "002_fase3.sql", "003_fase4.sql"):
        (carpeta_solo_003 / nombre).write_bytes((directorio_real / nombre).read_bytes())
    modulo_migraciones._resolver_directorio = lambda: carpeta_solo_003  # noqa: SLF001

    from bingo.persistencia.conexion import abrir_conexion

    con = abrir_conexion()
    try:
        aplicadas = modulo_migraciones.aplicar_migraciones(con)
        if aplicadas != [1, 2, 3]:
            _fallar(f"la base de partida no quedó en la versión 3: aplicó {aplicadas}")
        con.execute(
            "INSERT INTO organizacion (nombre, creada_en) VALUES ('Org de actualización', 'y')"
        )
        con.execute(
            "INSERT INTO evento (organizacion_id, nombre, creado_en) "
            "VALUES (1, 'Evento previo a la fase 5', 'y')"
        )
        con.commit()
    finally:
        con.close()
    shutil.rmtree(carpeta_solo_003)


def main() -> int:
    if not EXE.exists():
        _fallar(
            f"no existe {EXE} — construye primero con "
            "'.venv\\Scripts\\pyinstaller.exe empaquetado\\bingo.spec --noconfirm'"
        )

    with tempfile.TemporaryDirectory(prefix="bingo-actualizacion-") as carpeta_temporal:
        bingo_home = Path(carpeta_temporal)
        _construir_base_version_3(bingo_home)
        print("[actualizacion] base de partida en version 3: OK")

        proceso = subprocess.Popen(
            [str(EXE), "--forzar-instancia"],
            env={**os.environ, "BINGO_HOME": str(bingo_home)},
        )
        try:
            time.sleep(SEGUNDOS_ESPERA_ARRANQUE)
            if proceso.poll() is not None:
                _fallar(f"bingo.exe terminó solo, código {proceso.returncode}")
        finally:
            if proceso.poll() is None:
                proceso.terminate()
                try:
                    proceso.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proceso.kill()
                    proceso.wait(timeout=10)

        ruta_bd = bingo_home / "datos" / "bingo.db"
        con = sqlite3.connect(ruta_bd)
        con.row_factory = sqlite3.Row
        try:
            version_final = con.execute("SELECT MAX(version) AS v FROM schema_version").fetchone()[
                "v"
            ]
            nombre = con.execute("SELECT nombre FROM organizacion WHERE id = 1").fetchone()
        finally:
            con.close()

        sys.path.insert(0, str(RAIZ / "src"))
        from bingo.persistencia.migraciones import version_maxima_disponible

        esperada = version_maxima_disponible()
        if version_final != esperada:
            _fallar(f"schema_version quedó en {version_final}, se esperaba {esperada}")
        if nombre is None or nombre["nombre"] != "Org de actualización":
            _fallar("la fila de organización insertada antes de migrar no sobrevivió")
        print(f"[actualizacion] migró de 3 a {version_final} sin perder filas: OK")

        copia_pre_3 = ruta_bd.with_name("bingo.db.pre-3")
        if not copia_pre_3.exists():
            _fallar(f"no se encontró {copia_pre_3} (hallazgo B5, tarea 4.22)")
        con_copia = sqlite3.connect(copia_pre_3)
        con_copia.row_factory = sqlite3.Row
        try:
            version_copia = con_copia.execute(
                "SELECT MAX(version) AS v FROM schema_version"
            ).fetchone()["v"]
            nombre_copia = con_copia.execute(
                "SELECT nombre FROM organizacion WHERE id = 1"
            ).fetchone()
        finally:
            con_copia.close()
        if version_copia != 3:
            _fallar(f"bingo.db.pre-3 quedó en la versión {version_copia}, se esperaba 3")
        if nombre_copia is None or nombre_copia["nombre"] != "Org de actualización":
            _fallar("bingo.db.pre-3 no conserva los datos de antes de migrar")
        print("[actualizacion] bingo.db.pre-3 íntegro en la versión 3: OK")

    print("[actualizacion] TODO OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
