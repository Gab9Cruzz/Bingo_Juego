import sqlite3
import zipfile
from pathlib import Path

import pytest
from factorias import (
    crear_carton,
    crear_comprador,
    crear_evento,
    crear_organizacion,
    crear_patron,
    crear_ronda,
)

from bingo.config.rutas import dir_respaldos, raiz_datos, ruta_bd
from bingo.persistencia import repo_carton, repo_ronda
from bingo.servicios import servicio_respaldos
from bingo.utilidades.errores import ErrorNoEncontrado, ErrorValidacion


def _evento_simple(con: sqlite3.Connection):
    org = crear_organizacion(con)
    return crear_evento(con, org.id)


def test_exportar_crea_un_zip_con_la_base_y_el_leeme(
    con: sqlite3.Connection, bingo_home: Path
) -> None:
    evento = _evento_simple(con)
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    ruta_zip = servicio_respaldos.exportar(evento.id)

    assert ruta_zip is not None
    assert ruta_zip.exists()
    assert ruta_zip.parent == dir_respaldos()
    with zipfile.ZipFile(ruta_zip) as z:
        nombres = z.namelist()
        assert "datos/bingo.db" in nombres
        assert "RESPALDO_LEEME.txt" in nombres
        leeme = z.read("RESPALDO_LEEME.txt").decode("utf-8")
        assert "datos personales" in leeme


def test_exportar_evento_inexistente_falla(con: sqlite3.Connection, bingo_home: Path) -> None:
    with pytest.raises(ErrorNoEncontrado):
        servicio_respaldos.exportar(999_999)


def test_exportar_bloqueado_con_ronda_en_curso(con: sqlite3.Connection, bingo_home: Path) -> None:
    evento = _evento_simple(con)
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento.id, patron.id, orden=1)
    repo_ronda.actualizar_estado(con, ronda.id, "en_curso")

    with pytest.raises(ErrorValidacion):
        servicio_respaldos.exportar(evento.id)


def test_exportar_bloqueado_con_ronda_pausada(con: sqlite3.Connection, bingo_home: Path) -> None:
    evento = _evento_simple(con)
    patron = crear_patron(con)
    ronda = crear_ronda(con, evento.id, patron.id, orden=1)
    repo_ronda.actualizar_estado(con, ronda.id, "pausada")

    with pytest.raises(ErrorValidacion):
        servicio_respaldos.exportar(evento.id)


def test_exportar_cancelado_no_deja_zip_parcial(con: sqlite3.Connection, bingo_home: Path) -> None:
    evento = _evento_simple(con)
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    resultado = servicio_respaldos.exportar(evento.id, debe_cancelar=lambda: True)

    assert resultado is None
    assert list(dir_respaldos().glob("*.zip")) == []
    assert list(dir_respaldos().glob("*.tmp")) == []


def test_exportar_incluye_medios_logs_impresos_si_existen(
    con: sqlite3.Connection, bingo_home: Path
) -> None:
    from bingo.config.rutas import dir_impresos_evento, dir_medios_evento

    evento = _evento_simple(con)
    dir_medios_evento(evento.id).mkdir(parents=True, exist_ok=True)
    (dir_medios_evento(evento.id) / "logo.png").write_bytes(b"fake-png")
    dir_impresos_evento(evento.id).mkdir(parents=True, exist_ok=True)
    (dir_impresos_evento(evento.id) / "acta-1.pdf").write_bytes(b"fake-pdf")
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    ruta_zip = servicio_respaldos.exportar(evento.id)

    with zipfile.ZipFile(ruta_zip) as z:
        nombres = z.namelist()
        assert "medios/logo.png" in nombres
        assert "impresos/acta-1.pdf" in nombres


def test_validar_zip_inexistente_falla(tmp_path: Path) -> None:
    with pytest.raises(ErrorValidacion):
        servicio_respaldos.validar_zip_de_respaldo(tmp_path / "no_existe.zip")


def test_validar_zip_sin_base_falla(tmp_path: Path) -> None:
    ruta = tmp_path / "malo.zip"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("RESPALDO_LEEME.txt", "hola")
    with pytest.raises(ErrorValidacion):
        servicio_respaldos.validar_zip_de_respaldo(ruta)


def test_validar_zip_corrupto_falla(tmp_path: Path) -> None:
    ruta = tmp_path / "corrupto.zip"
    ruta.write_bytes(b"esto no es un zip de verdad")
    with pytest.raises(ErrorValidacion):
        servicio_respaldos.validar_zip_de_respaldo(ruta)


def test_extraer_seguro_rechaza_zip_slip(tmp_path: Path) -> None:
    ruta_zip = tmp_path / "malicioso.zip"
    with zipfile.ZipFile(ruta_zip, "w") as z:
        z.writestr("../../fuera.txt", "malicioso")

    destino = tmp_path / "destino"
    destino.mkdir()
    with zipfile.ZipFile(ruta_zip) as z, pytest.raises(ErrorValidacion):
        servicio_respaldos._extraer_seguro(z, destino)  # noqa: SLF001
    assert not (tmp_path / "fuera.txt").exists()


def test_restaurar_mueve_los_datos_previos_y_extrae_encima(
    con: sqlite3.Connection, bingo_home: Path
) -> None:
    evento = _evento_simple(con)
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    ruta_zip = servicio_respaldos.exportar(evento.id)
    con.close()

    # Deja un archivo centinela para comprobar que lo "viejo" se movió, no
    # se borró.
    (raiz_datos() / "centinela.txt").write_text("hola")

    ruta_bd_restaurada = servicio_respaldos.restaurar(ruta_zip)

    assert ruta_bd_restaurada == ruta_bd()
    assert ruta_bd_restaurada.exists()
    copias_previas = list(raiz_datos().parent.glob(f"{raiz_datos().name}.pre-restauracion-*"))
    assert len(copias_previas) == 1
    assert (copias_previas[0] / "centinela.txt").exists()


def test_exportar_y_restaurar_conserva_los_cartones(
    con: sqlite3.Connection, bingo_home: Path, lote_creado, evento_creado
) -> None:
    """El criterio de aceptación de la tarea 4.12: el .zip de un evento
    tomado a mitad de partida se restaura y los datos siguen ahí."""
    carton = crear_carton(con, evento_creado.id, lote_creado.id, semilla=1, estado="vendido")
    crear_comprador(con, carton.id)
    con.execute("PRAGMA wal_checkpoint(TRUNCATE)")

    ruta_zip = servicio_respaldos.exportar(evento_creado.id)
    con.close()

    servicio_respaldos.restaurar(ruta_zip)

    from bingo.persistencia.conexion import abrir_conexion

    con_restaurada = abrir_conexion(synchronous="OFF")
    try:
        recuperado = repo_carton.obtener_por_codigo(con_restaurada, evento_creado.id, carton.codigo)
        assert recuperado is not None
        assert recuperado.estado == "vendido"
    finally:
        con_restaurada.close()
