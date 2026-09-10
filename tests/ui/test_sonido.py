from pathlib import Path

from bingo.ui import sonido


def test_efectos_desactivado_no_instancia_nada(qapp) -> None:
    """Tarea 4.10: con `activado=False` no se instancia ningún
    `QSoundEffect` — en un equipo sin tarjeta de sonido, instanciar uno
    avisa por consola."""
    efectos = sonido.Efectos(activado=False)
    assert efectos.activados is False
    efectos.reproducir("bola")  # no debe lanzar aunque no haya nada


def test_efectos_activado_crea_los_tres(qapp) -> None:
    efectos = sonido.Efectos(activado=True)
    assert efectos.activados is True
    for clave in ("bola", "ganador", "alerta"):
        efectos.reproducir(clave)  # no debe lanzar, listo o no


def test_reproducir_clave_desconocida_no_lanza(qapp) -> None:
    efectos = sonido.Efectos(activado=True)
    efectos.reproducir("no_existe")


def test_musica_desactivada_no_instancia_nada(qapp) -> None:
    musica = sonido.Musica(activado=False)
    assert musica.activada is False
    musica.reproducir_archivo(Path("no-importa.mp3"))
    musica.detener()


def test_musica_activada_crea_reproductor(qapp) -> None:
    musica = sonido.Musica(activado=True, volumen=0.3)
    assert musica.activada is True


def test_crear_proveedor_desactivado_devuelve_none(qapp) -> None:
    """El mismo principio que Efectos/Musica: `activado=False` no toca
    `QTextToSpeech` en absoluto, ni siquiera para comprobar motores."""
    assert sonido.crear_proveedor("es", activado=False) is None


def test_crear_proveedor_sin_carpeta_pregrabada_usa_tts(qapp, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sonido, "_carpeta_pregrabada", lambda idioma: tmp_path / "no_existe")
    proveedor = sonido.crear_proveedor("es")
    assert isinstance(proveedor, sonido.LocucionTTS)


def test_crear_proveedor_con_carpeta_pregrabada_completa(qapp, tmp_path, monkeypatch) -> None:
    carpeta = tmp_path / "es"
    carpeta.mkdir()
    for n in range(1, 76):
        (carpeta / f"{n:02d}.wav").write_bytes(b"")
    monkeypatch.setattr(sonido, "_carpeta_pregrabada", lambda idioma: carpeta)

    proveedor = sonido.crear_proveedor("es")

    assert isinstance(proveedor, sonido.LocucionPregrabada)
    assert proveedor.disponible() is True


def test_pregrabada_incompleta_no_se_usa(qapp, tmp_path, monkeypatch) -> None:
    carpeta = tmp_path / "es"
    carpeta.mkdir()
    for n in range(1, 75):  # falta el 75
        (carpeta / f"{n:02d}.wav").write_bytes(b"")
    monkeypatch.setattr(sonido, "_carpeta_pregrabada", lambda idioma: carpeta)

    proveedor = sonido.crear_proveedor("es")

    assert isinstance(proveedor, sonido.LocucionTTS)


def test_locucion_tts_nunca_lanza_al_decir_sin_motor(qapp, monkeypatch) -> None:
    monkeypatch.setattr(sonido.LocucionTTS, "_importar_qtexttospeech", staticmethod(lambda: False))
    locucion = sonido.LocucionTTS("es")
    assert locucion.disponible() is False
    locucion.decir(42)  # no debe lanzar
    locucion.detener()
