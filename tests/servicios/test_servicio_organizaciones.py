import sqlite3
from pathlib import Path

import pytest
from PIL import Image

from bingo.dominio.modelos import Organizacion
from bingo.persistencia import repo_organizacion
from bingo.servicios import servicio_organizaciones
from bingo.utilidades.errores import ErrorValidacion


def _crear_png(ruta: Path) -> None:
    Image.new("RGBA", (20, 20), (10, 20, 30, 255)).save(ruta, format="PNG")


def test_alta_completa_con_logo(con: sqlite3.Connection, tmp_path: Path) -> None:
    logo = tmp_path / "logo.png"
    _crear_png(logo)

    creada = servicio_organizaciones.crear_organizacion(con, Organizacion(nombre="X"), logo)

    assert creada.id is not None
    assert creada.logo_path is not None
    assert Path(creada.logo_path).exists()
    assert Path(creada.logo_path).name == servicio_organizaciones.NOMBRE_LOGO_PRINCIPAL

    persistida = repo_organizacion.obtener(con, creada.id)
    assert persistida.logo_path == creada.logo_path


def test_alta_sin_logo(con: sqlite3.Connection) -> None:
    creada = servicio_organizaciones.crear_organizacion(con, Organizacion(nombre="Sin logo"), None)
    assert creada.logo_path is None


def test_alta_nombre_vacio_rechazada(con: sqlite3.Connection) -> None:
    with pytest.raises(ErrorValidacion):
        servicio_organizaciones.crear_organizacion(con, Organizacion(nombre="   "), None)


def test_commit_fallido_tras_copiar_logo_no_deja_rastro(
    con: sqlite3.Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """El punto de consistencia entre disco y base: si el commit falla después
    de copiar el logo, no debe quedar ni fila en la base ni archivo en disco.
    """
    logo = tmp_path / "logo.png"
    _crear_png(logo)

    def _falla(*args: object, **kwargs: object) -> None:
        raise RuntimeError("fallo simulado justo antes del commit")

    monkeypatch.setattr(servicio_organizaciones.repo_auditoria, "registrar", _falla)

    with pytest.raises(RuntimeError):
        servicio_organizaciones.crear_organizacion(con, Organizacion(nombre="X"), logo)

    assert repo_organizacion.listar(con) == []
    from bingo.config.rutas import dir_medios

    archivos = list(dir_medios().rglob("*.png"))
    assert archivos == [], f"quedaron archivos huérfanos: {archivos}"


def test_editar_reemplaza_logo(con: sqlite3.Connection, tmp_path: Path) -> None:
    logo1 = tmp_path / "logo1.png"
    _crear_png(logo1)
    creada = servicio_organizaciones.crear_organizacion(con, Organizacion(nombre="X"), logo1)

    logo2 = tmp_path / "logo2.png"
    Image.new("RGBA", (5, 5), (1, 2, 3, 255)).save(logo2, format="PNG")
    editada = servicio_organizaciones.actualizar_organizacion(con, creada, logo2)

    with Image.open(editada.logo_path) as img:
        assert img.size == (5, 5)


def test_eliminar_borra_carpeta_de_medios(con: sqlite3.Connection, tmp_path: Path) -> None:
    logo = tmp_path / "logo.png"
    _crear_png(logo)
    creada = servicio_organizaciones.crear_organizacion(con, Organizacion(nombre="X"), logo)
    carpeta = Path(creada.logo_path).parent
    assert carpeta.exists()

    servicio_organizaciones.eliminar_organizacion(con, creada.id)

    assert not carpeta.exists()
    assert repo_organizacion.obtener(con, creada.id) is None
