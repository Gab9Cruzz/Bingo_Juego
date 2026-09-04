"""Fixtures compartidas. Sin imports de Qt aquí: PySide6 cuesta ~1s por proceso
y la mayoría de las pruebas no lo necesitan (`tests/ui/conftest.py` las trae).
"""

import os

# Debe ser lo primero, antes de que cualquier módulo importe PySide6.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import shutil  # noqa: E402
import sqlite3  # noqa: E402
from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from bingo import i18n  # noqa: E402
from bingo.config.rutas import asegurar_estructura, ruta_bd  # noqa: E402
from bingo.persistencia.conexion import abrir_conexion  # noqa: E402
from bingo.persistencia.migraciones import aplicar_migraciones  # noqa: E402
from bingo.utilidades import log as bingo_log  # noqa: E402

pytest_plugins = ["factorias"]


@pytest.fixture(autouse=True)
def bingo_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Hace estructuralmente imposible que una prueba escriba en el
    `%LOCALAPPDATA%` real: redirige `BINGO_HOME` a una carpeta temporal por
    prueba. Autouse a propósito.
    """
    monkeypatch.setenv("BINGO_HOME", str(tmp_path))
    asegurar_estructura()
    return tmp_path


@pytest.fixture(autouse=True)
def estado_limpio() -> None:
    """Evita que el idioma cargado o los manejadores de log se filtren entre
    pruebas: pytest corre en un solo proceso y ambos son globales de módulo.
    """
    i18n.reiniciar_para_pruebas()
    bingo_log.reiniciar_para_pruebas()
    yield
    i18n.reiniciar_para_pruebas()
    bingo_log.reiniciar_para_pruebas()


@pytest.fixture(scope="session")
def plantilla_bd(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Migra una base UNA VEZ por sesión, sobre una ruta de
    `tmp_path_factory` (NO depende de `bingo_home`, que es de función: una
    fixture de sesión no puede depender de una de función sin que pytest
    lance `ScopeMismatch` en la recolección, y si dependiera de ella igual
    migraría dentro del `%LOCALAPPDATA%` real del desarrollador).
    """
    carpeta = tmp_path_factory.mktemp("plantilla")
    ruta = carpeta / "plantilla.db"
    con = abrir_conexion(ruta, synchronous="OFF")
    aplicar_migraciones(con)
    # El checkpoint es obligatorio ANTES de copiar el archivo: si el esquema
    # confirmado sigue en bingo.db-wal, copiar solo bingo.db produce una
    # plantilla vacía.
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    con.close()
    return ruta


@pytest.fixture
def con(plantilla_bd: Path, bingo_home: Path) -> sqlite3.Connection:
    """Copia la plantilla ya migrada dentro del hogar de la prueba y la abre."""
    destino = bingo_home / "datos"
    destino.mkdir(parents=True, exist_ok=True)
    ruta = ruta_bd()
    shutil.copyfile(plantilla_bd, ruta)
    conexion = abrir_conexion(ruta, synchronous="OFF")
    yield conexion
    conexion.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conexion.close()


@pytest.fixture
def con_memoria() -> sqlite3.Connection:
    conexion = abrir_conexion(":memory:", synchronous="OFF")
    from bingo.persistencia.migraciones import aplicar_migraciones as _aplicar

    _aplicar(conexion)
    yield conexion
    conexion.close()
