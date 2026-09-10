import wave
from pathlib import Path

from scripts.generar_sonidos import FRECUENCIA_MUESTREO, generar_todos


def test_genera_los_tres_archivos(tmp_path: Path) -> None:
    rutas = generar_todos(tmp_path)
    nombres = {ruta.name for ruta in rutas}
    assert nombres == {"bola.wav", "ganador.wav", "alerta.wav"}
    for ruta in rutas:
        assert ruta.exists()
        assert ruta.stat().st_size > 0


def test_wav_valido_mono_16_bits(tmp_path: Path) -> None:
    rutas = generar_todos(tmp_path)
    for ruta in rutas:
        with wave.open(str(ruta), "rb") as archivo:
            assert archivo.getnchannels() == 1
            assert archivo.getsampwidth() == 2
            assert archivo.getframerate() == FRECUENCIA_MUESTREO


def test_son_pequenos() -> None:
    """Decisión D6: ~20 KB en total, no assets con licencia."""
    rutas = generar_todos()
    total = sum(ruta.stat().st_size for ruta in rutas)
    assert total < 200_000
