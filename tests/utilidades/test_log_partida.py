from pathlib import Path

import pytest

from bingo.utilidades.log_partida import LogPartida


def test_lineas_quedan_en_disco_sin_llamar_a_cerrar(tmp_path: Path) -> None:
    """Es la razón de existir de este módulo: si el proceso muere sin
    `cerrar()`, las líneas ya escritas (`flush()` + `fsync()`) siguen
    legibles en disco."""
    ruta = tmp_path / "logs" / "ronda-1.log"
    log = LogPartida(ruta)
    log.abrir()
    log.linea("1\t7\tevento-1")
    log.linea("2\t42\tevento-1")
    del log  # simula el proceso muriendo antes de cerrar()

    contenido = ruta.read_text(encoding="utf-8").splitlines()
    assert len(contenido) == 2
    assert contenido[0].endswith("1\t7\tevento-1")
    assert contenido[1].endswith("2\t42\tevento-1")


def test_formato_antepone_iso8601(tmp_path: Path) -> None:
    ruta = tmp_path / "ronda-1.log"
    log = LogPartida(ruta)
    log.abrir()
    log.linea("1\t7\tevento-1")
    log.cerrar()

    linea = ruta.read_text(encoding="utf-8").strip()
    marca, resto = linea.split("\t", 1)
    assert marca.endswith("Z")
    assert resto == "1\t7\tevento-1"


def test_crea_la_carpeta_si_no_existe(tmp_path: Path) -> None:
    ruta = tmp_path / "no_existe_todavia" / "ronda-1.log"
    log = LogPartida(ruta)
    log.abrir()
    log.linea("1\t1\tevento-1")
    log.cerrar()
    assert ruta.exists()


def test_modo_apendice_no_trunca_al_reabrir(tmp_path: Path) -> None:
    """Reanudar una ronda vuelve a abrir el mismo archivo."""
    ruta = tmp_path / "ronda-1.log"
    log = LogPartida(ruta)
    log.abrir()
    log.linea("1\t1\tevento-1")
    log.cerrar()

    log2 = LogPartida(ruta)
    log2.abrir()
    log2.linea("2\t2\tevento-1")
    log2.cerrar()

    assert len(ruta.read_text(encoding="utf-8").splitlines()) == 2


def test_linea_sin_abrir_falla() -> None:
    log = LogPartida(Path("no-importa.log"))
    with pytest.raises(ValueError):
        log.linea("1\t1\tevento-1")


def test_error_de_disco_al_escribir_no_se_traga(tmp_path: Path, monkeypatch) -> None:
    """S5-6: `linea()` no atrapa el `OSError` — le corresponde al llamante
    (`servicio_sorteo`, tarea 4.6) decidir qué hacer con él después del
    commit."""
    ruta = tmp_path / "ronda-1.log"
    log = LogPartida(ruta)
    log.abrir()

    def fsync_que_falla(fd: int) -> None:
        raise OSError("disco lleno (simulado)")

    monkeypatch.setattr("os.fsync", fsync_que_falla)
    with pytest.raises(OSError):
        log.linea("1\t1\tevento-1")
