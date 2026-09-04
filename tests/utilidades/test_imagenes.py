import io
from pathlib import Path

import pytest
from PIL import Image

from bingo.utilidades import imagenes
from bingo.utilidades.errores import ErrorImagen


def _crear_png(ruta: Path, tamano: tuple[int, int] = (10, 10)) -> None:
    Image.new("RGBA", tamano, (255, 0, 0, 255)).save(ruta, format="PNG")


def _crear_jpeg(ruta: Path, tamano: tuple[int, int] = (10, 10)) -> None:
    Image.new("RGB", tamano, (0, 255, 0)).save(ruta, format="JPEG")


def test_png_valido(tmp_path: Path) -> None:
    origen = tmp_path / "logo.png"
    _crear_png(origen)
    destino = tmp_path / "salida" / "logo_principal.png"
    resultado = imagenes.validar_y_normalizar(origen, destino)
    assert resultado.exists()
    with Image.open(resultado) as img:
        assert img.format == "PNG"
        assert img.mode == "RGBA"


def test_jpg_convertido_a_png(tmp_path: Path) -> None:
    origen = tmp_path / "logo.jpg"
    _crear_jpeg(origen)
    destino = tmp_path / "logo_principal.png"
    resultado = imagenes.validar_y_normalizar(origen, destino)
    with Image.open(resultado) as img:
        assert img.format == "PNG"


def test_archivo_inexistente_rechazado(tmp_path: Path) -> None:
    with pytest.raises(ErrorImagen):
        imagenes.validar_y_normalizar(tmp_path / "no_existe.png", tmp_path / "salida.png")


def test_archivo_corrupto_rechazado(tmp_path: Path) -> None:
    origen = tmp_path / "corrupto.png"
    origen.write_bytes(b"no es una imagen en absoluto")
    with pytest.raises(ErrorImagen):
        imagenes.validar_y_normalizar(origen, tmp_path / "salida.png")


def test_jpeg_truncado_rechazado(tmp_path: Path) -> None:
    """`verify()` no basta para JPEG truncado; `load()` sí lo detecta (enmienda G13)."""
    buffer = io.BytesIO()
    Image.new("RGB", (50, 50), (10, 20, 30)).save(buffer, format="JPEG")
    datos = buffer.getvalue()[:-200]  # corta el final
    origen = tmp_path / "truncado.jpg"
    origen.write_bytes(datos)
    with pytest.raises(ErrorImagen):
        imagenes.validar_y_normalizar(origen, tmp_path / "salida.png")


def test_redimensiona_si_excede_lado_max(tmp_path: Path) -> None:
    origen = tmp_path / "grande.png"
    _crear_png(origen, tamano=(200, 100))
    destino = tmp_path / "salida.png"
    imagenes.validar_y_normalizar(origen, destino, lado_max=50)
    with Image.open(destino) as img:
        assert max(img.size) == 50
        assert img.size == (50, 25)


def test_archivo_muy_grande_rechazado(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(imagenes, "_LIMITE_BYTES", 10)
    origen = tmp_path / "logo.png"
    _crear_png(origen)
    with pytest.raises(ErrorImagen):
        imagenes.validar_y_normalizar(origen, tmp_path / "salida.png")


def test_bomba_de_descompresion_rechazada(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(imagenes, "LIMITE_PIXELES_IMAGEN", 100)
    origen = tmp_path / "logo.png"
    _crear_png(origen, tamano=(50, 50))
    with pytest.raises(ErrorImagen):
        imagenes.validar_y_normalizar(origen, tmp_path / "salida.png")


def test_escritura_atomica_no_deja_temporal(tmp_path: Path) -> None:
    origen = tmp_path / "logo.png"
    _crear_png(origen)
    destino = tmp_path / "logo_principal.png"
    imagenes.validar_y_normalizar(origen, destino)
    assert not destino.with_suffix(destino.suffix + ".tmp").exists()


def test_es_imagen_valida() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (5, 5)).save(buffer, format="PNG")

    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        f.write(buffer.getvalue())
        ruta = Path(f.name)
    try:
        assert imagenes.es_imagen_valida(ruta)
    finally:
        ruta.unlink(missing_ok=True)
