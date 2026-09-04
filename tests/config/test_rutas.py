from pathlib import Path

from bingo.config import rutas


def test_asegurar_estructura_crea_carpetas(bingo_home: Path) -> None:
    rutas.asegurar_estructura()
    assert rutas.dir_datos().is_dir()
    assert rutas.dir_logs().is_dir()
    assert rutas.dir_respaldos().is_dir()
    assert rutas.dir_medios().is_dir()


def test_bingo_home_respetado(bingo_home: Path) -> None:
    assert rutas.raiz_datos() == bingo_home


def test_bingo_home_no_se_cachea(monkeypatch, tmp_path: Path) -> None:
    """`raiz_datos()` debe releer `os.environ` en cada llamada, sin cachear."""
    primero = tmp_path / "primero"
    segundo = tmp_path / "segundo"
    monkeypatch.setenv("BINGO_HOME", str(primero))
    assert rutas.raiz_datos() == primero
    monkeypatch.setenv("BINGO_HOME", str(segundo))
    assert rutas.raiz_datos() == segundo


def test_dir_medios_organizacion_usa_id(bingo_home: Path) -> None:
    assert rutas.dir_medios_organizacion(7) == rutas.dir_medios() / "7"


def test_dir_logs_evento_usa_id(bingo_home: Path) -> None:
    assert rutas.dir_logs_evento(3) == rutas.dir_logs() / "3"


def test_advertencia_ubicacion_sincronizada(monkeypatch, tmp_path: Path) -> None:
    ruta_onedrive = tmp_path / "OneDrive" / "Bingo"
    monkeypatch.setenv("BINGO_HOME", str(ruta_onedrive))
    assert rutas.advertencia_ubicacion_bd() == "ajustes.aviso_ubicacion_sincronizada"


def test_advertencia_ruta_unc(monkeypatch) -> None:
    monkeypatch.setenv("BINGO_HOME", r"\\servidor\recurso\Bingo")
    assert rutas.advertencia_ubicacion_bd() == "ajustes.aviso_ubicacion_sincronizada"


def test_sin_advertencia_en_ruta_local(bingo_home: Path) -> None:
    assert rutas.advertencia_ubicacion_bd() is None
