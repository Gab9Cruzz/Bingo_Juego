from pathlib import Path

from bingo.config import preferencias
from bingo.config.rutas import ruta_preferencias


def test_ida_y_vuelta(bingo_home: Path) -> None:
    prefs = preferencias.cargar()
    prefs.idioma = "en"
    prefs.ultimo_evento_abierto_id = 42
    preferencias.guardar(prefs)

    recargadas = preferencias.cargar()
    assert recargadas.idioma == "en"
    assert recargadas.ultimo_evento_abierto_id == 42


def test_archivo_ausente_da_valores_por_defecto(bingo_home: Path) -> None:
    prefs = preferencias.cargar()
    assert prefs.idioma == "es"
    assert prefs.ultimo_evento_abierto_id is None


def test_json_corrupto_da_valores_por_defecto_y_renombra(bingo_home: Path) -> None:
    ruta = ruta_preferencias()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("{ esto no es json", encoding="utf-8")

    prefs = preferencias.cargar()

    assert prefs.idioma == "es"
    assert ruta.with_suffix(ruta.suffix + ".corrupto").exists()
    assert not ruta.exists()


def test_escritura_atomica_no_deja_temporal(bingo_home: Path) -> None:
    preferencias.guardar(preferencias.cargar())
    ruta = ruta_preferencias()
    assert ruta.exists()
    assert not ruta.with_suffix(ruta.suffix + ".tmp").exists()
